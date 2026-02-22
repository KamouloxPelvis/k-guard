#!/bin/bash

# ==============================================================================
# 🛡️  K-GUARD DEPLOY-WIZARD (GO INSTALLER)
# Author: Kamal | Visit: https://devopsnotes.org
# ==============================================================================

# 0. Initialisation & Check Privilèges
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
    "🛡️  K-GUARD " "KUBERNETES MONITOR & SECURITY OPERATOR" "Target: http://$TARGET_URL"

# 1. AUTHENTIFICATION REGISTRY
gum style --foreground 212 "🔐 Checking Registry Access..."
if ! kubectl get secret regcred -n k-guard >/dev/null 2>&1; then
    gum spin --title "Creating ImagePullSecret..." -- \
    kubectl create secret docker-registry regcred \
        --docker-server=$CI_REGISTRY \
        --docker-username=$CI_REGISTRY_USER \
        --docker-password=$CI_REGISTRY_PASSWORD \
        -n k-guard
fi

# 2. CLEANING (Adapté)
if kubectl get namespace k-guard >/dev/null 2>&1; then
    gum style --foreground 212 "🧹 Cleaning ephemerals..."

    kubectl delete deployment,service,ingress -n k-guard --wait=true
else
    kubectl create namespace k-guard
fi

# 3. PULL & DEPLOY
gum style --foreground 212 "📥 Pulling K-Guard from GitLab Registry..."
gum style --foreground 82 "  ✓ Using remote image: $CI_REGISTRY_IMAGE/kguard-app:latest"

# 4. ORCHESTRATION
gum style --foreground 212 "🚀 Kubernetes Orchestration..."

# Application des secrets applicatifs (.env)
kubectl create secret generic k-guard-secrets \
    --from-env-file="$PROJECT_ROOT/backend/.env" \
    -n k-guard --dry-run=client -o yaml | kubectl apply -f -

# Application des manifestes
DOCKER_GID=$(stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "988")
sed "s/supplementalGroups: \[.*\]/supplementalGroups: \[$DOCKER_GID\]/g" k8s/deployment.yaml > k8s/deployment_tmp.yaml
kubectl apply -f k8s/deployment_tmp.yaml -n k-guard
rm k8s/deployment_tmp.yaml

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