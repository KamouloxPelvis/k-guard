package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"github.com/charmbracelet/bubbles/spinner"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// --- STYLES ---
var (
	keywordStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28")).Bold(true).Render
	successStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Bold(true).Render
	errorStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true).Render
	logStyle     = lipgloss.NewStyle().Foreground(lipgloss.Color("240")).Italic(true).Render
)

// --- MESSAGES ---
type logMsg string
type deployFinishedMsg struct{ err error }

// --- MODEL ---
type model struct {
	spinner  spinner.Model
	logs     []string
	err      error
	done     bool
}

func initialModel() model {
	s := spinner.New()
	s.Spinner = spinner.Dot
	s.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28"))
	return model{
		spinner: s,
		logs:    []string{"Initialisation du déploiement..."},
	}
}

// --- LOGIQUE DE STREAMING ---
// Cette fonction lance le script et envoie chaque ligne au programme Bubble Tea
func runDeploy(p *tea.Program) {
	cmd := exec.Command("bash", "../scripts/deploy.sh")
		
	// On récupère la sortie standard et les erreurs
	stdout, _ := cmd.StdoutPipe()
	cmd.Stderr = cmd.Stdout
	
	multi := io.TeeReader(stdout, os.Stdout) // Optionnel: garde aussi dans le terminal réel
	_ = multi // Pour l'instant on utilise direct stdout

	scanner := bufio.NewScanner(stdout)
	
	go func() {
		cmd.Start()
		for scanner.Scan() {
			// On envoie chaque ligne au programme via p.Send
			p.Send(logMsg(scanner.Text()))
		}
		err := cmd.Wait()
		p.Send(deployFinishedMsg{err: err})
	}()
}

func (m model) Init() tea.Cmd {
	return m.spinner.Tick
}

// --- UPDATE ---
func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "ctrl+c" || msg.String() == "q" {
			return m, tea.Quit
		}
	case spinner.TickMsg:
		var cmd tea.Cmd
		m.spinner, cmd = m.spinner.Update(msg)
		return m, cmd
	case logMsg:
		// On ajoute le nouveau log et on ne garde que les 5 derniers
		m.logs = append(m.logs, string(msg))
		if len(m.logs) > 5 {
			m.logs = m.logs[1:]
		}
		return m, nil
	case deployFinishedMsg:
		m.done = true
		m.err = msg.err
		return m, tea.Quit
	}
	return m, nil
}

// --- VIEW ---
func (m model) View() string {
	if m.err != nil {
		return fmt.Sprintf("\n  %s %v\n\n", errorStyle("❌ ERROR:"), m.err)
	}
	if m.done {
		return fmt.Sprintf("\n  %s %s\n\n", successStyle("✓"), "K-GUARD DEPLOYMENT COMPLETE")
	}

	// Affichage du spinner et du titre
	s := fmt.Sprintf("\n  %s %s\n\n", m.spinner.View(), keywordStyle("SHIELDING K-GUARD SYSTEM..."))
	
	// Affichage des logs (les 5 dernières lignes)
	for _, l := range m.logs {
		// On tronque si la ligne est trop longue pour rester propre
		displayLog := l
		if len(l) > 60 { displayLog = l[:57] + "..." }
		s += fmt.Sprintf("    %s\n", logStyle(displayLog))
	}

	return s
}

func main() {
	m := initialModel()
	p := tea.NewProgram(m)

	// On lance le script de déploiement en arrière-plan
	go runDeploy(p)

	if _, err := p.Run(); err != nil {
		fmt.Printf("Error: %v", err)
		os.Exit(1)
	}
}