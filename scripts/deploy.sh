#!/bin/bash

# ==============================================================================
# 🛡️  K-GUARD CYBER-WIZARD (GUM + STABLE FUSION)
# Author: Kamal | Visit: https://devopsnotes.org
# ==============================================================================

# 0. Initialisation & Check Privilèges
# On définit proprement la racine du projet pour les chemins relatifs
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit

if [ "$EUID" -ne 0 ]; then
  echo "⚠️  K-Guard nécessite des privilèges élevés pour l'injection réseau et K3s."
  echo "Veuillez relancer avec : sudo $0"
  exit 1
fi

export KUBECONFIG=${KUBECONFIG:-/etc/rancher/k3s/k3s.yaml}

# Check Gum
command -v gum >/dev/null 2>&1 || { echo "Veuillez installer 'gum' d'abord."; exit 1; }

# Check .env (Chemin absolu via PROJECT_ROOT)
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
    source "$PROJECT_ROOT/backend/.env"
else
    gum style --foreground 196 "❌ Erreur: .env non trouvé à $PROJECT_ROOT/backend/.env"
    exit 1
fi

VPS_IP=$(hostname -I | awk '{print $1}')
TARGET_URL=${USER_DOMAIN:-$VPS_IP}

clear
gum style \
    --foreground 212 --border-foreground 212 --border double \
    --align center --width 60 --margin "1 2" --padding "0 1" \
    "🛡️  K-GUARD " "K3S MONITOR & SECURITY OPERATOR" "Target: http://$TARGET_URL"

# 1. CLEANING (Smart Clean)
if kubectl get namespace k-guard >/dev/null 2>&1; then
    gum style --foreground 212 "🧹 Cleaning up old resources (keeping storage)..."
    # On supprime les ressources éphémères mais ON GARDE le Namespace et les PVCs
    kubectl delete deployment,service,ingress,secret -n k-guard --all --wait=true
else
    kubectl create namespace k-guard
fi
gum style --foreground 82 "  ✓ Environment ready"

# 2. BUILDING
gum style --foreground 212 "🏗️  Starting Binary Builds..."
gum spin --spinner pulse --title "Compiling Backend Engine (+Trivy)..." -- \
    docker build --no-cache -t k-guard-backend:latest ./backend
gum spin --spinner pulse --title "Compiling Frontend Interface..." -- \
    docker build --no-cache -t k-guard-frontend:latest ./frontend
gum style --foreground 82 "  ✓ Images generated"

# 3. IMPORTING
gum style --foreground 212 "📦 Injecting into K3s Registry..."
docker save k-guard-backend:latest -o backend.tar
docker save k-guard-frontend:latest -o frontend.tar
gum spin --spinner line --title "Importing layers to K3s..." -- \
    bash -c "k3s ctr images import backend.tar && k3s ctr images import frontend.tar"
rm -f backend.tar frontend.tar
gum style --foreground 82 "  ✓ Registry updated"

# 4. ORCHESTRATION
gum style --foreground 212 "🚀 Kubernetes Orchestration..."

# Application du Secret (Correctement pointé vers PROJECT_ROOT)
kubectl create secret generic k-guard-secrets \
    --from-env-file="$PROJECT_ROOT/backend/.env" \
    -n k-guard --dry-run=client -o yaml | kubectl apply -f -

# Application du stockage et des ressources de base
for manifest in k-guard-pvc service rbac ingress; do
    if [ -f "k8s/$manifest.yaml" ]; then
        kubectl apply -f "k8s/$manifest.yaml" -n k-guard > /dev/null
    fi
done

# --- GESTION DYNAMIQUE DU GID DOCKER ---
DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "988")
gum style --foreground 212 "🛠️  Adaptation du GID Docker ($DOCKER_GID) pour la portabilité..."

# On applique le deployment avec le patch de GID
sed "s/supplementalGroups: \[.*\]/supplementalGroups: \[$DOCKER_GID\]/g" k8s/deployment.yaml > k8s/deployment_tmp.yaml
kubectl apply -f k8s/deployment_tmp.yaml -n k-guard > /dev/null
rm k8s/deployment_tmp.yaml

gum style --foreground 82 "  ✓ Manifests & Ingress applied"

# 5. FINAL STABILIZATION
echo ""
gum style --foreground 212 "📡 Final Health Check..."

if gum spin --spinner points --title "Waiting for Liveness Probes..." -- \
    kubectl rollout status deployment/k-guard-deployment -n k-guard --timeout=120s; then
    
    gum style \
        --foreground 82 --border-foreground 82 --border rounded \
        --align center --width 60 --margin "1" --padding "1" \
        "✅ K-GUARD IS ONLINE" \
        "Dashboard: http://$TARGET_URL" \
        "API Health: http://$TARGET_URL/health" \
        "Visit: https://devopsnotes.org"
else
    gum style --foreground 196 --bold "❌ STABILIZATION FAILED"
    kubectl get pods -n k-guard
    exit 1
fi