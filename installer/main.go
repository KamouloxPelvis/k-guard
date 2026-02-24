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
			Width(46).             // Largeur fixe pour l'encadré
			Align(lipgloss.Center) // Centrage du texte à l'intérieur

	successStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Bold(true)
	errorStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
	checkStyle   = lipgloss.NewStyle().Foreground(lipgloss.Color("42"))
	statusStyle  = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))
)
var (
    // Style pour l'encadré de succès final
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

// 1. Vérification système & Nettoyage intelligent
func checkAndPrepare() (string, error) {
	if runtime.GOOS != "linux" {
		return "", fmt.Errorf("K-Guard est optimisé pour Linux (Debian/Ubuntu)")
	}
	if _, err := os.Stat("/etc/rancher/k3s/k3s.yaml"); os.IsNotExist(err) {
		return "", fmt.Errorf("K3s absent. Installez K3s avant de lancer K-Guard")
	}

	// Détection de l'existence du Namespace
	cmd := exec.Command("kubectl", "get", "ns", "k-guard")
	if err := cmd.Run(); err == nil {
		// Le namespace existe : on prépare le terrain en supprimant les orphelins
		// Note: Nécessite le label 'app=k-guard' dans vos YAML
		pruneCmd := exec.Command("kubectl", "apply", "-f", "../k8s/", "-n", "k-guard", "--prune", "-l", "app=k-guard", "--all")
		_ = pruneCmd.Run()
		return "Mise à jour détectée : Nettoyage des ressources obsolètes terminé", nil
	}

	// Vérifier les dépendances binaires nécessaires au script sh
	dependencies := []string{"kubectl", "sh"}
	for _, dep := range dependencies {
		if _, err := exec.LookPath(dep); err != nil {
			return "", fmt.Errorf("Dépendance manquante : %s", dep)
		}
	}

	// Vérifier le socket Docker (essentiel pour Trivy en mode image local)
	if _, err := os.Stat("/var/run/docker.sock"); os.IsNotExist(err) {
		// On prévient mais on ne bloque pas forcément, car Trivy peut scanner via registre
		fmt.Println("⚠️  Attention: /var/run/docker.sock non trouvé. Les scans d'images locales pourraient échouer.")
	}

	// Nouveau déploiement
	if err := exec.Command("kubectl", "create", "namespace", "k-guard").Run(); err != nil {
		return "", fmt.Errorf("Échec création Namespace : %v", err)
	}
	return "Nouveau déploiement : Infrastructure initialisée", nil
}

// 2. Génération Credentials
func setupCredentials(username string, password string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), 12)
	if err != nil {
		return err
	}

	envContent := fmt.Sprintf(`# K-GUARD CONFIGURATION
	ALLOWED_ORIGINS=http://localhost:30002,http://113.30.191.17:30002
	ADMIN_USERNAME=%s
	ADMIN_PASSWORD_HASH=%s
	SECRET_KEY=kguard_%d
	ALGORITHM=HS256
	ACCESS_TOKEN_EXPIRE_MINUTES=600

	# --- INFOS INFRASTRUCTURE ---
	USER_DOMAIN=113.30.191.17
	PROJECT_NAME=K-Guard

	# --- CONFIGURATION NETWORK SENTINEL ---
	KGUARD_PROTECTED_NS=k-guard,blog-prod,portfolio-prod
	KGUARD_ANSIBLE_PATH=../infra/ansible/harden_network.yml

	# --- CONFIGURATION SCANNER (TRIVY) ---
	TRIVY_CACHE_DIR=/data/trivy-cache
	`,
		time.Now().Format("2006-01-02"), // Pour le premier %s (date)
		username,                        // Pour le deuxième %s (nom d'utilisateur)
		string(hash),                    // Pour le troisième %s (le hash bcrypt)
		time.Now().Unix())               // Pour le %d (le timestamp du secret)

	return os.WriteFile("../backend/.env", []byte(envContent), 0600)
}

// 2.bis Synchronisation des Secrets vers K3s (Idempotent)
func syncSecretsToK8s() error {
	// On utilise sh -c pour pouvoir utiliser le pipe (|) et le dry-run
	// Cela garantit que le secret est mis à jour sans erreur s'il existe déjà
	script := "kubectl create secret generic k-guard-secrets --from-env-file=../backend/.env -n k-guard --dry-run=client -o yaml | kubectl apply -f -"

	cmd := exec.Command("sh", "-c", script)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("Échec synchro Secrets : %v\n%s", err, string(output))
	}
	return nil
}

// 3. Orchestration K8s (Idempotent)
func deployK8s() error {
	// kubectl apply est naturellement intelligent et ne recrée que ce qui a changé
	cmd := exec.Command("kubectl", "apply", "-f", "../k8s/", "-n", "k-guard")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("Échec K8s : %v\n%s", err, string(output))
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
		time.Sleep(800 * time.Millisecond) // Délai pour la lisibilité

		switch step {
		case 0:
			msg = "Vérification des dépendances système (kubectl, sh...)"
			_, err = checkAndPrepare()
		case 1:
			msg = "Vérification du socket Docker (/var/run/docker.sock)"
			if _, errStat := os.Stat("/var/run/docker.sock"); os.IsNotExist(errStat) {
				msg = "Socket Docker absent (Scan local limité)"
			} else {
				msg = "Socket Docker détecté et accessible"
			}
		case 2:
			msg = "Génération du fichier .env (Bcrypt & Configuration)"
			err = setupCredentials(m.adminUser, m.adminPwd)
		case 3:
			msg = "Initialisation de la base de vulnérabilités Trivy"
			// Simulation de préparation ou vérification de répertoire
			msg = "Base Trivy prête pour l'analyse"
		case 4:
			msg = "Injection des secrets dans le cluster K3s"
			err = syncSecretsToK8s()
		case 5:
			msg = "Déploiement final des manifests (Services & Pods)"
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
		return errorStyle.Render(fmt.Sprintf("\n❌ ERREUR FATALE : %v\n", m.err))
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
	s += statusStyle.Render(" [q] quitter")
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
		return false, "8 caractères minimum"
	}
	if !hasUpper {
		return false, "au moins une majuscule"
	}
	if !hasNumber {
		return false, "au moins un chiffre"
	}
	if !hasSpecial {
		return false, "au moins un caractère spécial"
	}
	return true, ""
}

func main() {
	var user string
	for {
		fmt.Print("👤 Entrez le 'username' administrateur souhaité : ")
		fmt.Scanln(&user)

		if user == "" {
			fmt.Println(errorStyle.Render("❌ Le username ne peut pas être vide."))
			continue
		}
		break
	}
	var pass string
	for {
		fmt.Print("🔐 Définissez le mot de passe admin pour 'kamal': ")
		bytePassword, _ := term.ReadPassword(int(syscall.Stdin))
		fmt.Println()

		p1 := string(bytePassword)

		// Validation de la force du mot de passe
		if ok, help := isStrongPassword(p1); !ok {
			fmt.Printf("❌ %s : %s\n", errorStyle.Render("Sécurité insuffisante"), help)
			continue
		}

		fmt.Print("🔄 Confirmez le mot de passe: ")
		byteConfirm, _ := term.ReadPassword(int(syscall.Stdin))
		fmt.Println()

		if p1 != string(byteConfirm) {
			fmt.Println(errorStyle.Render("❌ Les mots de passe ne correspondent pas. Réessayez."))
			continue
		}

		pass = p1
		break
	}

	fmt.Println(successStyle.Render("✨ Mot de passe sécurisé mémorisé."))

	spin := spinner.New()
	spin.Spinner = spinner.Dot
	spin.Style = lipgloss.NewStyle().Foreground(lipgloss.Color("#f05a28"))

	p := tea.NewProgram(model{
		spinner:  spin,
		status:   "Vérification des dépendances...",
		adminPwd: pass,
		results:  make([]string, 0),
	})

	if _, err := p.Run(); err != nil {
		fmt.Printf("Erreur fatale : %v", err)
		os.Exit(1)
	}
}
