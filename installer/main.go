package main

import (
	"bufio"
	"crypto/rand"
	"encoding/hex"
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

// checkAndPrepare performs environment sanity checks before deployment.
// It validates the Operating System, the presence of critical binaries,
// and ensures the Kubernetes namespace is properly initialized.
func checkAndPrepare() (string, error) {
	// K-Guard is strictly designed for Linux environments.
	if runtime.GOOS != "linux" {
		return "", fmt.Errorf("K-Guard is optimized for Linux systems")
	}

	// Verify K3s configuration availability.
	// K3s serves as the foundation for the K-Guard infrastructure.
	if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
		return "", fmt.Errorf("K3s not found. Please install K3s to host K-Guard infrastructure")
	}

	// Ensure Helm is installed to handle security components deployment.
	// This proactive check prevents runtime failures during the install phase.
	if _, err := exec.LookPath("helm"); err != nil {
		return "", fmt.Errorf("helm binary not found. Please install Helm to deploy security components")
	}

	// Check if the infrastructure namespace already exists.
	// This enables idempotency for the installation process.
	cmd := exec.Command("sudo", "-n","kubectl", "get", "ns", "k-guard")
	if err := cmd.Run(); err == nil {
		return "Infrastructure existing, ready for update", nil
	}

	// Create the namespace if it doesn't exist.
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

func generateSecureToken(length int) string {
	b := make([]byte, length)
	if _, err := rand.Read(b); err != nil {
		return "fallback_token_secure"
	}
	return hex.EncodeToString(b)
}

func setupCredentials(rootPath, username, password string) error {
	publicIP := getPublicIP()

	hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
	if err != nil {
		return fmt.Errorf("failed to hash password: %v", err)
	}

	// Generating random credentials for the internal Security SIEM
	wazuhUser := "wazuh_admin"
	wazuhPwd := generateSecureToken(16)

	envPath := filepath.Join(rootPath, "backend", ".env")

	// Constructing the configuration string cleanly
	var sb strings.Builder
	sb.WriteString("# K-GUARD SYSTEM CONFIGURATION\n")
	sb.WriteString(fmt.Sprintf("# Generated on: %s\n\n", time.Now().Format("2006-01-02 15:04:05")))

	sb.WriteString("# --- PATH RESOLUTION ---\n")
	sb.WriteString(fmt.Sprintf("PROJECT_ROOT=%s\n", rootPath))
	var dbDir string
	if os.Getenv("KGUARD_ENV") == "docker" {
		dbDir = "/app/data"
	} else {
		// Chemin local pour ton installation sur ton VPS
		dbDir = filepath.Join(rootPath, "backend", "data")
	}
	sb.WriteString(fmt.Sprintf("DB_DIR=%s\n", dbDir))
	sb.WriteString(fmt.Sprintf("KGUARD_ANSIBLE_PATH=%s/infra/ansible/harden_network.yml\n\n", rootPath))

	sb.WriteString("# --- AUTHENTICATION & SECURITY ---\n")
	sb.WriteString(fmt.Sprintf("ADMIN_USERNAME=%s\n", username))
	sb.WriteString(fmt.Sprintf("ADMIN_PASSWORD_HASH=%s\n", string(hash)))
	sb.WriteString(fmt.Sprintf("SECRET_KEY=kguard_%d\n", time.Now().Unix()))
	sb.WriteString("ALGORITHM=HS256\n")
	sb.WriteString("ACCESS_TOKEN_EXPIRE_MINUTES=600\n\n")

	sb.WriteString("# --- WAZUH INTEGRATION ---\n")
	sb.WriteString(fmt.Sprintf("WAZUH_API_URL=https://wazuh-manager:55000\n"))
	sb.WriteString(fmt.Sprintf("WAZUH_USERNAME=%s\n", wazuhUser))
	sb.WriteString(fmt.Sprintf("WAZUH_PASSWORD=%s\n\n", wazuhPwd))

	sb.WriteString("# --- NETWORK CONFIGURATION ---\n")
	sb.WriteString(fmt.Sprintf("ALLOWED_ORIGINS=http://localhost:8000,http://%s:8000,http://k-guard.local:8000\n", publicIP))
	sb.WriteString(fmt.Sprintf("USER_DOMAIN=%s\n", publicIP))
	sb.WriteString("PROJECT_NAME=K-Guard\n")
	sb.WriteString("KGUARD_PROTECTED_NS=k-guard\n")

	return os.WriteFile(envPath, []byte(sb.String()), 0600)
}

func syncSecretsToK8s(rootPath string) error {
	envPath := filepath.Join(rootPath, "backend", ".env")
	kubeConfig := "/etc/rancher/k3s/k3s.yaml"

	script := fmt.Sprintf(
		"KUBECONFIG=%s kubectl create secret generic k-guard-secrets "+
			"--from-env-file=%s -n k-guard --dry-run=client -o yaml | "+
			"KUBECONFIG=%s kubectl apply -f -",
		kubeConfig, envPath, kubeConfig,
	)

	cmd := exec.Command("sh", "-c", script)
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("Secrets sync failed: %s | Error: %v", string(output), err)
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

// Step defines a single deployment action for the pipeline.
type Step struct {
	Name string
	Run  func() error
}

func (m model) runStep(step int) tea.Cmd {
	return func() tea.Msg {
		// Define the pipeline of operations as an ordered slice of steps.
		// This improves readability and maintainability.
		pipeline := []Step{
			{"Checking system architecture", func() error { _, err := checkAndPrepare(); return err }},
			{"Hashing credentials & updating .env", func() error { return setupCredentials(m.projectRoot, m.adminUser, m.adminPwd) }},
			{"Synchronizing Kubernetes secrets", func() error { return syncSecretsToK8s(m.projectRoot) }},
			{"Applying K8s Manifests", func() error {
				k8sPath := filepath.Join(m.projectRoot, "k8s")
				kubeConfig := "/etc/rancher/k3s/k3s.yaml"
				cmdStr := fmt.Sprintf("KUBECONFIG=%s kubectl apply -f %s", kubeConfig, k8sPath)
				cmd := exec.Command("sh", "-c", cmdStr)
				out, err := cmd.CombinedOutput()
				if err != nil {
					return fmt.Errorf("%s | Err: %v", string(out), err)
				}
				return nil
			}},
			{"Deploying frontend assets (Linking static)", func() error { return deployFrontend(m.projectRoot) }},
			{"Registering 'kguard' global command", func() error { return setupGlobalCommand(m.projectRoot) }},

			// DeployWazuhStack handles the installation of the Wazuh server within the cluster.
			// This provides a centralized security monitoring and incident response platform.
			{"Installing Wazuh Security Stack", func() error {
				kubeConfig := "KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
				path, _ := exec.LookPath("helm")

				// Using the official stable repository endpoint
				steps := []string{
					fmt.Sprintf("%s %s repo add wazuh https://wazuh.github.io/wazuh-charts/", kubeConfig, path), // Note the trailing slash
					fmt.Sprintf("%s %s repo update", kubeConfig, path),
					fmt.Sprintf("%s %s upgrade --install wazuh wazuh/wazuh -n wazuh --create-namespace", kubeConfig, path),
				}

				for _, s := range steps {
					cmd := exec.Command("sh", "-c", s)
					if out, err := cmd.CombinedOutput(); err != nil {
						return fmt.Errorf("Wazuh installation failed: %s | Err: %v", string(out), err)
					}
				}
				return nil
			}},

			{"Installing Security Stack (Falco + Sidekick)", func() error {
				kubeConfig := "KUBECONFIG=/etc/rancher/k3s/k3s.yaml"
				path, _ := exec.LookPath("helm")
				wazuhManagerHost := "wazuh-manager.wazuh.svc.cluster.local"

				// We consolidate into a single release named 'kguard-security'
				// Falcosidekick is enabled as a dependency within the Falco chart
				steps := []string{
					fmt.Sprintf("%s %s repo add falcosecurity https://falcosecurity.github.io/charts", kubeConfig, path),
					fmt.Sprintf("%s %s repo update", kubeConfig, path),
					fmt.Sprintf("%s %s upgrade --install kguard-security falcosecurity/falco -n falco --create-namespace "+
						"--set driver.kind=modern_ebpf "+
						"--set controller.kind=daemonset "+
						"--set falcosidekick.enabled=true "+
						"--set falcosidekick.config.wazuh.enabled=true "+
						"--set falcosidekick.config.wazuh.host=%s "+
						"--set falcosidekick.config.wazuh.port=1514",
						kubeConfig, path, wazuhManagerHost),
				}

				for _, s := range steps {
					cmd := exec.Command("sh", "-c", s)
					if out, err := cmd.CombinedOutput(); err != nil {
						return fmt.Errorf("Security stack installation failed: %s | Err: %v", string(out), err)
					}
				}
				return nil
			}},
		}

		if step >= len(pipeline) {
			return successMsg(true)
		}

		current := pipeline[step]
		time.Sleep(600 * time.Millisecond) // Smooth UI pacing

		if err := current.Run(); err != nil {
			return errMsg(err)
		}
		return statusMsg(current.Name)
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
