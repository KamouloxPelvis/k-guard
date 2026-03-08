#!/bin/bash
# --- K-Guard SRE Connectivity Validator ---
set -e

# 1. DYNAMIC SCOPING
TARGET_NS=$(kubectl get pods -A --field-selector=status.phase=Running -o jsonpath='{.items[?(@.metadata.namespace!="kube-system")].metadata.namespace}' | tr ' ' '\n' | head -n 1)
if [ -z "$TARGET_NS" ]; then echo "❌ No target namespace found."; exit 1; fi

TEST_POD=$(kubectl get pods -n "$TARGET_NS" --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')
POD_IP=$(kubectl get pod -n "$TARGET_NS" "$TEST_POD" -o jsonpath='{.status.podIP}')

# Extract first exposed port robustly
POD_PORT=$(kubectl get pod -n "$TARGET_NS" "$TEST_POD" -o jsonpath='{.spec.containers[*].ports[*].containerPort}' | awk '{print $1}')
POD_PORT=${POD_PORT:-80}

echo "--------------------------------------------------------"
echo "🔍 K-GUARD CONNECTIVITY TEST"
echo "📍 Target Namespace : $TARGET_NS"
echo "🚀 Target App Pod   : $TEST_POD ($POD_IP:$POD_PORT)"
echo "--------------------------------------------------------"

# 2. DEPLOY EPHEMERAL POD
echo "⏳ Deploying ephemeral diagnostic pod (sentinel-debug)..."
kubectl run sentinel-debug -n "$TARGET_NS" --image=nicolaka/netshoot --restart=Never -- sleep 60 > /dev/null 2>&1
kubectl wait --for=condition=Ready pod/sentinel-debug -n "$TARGET_NS" --timeout=45s > /dev/null 2>&1

# 3. RUN AUDIT
echo -n "[1/4] Testing DNS Resolution... "
if kubectl exec -n "$TARGET_NS" sentinel-debug -- nslookup google.com > /dev/null 2>&1; then echo "✅ SUCCESS"; else echo "❌ FAILED"; fi

echo -n "[2/4] Testing K8s API Access... "
if kubectl exec -n "$TARGET_NS" sentinel-debug -- curl -k -s --connect-timeout 2 https://10.43.0.1 > /dev/null 2>&1; then echo "✅ SUCCESS"; else echo "❌ FAILED"; fi

echo -n "[3/4] Testing App Reachability... "
if kubectl exec -n "$TARGET_NS" sentinel-debug -- curl -s --connect-timeout 2 "$POD_IP:$POD_PORT" > /dev/null 2>&1; then echo "✅ SUCCESS"; else echo "❌ FAILED"; fi

echo -n "[4/4] Verifying Egress Isolation (1.1.1.1)... "
if ! kubectl exec -n "$TARGET_NS" sentinel-debug -- curl -s --connect-timeout 3 http://1.1.1.1 > /dev/null 2>&1; then echo "✅ SUCCESS (Blocked)"; else echo "⚠️ WARNING (Open)"; fi

# 4. CLEANUP
echo "🧹 Cleaning up..."
kubectl delete pod sentinel-debug -n "$TARGET_NS" --grace-period=0 --force > /dev/null 2>&1
echo "--------------------------------------------------------"
echo "🏁 DYNAMIC AUDIT COMPLETE"