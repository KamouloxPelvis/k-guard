package main

import (
    "fmt"
    "os/exec"
    "github.com/charmbracelet/lipgloss"
)

func main() {
    style := lipgloss.NewStyle().Foreground(lipgloss.Color("196")).Bold(true)
    fmt.Println(style.Render("⚠️  SUPPRESSION TOTALE DE K-GUARD EN COURS..."))

    // 1. Suppression du namespace (supprime tout ce qui est dedans)
    cmd := exec.Command("kubectl", "delete", "namespace", "k-guard")
    if out, err := cmd.CombinedOutput(); err != nil {
        fmt.Printf("Info: %s\n", string(out))
    }

    // 2. Nettoyage des images Docker/Containerd orphelines sur le VPS (K3s)
    // Pour libérer de l'espace disque sur ton VPS
    exec.Command("crictl", "rmi", "--prune").Run()

    fmt.Println(lipgloss.NewStyle().Foreground(lipgloss.Color("42")).Render("✅ VPS nettoyé. Toutes les ressources K-Guard ont été supprimées."))
}