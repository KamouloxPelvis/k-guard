import os
import sys

def verify_system_readiness():
    errors = []
    
    # 1. Check Kubeconfig
    kube_path = "/etc/rancher/k3s/k3s.yaml"
    if not os.path.exists(kube_path):
        errors.append(f"Fichier config K3s absent à {kube_path}")
    elif not os.access(kube_path, os.R_OK):
        errors.append(f"Permission de LECTURE refusée sur {kube_path}. (Astuce: sudo chown $USER /etc/rancher/k3s/k3s.yaml)")

    # 2. Check Docker Socket (Crucial pour Trivy via Sidecar)
    docker_socket = "/var/run/docker.sock"
    if not os.path.exists(docker_socket):
        errors.append(f"Socket Docker absent à {docker_socket}")
    elif not os.access(docker_socket, os.W_OK):
        errors.append(f"Permission d'ÉCRITURE refusée sur {docker_socket}. (Solution Pro: sudo usermod -aG docker $USER)")

    # 3. Check Variables d'environnement 
    env_path = os.path.join(os.path.dirname(__file__), '../backend/.env')
    if not os.path.exists(env_path):
        errors.append("Fichier .env manquant dans le dossier /backend. Lancez d'abord python3 scripts/generate_creds.py")
    else:
        with open(env_path, 'r') as f:
            content = f.read()
            if "ADMIN_PSEUDO" not in content:
                errors.append("Variable ADMIN_PSEUDO manquante dans le .env")

    if errors:
        print("\n❌ K-Guard Pre-flight Check FAILED :")
        for err in errors:
            print(f"   - {err}")
        print("\n💡 Note : Relancez votre session après un 'usermod' (logout/login).\n")
        sys.exit(1)
    
    print("✅ System Readiness : OK")

if __name__ == "__main__":
    verify_system_readiness()