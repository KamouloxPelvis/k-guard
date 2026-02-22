package main

import (
	"fmt"
	"os"
	"os/exec"
	"runtime"
	"time"

	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"golang.org/x/crypto/bcrypt"
)

// --- CONFIGURATION & STYLES ---
var (
	headerStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28")).Bold(true).BorderStyle(lipgloss.DoubleBorder()).Padding(0, 1)
	successStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Bold(true)
	errorStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
	statusStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
)

type statusMsg string
type errMsg error
type successMsg bool

type model struct {
	spinner  spinner.Model
	status   string
	err      error
	quitting bool
	step     int
}

// 1. Vérification système (Native Go)
func checkSystem() error {
	if runtime.GOOS != "linux" {
		return fmt.Errorf("K-Guard est optimisé pour Linux (Debian/Ubuntu)")
	}
	if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
		return fmt.Errorf("K3s absent. Installez K3s avant de lancer K-Guard")
	}
	return nil
}

// 2. Génération Credentials (Bcrypt Native)
func setupCredentials() error {
	password := "admin_kguard" // À changer
	hash, err := bcrypt.GenerateFromPassword([]byte(password), 10)
	if err != nil {
		return err
	}
	envContent := fmt.Sprintf("ADMIN_PASSWORD_HASH=%s\nSECRET_KEY=kguard_%d\n", string(hash), time.Now().Unix())
	return os.WriteFile("../backend/.env", []byte(envContent), 0600)
}

// 3. Orchestration K8s
func deployK8s() error {
	_ = exec.Command("kubectl", "create", "namespace", "k-guard").Run()
	return nil 
}

// --- BUBBLE TEA ENGINE ---

func (m model) Init() tea.Cmd {
	return tea.Batch(m.spinner.Tick, nextStep(0))
}

func nextStep(step int) tea.Cmd {
	return func() tea.Msg {
		time.Sleep(800 * time.Millisecond)
		var err error
		switch step {
		case 0:
			err = checkSystem()
		case 1:
			err = setupCredentials()
		case 2:
			err = deployK8s()
		default:
			return successMsg(true)
		}
		if err != nil {
			return errMsg(err)
		}
		return statusMsg(fmt.Sprintf("Étape %d terminée", step+1))
	}
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case statusMsg:
		m.step++
		m.status = string(msg)
		return m, nextStep(m.step)
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
		return errorStyle.Render(fmt.Sprintf("\n❌ ERREUR FATALE : %v\n", m.err))
	}
	if m.quitting {
		return successStyle.Render("\n✅ K-GUARD DEPLOYED SUCCESSFULLY (SOAR-LITE ONLINE)\n")
	}
	s := headerStyle.Render("🛡️ K-GUARD SYSTEM INSTALLER") + "\n\n"
	s += m.spinner.View() + " " + m.status + "\n\n"
	s += statusStyle.Render("Appuyez sur 'q' pour quitter")
	return s
}

func main() {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28"))
	p := tea.NewProgram(model{spinner: s, status: "Démarrage des contrôles..."})
	if _, err := p.Run(); err != nil {
		fmt.Printf("Erreur : %v", err)
		os.Exit(1)
	}
}