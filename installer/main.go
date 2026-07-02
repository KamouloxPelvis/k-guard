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
// It validates the OS, ensures K3s is present, and verifies Kubernetes cluster readiness.
func checkAndPrepare() (string, error) {
	// K-Guard is strictly designed for Linux environments.
	if runtime.GOOS != "linux" {
		return "", fmt.Errorf("K-Guard is optimized for Linux systems")
	}

	// Verify K3s configuration availability.
	if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
		return "", fmt.Errorf("K3s not found. Please install K3s to host K-Guard infrastructure")
	}

	// Ensure Helm is installed to handle security components.
	if _, err := exec.LookPath("helm"); err != nil {
		return "", fmt.Errorf("helm binary not found. Please install Helm to deploy security components")
	}

	// Verify Kubernetes cluster readiness by checking node status.
	// This proactive check ensures that the K8s API is responsive before proceeding.
	cmd := exec.Command("kubectl", "get", "nodes", "--no-headers")
	out, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to communicate with K8s cluster: %v", err)
	}

	// Ensure at least one node is in the 'Ready' state.
	if !strings.Contains(string(out), "Ready") {
		return "", fmt.Errorf("Kubernetes cluster is not ready. All nodes are currently offline or unresponsive")
	}

	// Check if the infrastructure namespace exists, or create it if missing.
	checkNs := exec.Command("kubectl", "get", "ns", "k-guard")
	if err := checkNs.Run(); err != nil {
		if err := exec.Command("kubectl", "create", "namespace", "k-guard").Run(); err != nil {
			return "", fmt.Errorf("namespace creation failed: %v", err)
		}
		return "Infrastructure namespace initialized", nil
	}

	return "Infrastructure existing, ready for update", nil
}

// Helper to get the public IP of the VPS
func getPublicIP() string {
	// Adding a 5-second timeout for the network check
	cmd := exec.Command("curl", "-s", "--max-time", "5", "ifconfig.me")
	out, err := cmd.Output()
	if err != nil {
		// Log warning for infrastructure debugging
		return "127.0.0.1"
	}
	ip := strings.TrimSpace(string(out))
	// Validate that it looks like an IP
	if strings.Contains(ip, ".") {
		return ip
	}
	return "127.0.0.1"
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

	// Hash the password for security
	hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
	if err != nil {
		return fmt.Errorf("failed to hash password: %v", err)
	}

	envPath := filepath.Join(rootPath, "backend", ".env")

	// --- Construction of the configuration string ---
	var sb strings.Builder
	sb.WriteString("# K-GUARD SYSTEM CONFIGURATION\n")
	sb.WriteString(fmt.Sprintf("# Generated on: %s\n\n", time.Now().Format("2006-01-02 15:04:05")))

	sb.WriteString("# --- PATH RESOLUTION ---\n")
	sb.WriteString(fmt.Sprintf("PROJECT_ROOT=%s\n", rootPath))

	// Determine database directory based on environment
	var dbDir string
	if os.Getenv("KGUARD_ENV") == "docker" {
		dbDir = "/app/data"
	} else {
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

	sb.WriteString("# --- NETWORK CONFIGURATION ---\n")
	// Using the dynamically retrieved publicIP here
	sb.WriteString(fmt.Sprintf("ALLOWED_ORIGINS=http://localhost:8000,http://%s:8000,http://k-guard.local:8000\n", publicIP))
	sb.WriteString(fmt.Sprintf("USER_DOMAIN=%s\n", publicIP))
	sb.WriteString("PROJECT_NAME=K-Guard\n")
	sb.WriteString("KGUARD_PROTECTED_NS=k-guard\n")

	// Write the configuration to the file with restricted permissions (0600)
	err = os.WriteFile(envPath, []byte(sb.String()), 0600)
	if err != nil {
		return fmt.Errorf("failed to write .env: %v", err)
	}

	// Verify the file was actually created
	if _, err := os.Stat(envPath); os.IsNotExist(err) {
		return fmt.Errorf("critical failure: .env file creation failed")
	}

	return nil
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

// runKubeCommand executes shell commands and captures standard error for professional debugging.
// This ensures that deployment failures are transparent and actionable.
func runKubeCommand(name, cmdStr string) error {
	cmd := exec.Command("sh", "-c", cmdStr)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("Step '%s' failed: %s | Error: %v", name, string(out), err)
	}
	return nil
}

// runStep manages the deployment pipeline sequence.
// It enforces order-of-operations to prevent dependency mismatches in the K8s cluster.
func (m model) runStep(step int) tea.Cmd {
	return func() tea.Msg {
		kubeConfig := "/etc/rancher/k3s/k3s.yaml"
		os.Setenv("KUBECONFIG", kubeConfig)

		// Define the pipeline of operations as an ordered slice of steps.
		// Each step is validated sequentially to ensure infrastructure integrity.
		pipeline := []Step{
			{"Checking system architecture", func() error { _, err := checkAndPrepare(); return err }},
			{"Hashing credentials & updating .env", func() error { return setupCredentials(m.projectRoot, m.adminUser, m.adminPwd) }},
			{"Synchronizing Kubernetes secrets", func() error { return syncSecretsToK8s(m.projectRoot) }},

			// 1. Deploy Core Infrastructure (RBAC, Namespaces, Services)
			{"Applying Core K8s Manifests", func() error {
				return runKubeCommand("Core", "kubectl apply -f "+filepath.Join(m.projectRoot, "k8s/core/"))
			}},

			// 2. Deploy Data Layer (Elasticsearch)
			{"Deploying ELK Stack (Data Layer)", func() error {
				return runKubeCommand("ELK", "kubectl apply -f "+filepath.Join(m.projectRoot, "k8s/elk/"))
			}},

			// 3. Deploy Security Agents (Falco & Fluent-bit)
			{"Deploying Runtime Security (Falco)", func() error {
				cmd := "helm upgrade --install falco falcosecurity/falco -n k-guard -f " + filepath.Join(m.projectRoot, "k8s/falco/values-falco.yaml")
				return runKubeCommand("Falco", cmd) 
			}},
			{"Deploying Fluent-bit (Log Collector)", func() error {
				return runKubeCommand("Fluent-bit", "kubectl apply -f "+filepath.Join(m.projectRoot, "k8s/fluentbit/"))
			}},

			// 4. Deploy K-Guard Application
			{"Deploying K-Guard App", func() error {
				return runKubeCommand("App", "kubectl apply -f "+filepath.Join(m.projectRoot, "k8s", "core"))
			}},

			// 5. Post-deployment configuration
			{"Deploying frontend assets", func() error { return deployFrontend(m.projectRoot) }},
			{"Registering 'kguard' command", func() error { return setupGlobalCommand(m.projectRoot) }},
		}

		if step >= len(pipeline) {
			return successMsg(true)
		}

		current := pipeline[step]
		time.Sleep(500 * time.Millisecond) // Ensure UI pacing for the installer feedback

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
