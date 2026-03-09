#!/bin/bash
# --- K-Guard SRE Connectivity Validator ---
# Compliance: Cisco DevNet Standard for In-Cluster Diagnostics
set -e

# 0. SRE ENVIRONMENT SETUP
# Force kubectl to use the internal ServiceAccount identity
export KUBERNETES_SERVICE_HOST=kubernetes.default.svc
export KUBERNETES_SERVICE_PORT=443

# 1. DYNAMIC SCOPING
# Discover the first non-system namespace with running workloads
TARGET_NS=$(kubectl get pods -A --field-selector=status.phase=Running -o jsonpath='{.items[?(@.metadata.namespace!="kube-system")].metadata.namespace}' | tr ' ' '\n' | head -n 1)

if [ -z "$TARGET_NS" ]; then 
    echo "❌ ERROR: No target namespace found for audit."
    exit 1
fi

# Select a target pod and extract its network metadata
TEST_POD=$(kubectl get pods -n "$TARGET_NS" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
POD_IP=$(kubectl get pod -n "$TARGET_NS" "$TEST_POD" -o jsonpath='{.status.podIP}')
POD_PORT=$(kubectl get pod -n "$TARGET_NS" "$TEST_POD" -o jsonpath='{.spec.containers[*].ports[*].containerPort}' | awk '{print $1}')
POD_PORT=${POD_PORT:-80}

echo "--------------------------------------------------------"
echo "🔍 K-GUARD CONNECTIVITY AUDIT"
echo "📍 Namespace : $TARGET_NS"
echo "🚀 Target    : $TEST_POD ($POD_IP:$POD_PORT)"
echo "--------------------------------------------------------"

# 2. EPHEMERAL DIAGNOSTIC DEPLOYMENT
echo "⏳ Deploying sentinel-debug pod (Netshoot)..."

# Pre-emptive cleanup to avoid name collisions
kubectl delete pod sentinel-debug -n "$TARGET_NS" --grace-period=0 --force > /dev/null 2>&1 || true

# Launching the diagnostic container
kubectl run sentinel-debug -n "$TARGET_NS" \
    --image=nicolaka/netshoot \
    --restart=Never \
    --overrides='{"spec": {"terminationGracePeriodSeconds": 0}}' \
    -- sleep 60 > /dev/null 2>&1

# Wait for readiness with a strict timeout to prevent UI hang
if ! kubectl wait --for=condition=Ready pod/sentinel-debug -n "$TARGET_NS" --timeout=30s > /dev/null 2>&1; then
    echo "❌ FATAL: Diagnostic pod failed to initialize (Check ImagePullBackOff or Resources)."
    kubectl delete pod sentinel-debug -n "$TARGET_NS" --grace-period=0 --force > /dev/null 2>&1
    exit 1
fi

# 3. SECURITY AUDIT EXECUTION
echo -n "[1/4] DNS Resolution Check...      "
if kubectl exec -n "$TARGET_NS" sentinel-debug -- nslookup google.com > /dev/null 2>&1; then echo "✅ OK"; else echo "❌ FAIL"; fi

echo -n "[2/4] K8s API Access Check...      "
if kubectl exec -n "$TARGET_NS" sentinel-debug -- curl -k -s --connect-timeout 2 https://10.43.0.1 > /dev/null 2>&1; then echo "✅ OK"; else echo "❌ FAIL"; fi

echo -n "[3/4] Service Mesh Reachability... "
if kubectl exec -n "$TARGET_NS" sentinel-debug -- curl -s --connect-timeout 2 "$POD_IP:$POD_PORT" > /dev/null 2>&1; then echo "✅ OK"; else echo "❌ FAIL"; fi

echo -n "[4/4] Zero-Trust Egress Check...   "
if ! kubectl exec -n "$TARGET_NS" sentinel-debug -- curl -s --connect-timeout 2 http://1.1.1.1 > /dev/null 2>&1; then 
    echo "✅ SECURE (Blocked)"
else 
    echo "⚠️ WARNING (Open)"
fi

# 4. SRE CLEANUP
echo "🧹 Purging diagnostic resources..."
kubectl delete pod sentinel-debug -n "$TARGET_NS" --grace-period=0 --force > /dev/null 2>&1

echo "--------------------------------------------------------"
echo "🏁 DYNAMIC AUDIT COMPLETE"