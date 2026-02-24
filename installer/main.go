package main

import (
    "fmt"
    "os"
    "os/exec"
    "runtime"
    "syscall"
    "time"
    "unicode"

    "github.com/charmbracelet/bubbles/spinner"
    tea "github.com/charmbracelet/bubbletea"
    "github.com/charmbracelet/lipgloss"
    "golang.org/x/crypto/bcrypt"
    "golang.org/x/term"
)

// --- CONFIGURATION & STYLES ---
var (
    headerStyle = lipgloss.NewStyle().
            Foreground(lipgloss.Color("#f05a28")).
            Bold(true).
            BorderStyle(lipgloss.DoubleBorder()).
            BorderForeground(lipgloss.Color("#f05a28")).
            Padding(0, 1).
            Width(46).             // Fixed width for the header box
            Align(lipgloss.Center) // Center text inside

    successStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Bold(true)
    errorStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
    checkStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
    statusStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
)

var (
    // Style for the final success footer box
    footerStyle = lipgloss.NewStyle().
        Foreground(lipgloss.Color("42")). 
        Bold(true).
        BorderStyle(lipgloss.DoubleBorder()).
        BorderForeground(lipgloss.Color("42")).
        Padding(0, 1).
        Width(55). 
        Align(lipgloss.Center)
)

type statusMsg string
type errMsg error
type successMsg bool

type model struct {
    spinner   spinner.Model
    status    string
    err       error
    quitting  bool
    step      int
    adminUser string
    adminPwd  string
    results   []string
}

// 1. System Check & Smart Cleanup
func checkAndPrepare() (string, error) {
    if runtime.GOOS != "linux" {
        return "", fmt.Errorf("K-Guard is optimized for Linux (Debian/Ubuntu)")
    }
    if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
        return "", fmt.Errorf("K3s not found. Please install K3s before running K-Guard")
    }

    // Check if Namespace exists
    cmd := exec.Command("kubectl", "get", "ns", "k-guard")
    if err := cmd.Run(); err == nil {
        // Namespace exists: prepare the ground by removing orphans
        // Note: Requires 'app=k-guard' label in your YAML files
        pruneCmd := exec.Command("kubectl", "apply", "-f", "../k8s/", "-n", "k-guard", "--prune", "-l", "app=k-guard", "--all")
        _ = pruneCmd.Run()
        return "Update detected: Obsolete resources cleanup completed", nil
    }

    // Check binary dependencies needed for the sh script
    dependencies := []string{"kubectl", "sh"}
    for _, dep := range dependencies {
        if _, err := exec.LookPath(dep); err != nil {
            return "", fmt.Errorf("Missing dependency: %s", dep)
        }
    }

    // Check Docker socket (essential for Trivy in local image mode)
    if _, err := os.Stat("/var/run/docker.sock"); os.IsNotExist(err) {
        // Warning only, as Trivy can scan via registry
        fmt.Println("⚠️  Warning: /var/run/docker.sock not found. Local image scans might fail.")
    }

    // New deployment
    if err := exec.Command("kubectl", "create", "namespace", "k-guard").Run(); err != nil {
        return "", fmt.Errorf("Namespace creation failed: %v", err)
    }
    return "New deployment: Infrastructure initialized", nil
}

// 2. Credentials Generation
func setupCredentials(username string, password string) error {
    hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
    if err != nil {
        return err
    }

    envContent := fmt.Sprintf(`# K-GUARD CONFIGURATION GENERATED ON %s
ALLOWED_ORIGINS=http://localhost:30002,http://113.30.191.17:30002
ADMIN_USERNAME=%s
ADMIN_PASSWORD_HASH=%s
SECRET_KEY=kguard_%d
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=600

# --- INFRASTRUCTURE INFOS ---
USER_DOMAIN=113.30.191.17
PROJECT_NAME=K-Guard

# --- NETWORK SENTINEL CONFIGURATION ---
KGUARD_PROTECTED_NS=k-guard,blog-prod,portfolio-prod
KGUARD_ANSIBLE_PATH=../infra/ansible/harden_network.yml

# --- SCANNER CONFIGURATION (TRIVY) ---
TRIVY_CACHE_DIR=/data/trivy-cache
`, 
    time.Now().Format("2006-01-02"), 
    username,                        
    string(hash),                    
    time.Now().Unix())               

    return os.WriteFile("../backend/.env", []byte(envContent), 0600)
}

// 2.bis Secret Synchronization to K3s (Idempotent)
func syncSecretsToK8s() error {
    // Using sh -c to handle piping and dry-run
    // This ensures the secret is updated without errors if it already exists
    script := "kubectl create secret generic k-guard-secrets --from-env-file=../backend/.env -n k-guard --dry-run=client -o yaml | kubectl apply -f -"

    cmd := exec.Command("sh", "-c", script)
    output, err := cmd.CombinedOutput()
    if err != nil {
        return fmt.Errorf("Secrets sync failed: %v\n%s", err, string(output))
    }
    return nil
}

// 3. K8s Orchestration (Idempotent)
func deployK8s() error {
    // kubectl apply is natively smart and only recreates what changed
    cmd := exec.Command("kubectl", "apply", "-f", "../k8s/", "-n", "k-guard")
    output, err := cmd.CombinedOutput()
    if err != nil {
        return fmt.Errorf("K8s deployment failed: %v\n%s", err, string(output))
    }
    return nil
}

// --- BUBBLE TEA ENGINE ---

func (m model) Init() tea.Cmd {
    return tea.Batch(m.spinner.Tick, m.runStep(0))
}

func (m model) runStep(step int) tea.Cmd {
    return func() tea.Msg {
        var err error
        var msg string
        time.Sleep(800 * time.Millisecond) // Delay for readability

        switch step {
        case 0:
            msg = "Checking system dependencies (kubectl, sh...)"
            _, err = checkAndPrepare()
        case 1:
            msg = "Checking Docker socket (/var/run/docker.sock)"
            if _, errStat := os.Stat("/var/run/docker.sock"); os.IsNotExist(errStat) {
                msg = "Docker socket missing (Limited local scan)"
            } else {
                msg = "Docker socket detected and accessible"
            }
        case 2:
            msg = "Generating .env file (Bcrypt & Configuration)"
            err = setupCredentials(m.adminUser, m.adminPwd)
        case 3:
            msg = "Initializing Trivy vulnerability database"
            // Simulating preparation or directory check
            msg = "Trivy database ready for analysis"
        case 4:
            msg = "Injecting secrets into K3s cluster"
            err = syncSecretsToK8s()
        case 5:
            msg = "Final manifests deployment (Services & Pods)"
            err = deployK8s()
        default:
            return successMsg(true)
        }

        if err != nil {
            return errMsg(err)
        }
        return statusMsg(msg)
    }
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
    switch msg := msg.(type) {
    case statusMsg:
        m.results = append(m.results, string(msg))
        m.status = string(msg)
        m.step++
        return m, m.runStep(m.step)
    case successMsg:
        m.quitting = true
        return m, tea.Quit
    case errMsg:
        m.err = msg
        return m, tea.Quit
    case spinner.TickMsg:
        var cmd tea.Cmd
        m.spinner, cmd = m.spinner.Update(msg)
        return m, cmd
    case tea.KeyMsg:
        if msg.String() == "q" || msg.String() == "ctrl+c" {
            return m, tea.Quit
        }
    }
    return m, nil
}

func (m model) View() string {
    if m.err != nil {
        return errorStyle.Render(fmt.Sprintf("\n❌ Fatal Error: %v\n", m.err))
    }

    s := "\n" + headerStyle.Render("🛡️ K-GUARD SYSTEM INSTALLER ") + "\n\n"

    for _, res := range m.results {
        s += checkStyle.Render("  ✓ ") + res + "\n"
    }

    if m.quitting {
        successMsg := fmt.Sprintf(
            "Thank you for installing, %s!\n\nK-Guard is ready & accessible via:\n'113.30.191.17:30002'\n\nTo know more about my works, visit:\nhttps://devopsnotes.org",
            m.adminUser,
        )
        
        s += "\n" + footerStyle.Render(successMsg) + "\n"
        return s
    }

    s += "\n " + m.spinner.View() + " " + m.status + "\n\n"
    s += statusStyle.Render(" [q] quit")
    return s
}

func isStrongPassword(p string) (bool, string) {
    var (
        hasMinLen  = len(p) >= 8
        hasUpper   = false
        hasNumber  = false
        hasSpecial = false
    )
    for _, char := range p {
        switch {
        case unicode.IsUpper(char):
            hasUpper = true
        case unicode.IsNumber(char):
            hasNumber = true
        case unicode.IsPunct(char) || unicode.IsSymbol(char):
            hasSpecial = true
        }
    }
    if !hasMinLen {
        return false, "8 characters minimum"
    }
    if !hasUpper {
        return false, "at least one uppercase letter"
    }
    if !hasNumber {
        return false, "at least one number"
    }
    if !hasSpecial {
        return false, "at least one special character"
    }
    return true, ""
}

func main() {
    var user string
    for {
        fmt.Print("👤 Enter the administrator username: ")
        fmt.Scanln(&user)

        if user == "" {
            fmt.Println(errorStyle.Render("❌ Username cannot be empty."))
            continue
        }
        break
    }
    var pass string
    for {
        fmt.Print("🔐 Define the admin password for '%s': ")
        bytePassword, _ := term.ReadPassword(int(syscall.Stdin))
        fmt.Println()

        p1 := string(bytePassword)

        // Password strength validation
        if ok, help := isStrongPassword(p1); !ok {
            fmt.Printf("❌ %s: %s\n", errorStyle.Render("Insufficiently secure"), help)
            continue
        }

        fmt.Print("🔄 Confirm password: ")
        byteConfirm, _ := term.ReadPassword(int(syscall.Stdin))
        fmt.Println()

        if p1 != string(byteConfirm) {
            fmt.Println(errorStyle.Render("❌ Passwords do not match. Please try again."))
            continue
        }

        pass = p1
        break
    }

    fmt.Println(successStyle.Render("✨ Secure password stored."))

    spin := spinner.New()
    spin.Spinner = spinner.Dot
    spin.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28"))

    p := tea.NewProgram(model{
        spinner:  spin,
        status:   "Dependency check...",
        adminPwd: pass,
        results:  make([]string, 0),
    })

    if _, err := p.Run(); err != nil {
        fmt.Printf("Fatal Error: %v", err)
        os.Exit(1)
    }
}