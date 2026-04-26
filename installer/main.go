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
			Width(55).
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
		return "", fmt.Errorf("K-Guard is optimized for Linux")
	}
	if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
		return "", fmt.Errorf("K3s not found. Please install K3s first")
	}

	cmd := exec.Command("kubectl", "get", "ns", "k-guard")
	if err := cmd.Run(); err == nil {
		pruneCmd := exec.Command("kubectl", "apply", "-f", "../k8s/", "-n", "k-guard", "--prune", "-l", "app=k-guard", "--all")
		_ = pruneCmd.Run()
		return "Infrastructure update and cleanup completed", nil
	}

	if err := exec.Command("kubectl", "create", "namespace", "k-guard").Run(); err != nil {
		return "", fmt.Errorf("Namespace creation failed: %v", err)
	}
	return "Infrastructure initialized", nil
}

// 2. Credentials Generation & Hashing
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

USER_DOMAIN=113.30.191.17
PROJECT_NAME=K-Guard
KGUARD_PROTECTED_NS=k-guard,blog-prod,portfolio-prod
KGUARD_ANSIBLE_PATH=../infra/ansible/harden_network.yml
TRIVY_CACHE_DIR=/data/trivy-cache
`,
		time.Now().Format("2006-01-02"),
		username,
		string(hash),
		time.Now().Unix())

	return os.WriteFile("../backend/.env", []byte(envContent), 0600)
}

func syncSecretsToK8s() error {
	script := "kubectl create secret generic k-guard-secrets --from-env-file=../backend/.env -n k-guard --dry-run=client -o yaml | kubectl apply -f -"
	cmd := exec.Command("sh", "-c", script)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("Secrets sync failed: %v\n%s", err, string(output))
	}
	return nil
}

func deployK8s() error {
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
		time.Sleep(800 * time.Millisecond)

		// Récupération du chemin absolu du dossier actuel (installer)
		currentDir, _ := os.Getwd()
		// On remonte d'un cran pour atteindre la racine du projet, puis backend
		absBackendPath := filepath.Join(currentDir, "..", "backend")

		switch step {
		case 0:
			msg = "Checking system dependencies"
			_, err = checkAndPrepare()
		case 1:
			msg = "Scanning Docker socket accessibility"
			if _, errStat := os.Stat("/var/run/docker.sock"); os.IsNotExist(errStat) {
				msg = "Docker socket missing (Limited local scan)"
			} else {
				msg = "Docker socket detected"
			}
		case 2:
			msg = "Hasing credentials and generating .env"
			err = setupCredentials(m.adminUser, m.adminPwd)
		case 3:
			msg = "Initializing Trivy database"
			msg = "Trivy database ready"
		case 4:
			msg = "Synchronizing secrets with K3s"
			err = syncSecretsToK8s()
		case 5:
			msg = "Deploying K-Guard Core Manifests"
			err = deployK8s()
		case 6:
			msg = "Installing Systemd service & 'kguard' command"
			err = setupSystemdService(absBackendPath)
			if err == nil {
				err = setupGlobalCommand(absBackendPath)
			}
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
		finalMsg := fmt.Sprintf(
			"Installation Complete, %s !\n\n"+
				"🚀 Service started: 'systemctl status kguard'\n"+
				"💻 Quick launch: 'sudo kguard'\n"+
				"🌐 Accessible at: https://113.30.191.17:8443",
			m.adminUser,
		)
		s += "\n" + footerStyle.Render(finalMsg) + "\n"
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
	reader := bufio.NewReader(os.Stdin)
	var user string

	for {
		fmt.Print("👤 Enter the administrator username: ")
		input, _ := reader.ReadString('\n')
		user = strings.TrimSpace(input)

		// Nouvelle validation : non vide ET au moins 5 caractères
		if user == "" {
			fmt.Println(errorStyle.Render("❌ Username cannot be empty."))
			continue
		}
		if len(user) < 5 {
			fmt.Println(errorStyle.Render("❌ Username must be at least 5 characters long."))
			continue
		}
		break
	}

	var pass string
	for {
		// Correction du %s(MISSING) en passant 'user' en argument
		fmt.Printf("🔐 Define the password for %s: ", user)
		bytePassword, _ := term.ReadPassword(int(syscall.Stdin))
		fmt.Println()

		p1 := string(bytePassword)
		if ok, help := isStrongPassword(p1); !ok {
			fmt.Printf("❌ %s: %s\n", errorStyle.Render("Insufficiently secure"), help)
			continue
		}

		fmt.Print("🔄 Confirm password: ")
		byteConfirm, _ := term.ReadPassword(int(syscall.Stdin))
		fmt.Println()

		if p1 != string(byteConfirm) {
			fmt.Println(errorStyle.Render("❌ Passwords do not match."))
			continue
		}

		pass = p1
		break
	}

	fmt.Println(successStyle.Render("✨ Credentials validated."))

	spin := spinner.New()
	spin.Spinner = spinner.Dot
	spin.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28"))

	p := tea.NewProgram(model{
		spinner:   spin,
		status:    "Starting installation engine...",
		adminUser: user,
		adminPwd:  pass,
		results:   make([]string, 0),
	})

	if _, err := p.Run(); err != nil {
		fmt.Printf("Fatal Error: %v", err)
		os.Exit(1)
	}
}

// --- NEW FUNCTIONS FOR SYSTEMD & CLI ---

func setupSystemdService(backendDir string) error {
	// On utilise SUDO_USER pour que le service appartienne à l'utilisateur réel
	user := os.Getenv("SUDO_USER")
	if user == "" {
		user = os.Getenv("USER")
	}

	serviceContent := fmt.Sprintf(`[Unit]
Description=K-Guard Backend Service
After=network.target

[Service]
Type=simple
User=%s
WorkingDirectory=%s
ExecStart=%s/venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8443
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
`, user, backendDir, backendDir)

	err := os.WriteFile("/etc/systemd/system/kguard.service", []byte(serviceContent), 0644)
	if err != nil {
		return fmt.Errorf("failed to create service file (try running with sudo): %v", err)
	}

	exec.Command("systemctl", "daemon-reload").Run()
	exec.Command("systemctl", "enable", "kguard.service").Run()
	return exec.Command("systemctl", "restart", "kguard.service").Run()
}

func setupGlobalCommand(backendDir string) error {
	wrapperContent := fmt.Sprintf(`#!/bin/bash
cd %s
source ./venv/bin/activate
python3 -m uvicorn main:app --host 0.0.0.0 --port 8443
`, backendDir)

	binPath := "/usr/local/bin/kguard"
	err := os.WriteFile(binPath, []byte(wrapperContent), 0755)
	if err != nil {
		return fmt.Errorf("failed to create global command: %v", err)
	}
	return nil
}
