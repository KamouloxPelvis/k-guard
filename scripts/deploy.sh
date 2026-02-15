#!/bin/bash

# ==============================================================================
# 🛡️  K-GUARD CYBER-WIZARD (GUM + STABLE FUSION)
# Author: Kamal | Visit: https://devopsnotes.org
# ==============================================================================

# 0. Initialisation
cd "$(dirname "$0")/.." || exit

# Check Gum
command -v gum >/dev/null 2>&1 || { echo "Veuillez installer 'gum' d'abord."; exit 1; }

# Check .env
if [ -f "backend/.env" ]; then
    source backend/.env
else
    echo "❌ Erreur: .env non trouvé. Lancez 'python3 scripts/generate_creds.py' d'abord."
    exit 1
fi

# Récupération IP/Domaine
VPS_IP=$(hostname -I | awk '{print $1}')
TARGET_URL=${USER_DOMAIN:-$VPS_IP}

# --- Header Style Gum ---
clear
gum style \
    --foreground 212 --border-foreground 212 --border double \
    --align center --width 60 --margin "1 2" --padding "0 1" \
    "🛡️  K-GUARD " "K3S MONITOR & SECURITY OPERATOR" "Target: http://$TARGET_URL"

# 1. CLEANING
if kubectl get namespace k-guard >/dev/null 2>&1; then
    gum spin --spinner dot --title "Purging old namespace..." -- \
        kubectl delete namespace k-guard --wait=true
fi
gum style --foreground 82 "  ✓ Environment cleared"

# 2. BUILDING
gum style --foreground 212 "🏗️  Starting Binary Builds..."

gum spin --spinner pulse --title "Compiling Backend Engine (+Trivy)..." -- \
    docker build --no-cache -t k-guard-backend:latest ./backend

# CORRECTION: Plus besoin de VITE_API_URL car on utilise des chemins relatifs (/api)
gum spin --spinner pulse --title "Compiling Frontend Interface..." -- \
    docker build --no-cache -t k-guard-frontend:latest ./frontend

# Vérification build
if [[ "$(docker images -q k-guard-frontend:latest 2> /dev/null)" == "" ]]; then
    gum style --foreground 196 "❌ ERROR: Frontend build failed!"
    exit 1
fi
gum style --foreground 82 "  ✓ Images generated"

# 3. IMPORTING (Transfert Docker -> K3s Containerd)
gum style --foreground 212 "📦 Injecting into K3s Registry..."
docker save k-guard-backend:latest -o backend.tar
docker save k-guard-frontend:latest -o frontend.tar

gum spin --spinner line --title "Importing layers to K3s..." -- \
    bash -c "sudo k3s ctr images import backend.tar && sudo k3s ctr images import frontend.tar"

rm backend.tar frontend.tar
gum style --foreground 82 "  ✓ Registry updated"

# 4. ORCHESTRATION
gum style --foreground 212 "🚀 Kubernetes Orchestration..."

# Namespace & Secrets
kubectl create namespace k-guard --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic k-guard-secrets --from-env-file=backend/.env -n k-guard --dry-run=client -o yaml | kubectl apply -f -

# Manifests (Assure-toi que le fichier Ingress s'appelle bien k8s/ingress.yaml)
kubectl apply -f k8s/deployment.yaml -n k-guard > /dev/null
kubectl apply -f k8s/service.yaml -n k-guard > /dev/null
kubectl apply -f k8s/rbac.yaml -n k-guard > /dev/null
kubectl apply -f k8s/ingress.yaml -n k-guard > /dev/null

gum style --foreground 82 "  ✓ Manifests & Ingress applied"

# 5. FINAL STABILIZATION
echo ""
gum style --foreground 212 "📡 Final Health Check..."

# On attend que le déploiement soit prêt
if gum spin --spinner points --title "Waiting for Liveness Probes..." -- \
    kubectl rollout status deployment/k-guard-deployment -n k-guard --timeout=120s; then
    
    # CORRECTION URLs : On pointe sur la racine pour le dash et /api pour la santé
    gum style \
        --foreground 82 --border-foreground 82 --border rounded \
        --align center --width 60 --margin "1" --padding "1" \
        "✅ K-GUARD IS ONLINE" \
        "Dashboard: http://$TARGET_URL" \
        "API Health: http://$TARGET_URL/api/k3s/health" \
        "Visit https://devopsnotes.org"
else
    gum style --foreground 196 --bold "❌ STABILIZATION FAILED"
    echo "🔍 Debugging Pods :"
    kubectl get pods -n k-guard
    echo "📋 Backend Logs :"
    kubectl logs -l app=k-guard -c backend -n k-guard --tail=20
    echo "📋 Recent Events :"
    kubectl get events -n k-guard --sort-by='.lastTimestamp' | tail -n 10
    exit 1
fi