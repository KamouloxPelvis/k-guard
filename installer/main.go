package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
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
			Width(60).
			Align(lipgloss.Center)

	successStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Bold(true)
	errorStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
	checkStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	statusStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))

	footerStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color("42")).
			Bold(true).
			BorderStyle(lipgloss.DoubleBorder()).
			BorderForeground(lipgloss.Color("42")).
			Padding(0, 1).
			Width(60).
			Align(lipgloss.Center)
)

type statusMsg string
type errMsg error
type successMsg bool

type model struct {
	spinner     spinner.Model
	status      string
	err         error
	quitting    bool
	step        int
	adminUser   string
	adminPwd    string
	results     []string
	projectRoot string // Stockage du chemin absolu racine
}

// --- CORE FUNCTIONS ---

func checkAndPrepare() (string, error) {
	if runtime.GOOS != "linux" {
		return "", fmt.Errorf("K-Guard is optimized for Linux systems")
	}
	// Vérification de K3s (Crucial pour ton architecture)
	if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
		return "", fmt.Errorf("K3s not found. Please install K3s to host K-Guard infrastructure")
	}

	// Nettoyage intelligent du Namespace
	cmd := exec.Command("kubectl", "get", "ns", "k-guard")
	if err := cmd.Run(); err == nil {
		return "Infrastructure existing, ready for update", nil
	}

	if err := exec.Command("kubectl", "create", "namespace", "k-guard").Run(); err != nil {
		return "", fmt.Errorf("Namespace creation failed: %v", err)
	}
	return "Infrastructure namespace initialized", nil
}

// Helper to get the public IP of the VPS
func getPublicIP() string {
	cmd := exec.Command("curl", "-s", "ifconfig.me")
	out, err := cmd.Output()
	if err != nil {
		return "127.0.0.1" // Fallback to localhost if no internet
	}
	return strings.TrimSpace(string(out))
}

func setupCredentials(rootPath, username, password string) error {
	publicIP := getPublicIP() // Dynamic detection

	hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
	if err != nil {
		return fmt.Errorf("failed to hash password: %v", err)
	}

	envPath := filepath.Join(rootPath, "backend", ".env")

	protectedNamespaces := "k-guard"

	// Fixed: Added publicIP and publicIP to the arguments of Sprintf
	envContent := fmt.Sprintf(`# K-GUARD SYSTEM CONFIGURATION
# Generated on: %s
# Target Environment: Global/Portable

# --- PATH RESOLUTION ---
PROJECT_ROOT=%s
DB_DIR=%s/backend/data
KGUARD_ANSIBLE_PATH=%s/infra/ansible/harden_network.yml

# --- AUTHENTICATION & SECURITY ---
ADMIN_USERNAME=%s
ADMIN_PASSWORD_HASH=%s
SECRET_KEY=kguard_%d
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=600

# --- NETWORK CONFIGURATION ---
ALLOWED_ORIGINS=http://localhost:8000,http://%s:8000,http://k-guard.local:8000,http://localhost:80,http://%s:80,http://k-guard.local:80 
USER_DOMAIN=%s
PROJECT_NAME=K-Guard
KGUARD_PROTECTED_NS=%s
TRIVY_CACHE_DIR=/data/trivy-cache
`,
		time.Now().Format("2006-01-02 15:04:05"), // ARG 1: Date
		rootPath,                                 // ARG 2: PROJECT_ROOT
		rootPath,                                 // ARG 3: DB_DIR
		rootPath,                                 // ARG 4: KGUARD_ANSIBLE_PATH
		username,                                 // ARG 5: ADMIN_USERNAME
		string(hash),                             // ARG 6: ADMIN_PASSWORD_HASH
		time.Now().Unix(),                        // ARG 7: SECRET_KEY (%d)
		publicIP,                                 // ARG 8: For ALLOWED_ORIGINS (%s)
		publicIP,                                 // ARG 9: For USER_DOMAIN (%s)
		protectedNamespaces)                      // ARG 10: For KGUARD_PROTECTED_NS (%s)

	return os.WriteFile(envPath, []byte(envContent), 0600)
}

func syncSecretsToK8s(rootPath string) error {
	envPath := filepath.Join(rootPath, "backend", ".env")
	
	script := fmt.Sprintf("kubectl create secret generic k-guard-secrets --from-env-file=%s -n k-guard --dry-run=client -o yaml | kubectl apply -f -", envPath)
	cmd := exec.Command("sh", "-c", script)
	
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("Secrets sync failed: %s", string(output))
	}
	
	fmt.Println("🧹 Cleaning up sensitive local configuration...")
	return os.Remove(envPath)
}

// deployFrontend ensures the compiled frontend (dist) is linked to the
// 'static' directory expected by the FastAPI backend.
func deployFrontend(rootPath string) error {
	// Define source and destination paths
	// distPath: where Vite/Vue.js outputs the production build
	// staticLink: the directory name targeted by main.py
	distPath := filepath.Join(rootPath, "frontend", "dist")
	staticLink := filepath.Join(rootPath, "static")

	// Check if the production build directory exists
	// High-criticality environments require verification before deployment steps.
	if _, err := os.Stat(distPath); os.IsNotExist(err) {
		return fmt.Errorf("frontend build directory 'dist' is missing. Please run 'npm run build' first")
	}

	// Clean up existing symbolic link or directory to prevent "file exists" errors
	// This ensures an idempotent installation process.
	os.Remove(staticLink)

	// Create a symbolic link (Symlink)
	// This provides a seamless bridge between the frontend build and the backend server.
	err := os.Symlink(distPath, staticLink)
	if err != nil {
		return fmt.Errorf("failed to create symbolic link for static files: %v", err)
	}

	fmt.Println("✅ Frontend successfully linked to static directory.")
	return nil
}

// --- K8S MANAGEMENT CLI TOOLS ---

// setupGlobalCommand creates a wrapper to interact with the K-Guard K8s environment
func setupGlobalCommand(rootPath string) error {
	// The wrapper now focuses on Kubernetes management rather than systemd
	wrapperContent := `#!/bin/bash
echo "🛡️  K-Guard Management Console"
echo "----------------------------"
if [ "$1" == "logs" ]; then
    # Fetch logs from the K-Guard deployment
    kubectl logs -l app=k-guard -n k-guard --tail=100 -f
elif [ "$1" == "pods" ]; then
    kubectl get pods -n k-guard
else
    echo "Status: Checking K-Guard deployment..."
    kubectl get deployment k-guard -n k-guard
    echo ""
    echo "Usage: kguard [logs|pods]"
fi
`
	binPath := "/usr/local/bin/kguard"
	return os.WriteFile(binPath, []byte(wrapperContent), 0755)
}

// --- BUBBLE TEA ENGINE ---

func (m model) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, m.runStep(0))
}

func (m model) runStep(step int) tea.Cmd {
	return func() tea.Msg {
		var err error
		var msg string
		time.Sleep(600 * time.Millisecond)

		switch step {
		case 0:
			msg = "Checking system architecture"
			_, err = checkAndPrepare()
		case 1:
			msg = "Verifying Docker socket (Runtime Check)"
			// ... (votre code actuel)
		case 2:
			msg = "Hashing credentials & updating .env"
			err = setupCredentials(m.projectRoot, m.adminUser, m.adminPwd)
		case 3:
			msg = "Synchronizing Kubernetes secrets"
			err = syncSecretsToK8s(m.projectRoot)
		case 4:
			msg = "Applying K8s Manifests"
			k8sPath := filepath.Join(m.projectRoot, "k8s")
			cmd := exec.Command("kubectl", "apply", "-f", k8sPath, "-n", "k-guard")
			err = cmd.Run()
		case 5:
			msg = "Deploying frontend assets (Linking static)"
			err = deployFrontend(m.projectRoot)
		case 6:
			msg = "Registering 'kguard' global command"
			err = setupGlobalCommand(m.projectRoot)
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

	s := "\n" + headerStyle.Render("🛡️ K-GUARD SYSTEM INSTALLER") + "\n"

	for _, res := range m.results {
		s += checkStyle.Render("  ✓ ") + res + "\n"
	}

	if m.quitting {
		// We detect the IP again for the final display
		displayIP := getPublicIP()
		finalMsg := fmt.Sprintf(
			"Installation Success, %s !\n\n"+
				"🚀 API: 'sudo kguard logs'\n"+
				"💻 Status: 'kguard pods'\n"+
				"🌐 Access: http://%s",
			m.adminUser,
			displayIP,
		)
		s += "\n" + footerStyle.Render(finalMsg) + "\n"
		return s
	}

	s += "\n " + m.spinner.View() + " " + m.status + "\n\n"
	s += statusStyle.Render(" [q] quit installation")
	return s
}

// --- VALIDATIONS & MAIN ---

func isStrongPassword(p string) (bool, string) {
	var (
		hasMinLen = len(p) >= 10 // Augmenté pour la sécurité
		hasUpper  = false
		hasNumber = false
		hasSpec   = false
	)
	for _, char := range p {
		switch {
		case unicode.IsUpper(char):
			hasUpper = true
		case unicode.IsNumber(char):
			hasNumber = true
		case unicode.IsPunct(char) || unicode.IsSymbol(char):
			hasSpec = true
		}
	}
	if !hasMinLen {
		return false, "10 chars min"
	}
	if !hasUpper || !hasNumber || !hasSpec {
		return false, "need uppercase, number and special char"
	}
	return true, ""
}

func main() {
	// 1. Root privileges check
	if os.Geteuid() != 0 {
		fmt.Println(errorStyle.Render("❌ Error: Administrator privileges required. Run with 'sudo'."))
		os.Exit(1)
	}

	// 2. Absolute Path Detection (Universal & Idempotent)
	// We determine the project root based on the installer's location
	exePath, err := os.Executable()
	if err != nil {
		fmt.Println(errorStyle.Render("❌ Error: Could not determine executable path."))
		os.Exit(1)
	}
	// installerDir is /.../k-guard/installer
	installerDir := filepath.Dir(exePath)
	// projectRoot is /.../k-guard
	projectRoot := filepath.Dir(installerDir)

	reader := bufio.NewReader(os.Stdin)
	fmt.Print("👤 Admin Username (min 5 chars): ")
	user, _ := reader.ReadString('\n')
	user = strings.TrimSpace(user)
	if len(user) < 5 {
		fmt.Println(errorStyle.Render("❌ Username too short."))
		os.Exit(1)
	}

	fmt.Printf("🔐 Password for %s: ", user)
	bytePass, _ := term.ReadPassword(int(syscall.Stdin))
	fmt.Println()
	pass := string(bytePass)
	if ok, help := isStrongPassword(pass); !ok {
		fmt.Printf("❌ Weak password: %s\n", help)
		os.Exit(1)
	}

	spin := spinner.New()
	spin.Spinner = spinner.Dot
	spin.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28"))

	p := tea.NewProgram(model{
		spinner:     spin,
		status:      "Launching DevSecOps Engine...",
		adminUser:   user,
		adminPwd:    pass,
		results:     make([]string, 0),
		projectRoot: projectRoot, // Passing the robust absolute path to the model
	})

	if _, err := p.Run(); err != nil {
		fmt.Printf("Runtime Error: %v\n", err)
		os.Exit(1)
	}
}
