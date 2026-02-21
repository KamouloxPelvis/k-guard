# 🛡️ K-Guard: Orchestration, SRE & Security

### 🚀 Environnement de Développement
* **Backend (Node.js)** : `cd backend && npm run dev`
* **Frontend (React)** : `cd frontend && npm start`
* **Priorité actuelle** : Stabilisation de l'app et ajout d'une feature de sécurité

### ☸️ Gestion du Cluster K3s (Namespace: k-guard)
* **Lister les ressources** : `kubectl get all -n k-guard`
* **Logs de l'orchestrateur** : `kubectl logs -f -l app=k-guard -n k-guard`
* **Logs du scanner d'audit** : `kubectl logs -f -l app=k-guard-scanner -n k-guard`
* **Restart Deployment** : `kubectl rollout restart deployment k-guard-app -n k-guard`

### Débuggage post-modifications
* **Vérifier si les conteneurs**: `kubectl get pods -n k-guard`
* **Vérifier l'application** : `kubectl get svc -n k-guard`
* **Vérifier le routage** : `kubectl get ingressroute -n k-guard`

* **Vérifier les endpoints du service (s'ils sont <none>, c'est que les conteneurs ont échoué aux tests de santé)** :
`kubectl get endpoints k-guard-backend-service -n k-guard`

* **Vérifier les logs des conteneurs** :
* `kubectl logs -l app=k-guard -c frontend -n k-guard`
* `kubectl logs -l app=k-guard -c backend -n k-guard`

* **Débuggage Traefik**: `kubectl get svc`
* `kubectl get svc -n kube-system | grep traefik`

### Nettoyage du Cluster
* `kubectl delete all --all -n k-guard`
* `kubectl delete namespace k-guard`
* `k3s ctr images list | grep k-guard`
* `k3s ctr images rm docker.io/library/k-guard-backend:latest`
* `k3s ctr images rm docker.io/library/k-guard-frontend:latest`
* `k3s crictl rmi --prune`

### 🔒 Audit & Cyber-Sécurité (Cyber Master)
* **Vérification des droits RBAC** : `kubectl auth can-i get pods --as=system:serviceaccount:k-guard:k-guard-sa`
* **Scan d'image manuel (Trivy)** : `trivy image <tag_de_l_image>`
* **Analyse des vulnérabilités** : Vérifier les rapports dans le pod `k-guard-scanner`

### 🛠️ Infrastructure & Déploiement
* **Accès VPS** : `ssh kamal@113.30.191.17`
* **Déploiement** :
```bash
  cd /scripts
  sudo ./deploy.sh
 ```