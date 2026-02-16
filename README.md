🇺🇸 [English Version below](#english-version)

# 🛡️ K-Guard v1.0 : Opérateur de Maintenance & Sécurité automatisé pour clusters Kubernetes

## ⚠️ WARNING / SECURITY DISCLAIMER :

*Cet outil est un projet de recherche et d'apprentissage (Proof of Concept) développé pour un usage en environnement de développement contrôlé. En raison de l'accès direct au socket Docker et aux privilèges RBAC, l'utilisation de K-Guard dans un environnement de production non sécurisé peut exposer votre cluster à des risques d'escalade de privilèges. Ne déployez pas cet outil sur un réseau exposé sans une configuration stricte des Network Policies et une authentification renforcée.*

K-Guard est un dashboard SRE (Site Reliability Engineering) dédié à l'observabilité et à l'audit de sécurité automatisé pour clusters Kubernetes (optimisé pour k3s). Conçu pour offrir une visibilité en temps réel sur l'état de santé des Pods et leur surface d'attaque, K-Guard intègre des fonctions de remédiation immédiates : redémarrage de services, délestage dynamique des réplicas en cas de saturation CPU/RAM, et signalement de mise à jour des images conteneurisées suite à la détection de vulnérabilités critiques.


## 🚀 Fonctionnalités Clés

* **Health Monitoring** : Visualisation dynamique de la charge CPU/RAM avec seuils de criticité intelligents (Bleu/Orange/Rouge).

![Dashboard](frontend/public/screenshots/health_view.png)

* **Security Audit** : Intégration native de Trivy pour le scan de vulnérabilités (CVE) des images conteneurs.

![Update Required View](frontend/public/screenshots/demo_view.png)

* **Statut Dynamique** : Interprétation automatique des niveaux de risque (SECURE, WATCH OUT, UPDATE REQUIRED).

* **Gestion Opérationnelle** : Consultation des logs en temps réel et redémarrage des Pods via une interface sécurisée.

![Logs](frontend/public/screenshots/log.png)

### 💡 Astuce scan mode Démo : En maintenant Shift lors d'un clic sur "Launch Scan", K-Guard force l'analyse d'une image volontairement obsolète (nginx:1.18).

![Security View](frontend/public/screenshots/security_view.png)

## 🛠️ Stack Technique

* **Frontend** : Vue 3, TypeScript, Tailwind CSS (Design "Cyber" immersif).

* **Backend** : FastAPI (Python), Kubernetes Python Client (RBAC aware).

* **Sécurité** : Trivy Engine.

* **Infrastructure** : Cluster K3s sur VPS Ubuntu.

* **Audit Local** : Montage du socket Docker (/var/run/docker.sock) dans le conteneur backend pour permettre à Trivy d'analyser les images présentes sur l'hôte en temps réel, sans transfert de données vers l'extérieur.

## 🎯 Vision SRE & Sécurité

* **Réduction de la surface d'attaque** : Utilisation d'images de base Alpine et Slim pour minimiser les vulnérabilités système.

* **Infrastructure as Code** : Déploiement 100% automatisé via manifests YAML, garantissant une reproductibilité totale du cluster.

* **Sécurité RBAC** : Utilisation de ServiceAccounts dédiés avec des permissions limitées (Least Privilege principle).

## 🛠️ Configuration & Installation (Plug & Play)

![Installation](frontend/public/screenshots/installation.png)

### 1. Compatibilité & Pré-requis Stockage

Avant de lancer l'installation, vérifiez la conformité de votre infrastructure :

* **Type de Cluster :** Optimisé pour **K3s**. Compatible avec tout cluster **CNCF-compliant** (Vanilla, MicroK8s, Minikube).
* **Gestion du Stockage (PVC) :** K-Guard nécessite un **PersistentVolumeClaim de 2Gi** pour la base de données Trivy. 
    * **Classe par défaut :** Votre cluster doit disposer d'une `StorageClass` définie par défaut (ex: `local-path` sur K3s). 
    * *Vérification :* `kubectl get storageclass` (cherchez l'annotation `(default)`).
* **Architecture :** Support natif x86_64 et ARM64.


### ⚠️*Pour une isolation réseau maximale (Network Policies), l'utilisation d'un CNI compatible (Calico, Cilium ou Kube-router) est recommandée. Sur Flannel, l'application reste fonctionnelle mais l'isolation inter-pod ne sera pas active.*

K-Guard utilise un assistant d'installation intelligent qui gère la génération des clés de sécurité et le déploiement Kubernetes :

### 2. Auto-check & Dépendances Système

K-Guard inclut un script de pré-vol (check_env.py) qui valide vos permissions Docker et K3s avant toute installation. Assurez-vous tout de même d'avoir installé sur votre VPS :

* K3s (curl -sfL https://get.k3s.io | sh -)

* Docker (sudo apt install docker.io -y)

* Python 3 & Pip

### 2. Installation Rapide

```Bash
# Cloner le projet
git clone https://gitlab.com/portfolio-kamal-guidadou/k-guard.git
cd k-guard

# Rendre le script exécutable
chmod +x scripts/deploy.sh

# Lancer l'assistant de déploiement (Wizard TUI)
sudo ./scripts/deploy.sh
```

### 3. Accès à l'Interface (Post-Installation)

Une fois le déploiement terminé, l'application est verrouillée pour votre sécurité. Pour y accéder via votre navigateur :

Configurez votre résolution locale :
Ajoutez l'IP de votre serveur dans votre fichier hosts pour lier le domaine local.

* *Linux/MacOS* (/etc/hosts) ou *Windows* (C:\Windows\System32\drivers\etc\hosts) :


**[IP_DE_VOTRE_VPS]  k-guard.local**
*Exemple : 114.35.188.19  k-guard.local*

**Connexion sécurisée** :
Rendez-vous sur https://k-guard.local.

🔒 Note : Grâce au durcissement Nginx (TLS 1.3), votre session est intégralement chiffrée et protégée par les ACL définies lors du déploiement.

### Que fait le script ?

* **Wizard Interactif** : Vous demande votre domaine/IP et génère un mot de passe sécurisé.

* **Sécurisation Auto** : Génère une SECRET_KEY unique et hash votre mot de passe en Bcrypt.

* **Build Local** : Construit les images Docker et les injecte directement dans le moteur de conteneurs K3s (pas besoin de registre externe).

* **Kubernetes Orchestration** : Déploie automatiquement les manifests (RBAC, Services, Ingress, Deployment).

* **Zéro-Config Ingress** : Configure automatiquement le routage via Traefik/Nginx Ingress et gère nativement le servirage statique des modules Vue.js pour éviter les erreurs de type MIME.

*N'hésitez pas à lire mon article sur mon blog : https://blog.devopsnotes.org/articles/k-guard-orchestration-sre-et-audit-de-scurit-sur-k3s*


---------------------

Kamal Guidadou 2026
https://devopsnotes.org
https://blog.devopsnotes.org


                        ------------------------------------------------------------------


<a name="english-version"></a>
🇺🇸 English Version

# 🛡️ K-Guard v1.0 : Automated Maintenance & Security Operator for Kubernetes Clusters

## ⚠️ SECURITY DISCLAIMER & WARNING

*This tool is a Research and Learning project (Proof of Concept) developed for use in controlled development environments. Due to direct access to the Docker socket and specific RBAC privileges, deploying K-Guard in an unsecured production environment may expose your cluster to significant risks, including privilege escalation. Do not deploy this tool on an exposed network without strict Network Policies, robust authentication, and a full understanding of the underlying security implications.*

K-Guard is an SRE (Site Reliability Engineering) dashboard dedicated to observability and automated security auditing for Kubernetes clusters (optimized for k3s). Designed to provide real-time visibility into Pod health and attack surfaces, K-Guard integrates immediate remediation features: service restarts, dynamic replica scaling during CPU/RAM saturation, and update alerts for containerized images following the detection of critical vulnerabilities


## 🚀 Key Features

* **Health Monitoring**: Dynamic visualization of CPU/RAM load with intelligent criticality thresholds

![Dashboard](frontend/public/screenshots/health_view.png)

* **Security Audit**: Native Trivy integration for automated CVE scanning of container images.

![Update Required View](frontend/public/screenshots/demo_view.png)

* **Dynamic Status**: Automatic risk level interpretation (SECURE, WATCH OUT, UPDATE REQUIRED).

* **Operational Management**: Real-time log streaming and Pod lifecycle management (restarts) through a secure interface.

![Dashboard](frontend/public/screenshots/log.png)

💡 Demo Mode Scan Tip: By holding Shift while clicking "Launch Scan", K-Guard forces an audit on a legacy image (nginx:1.18) to demonstrate vulnerability detection.

![Security View](frontend/public/screenshots/security_view.png)

🛠️ Tech Stack

* **Frontend**: Vue 3, TypeScript, Tailwind CSS (Immersive "Cyber" Design).

* **Backend**: FastAPI (Python), Kubernetes Python Client (RBAC aware).

* **Security**: Trivy Engine.

* **Infrastructure**: K3s Cluster on Ubuntu VPS.

* **Local Audit**: Docker socket mounting (/var/run/docker.sock) into the backend container, allowing Trivy to analyze on-host images in real-time without external data transfer.

🎯 SRE & Security Vision

* **Attack Surface Reduction**: Use of Alpine and Slim base images to minimize system vulnerabilities.

* **Infrastructure as Code**: 100% automated deployment via YAML manifests, ensuring total cluster reproducibility.

* **RBAC Security**: Dedicated ServiceAccounts with scoped permissions following the Least Privilege principle.

## 🛠️ Configuration & Installation (Plug & Play)

### 1. Compatibility & Storage Requirements

Before starting the setup, ensure your infrastructure meets the following requirements:

* **Cluster Type:** Optimized for **K3s**. Fully compatible with any **CNCF-compliant** cluster (Vanilla, MicroK8s, Minikube).
* **Storage Management (PVC):** K-Guard requests a **2Gi PersistentVolumeClaim** for the Trivy vulnerability database.
    * **Default StorageClass:** Your cluster **must** have a default `StorageClass` configured (e.g., `local-path` on K3s, `gp2` on AWS).
    * *Verification:* Run `kubectl get storageclass` and check for the `(default)` annotation.

* **Architecture:** Native support for x86_64 and ARM64.

### ⚠️*For maximum network isolation via Network Policies, the use of a compatible CNI (such as Calico, Cilium, or Kube-router) is highly recommended. If you are using Flannel (the default K3s network plugin), K-Guard will remain fully functional, but the inter-pod network isolation rules will not be enforced by the cluster.*

K-Guard features a Smart Setup Assistant that automates security key generation and Kubernetes orchestration:

![Installation](frontend/public/screenshots/installation.png)

### 1. Prerequisites & Auto-check

K-Guard includes a pre-flight script (check_env.py) that validates your Docker and K3s permissions before installation. Ensure your VPS has:

* K3s: curl -sfL https://get.k3s.io | sh -

* Docker: sudo apt install docker.io -y

* Python 3 & Pip

### 2. Quick Start

```Bash
# Clone the repository
git clone https://gitlab.com/portfolio-kamal-guidadou/k-guard.git
cd k-guard

# Make the script executable
chmod +x scripts/deploy.sh

# Launch the Deployment Wizard (TUI)
sudo ./scripts/deploy.sh
```

### 3. Accessing the Interface (Post-Installation)
Once the deployment is complete, the application is locked down for your security. To access it via your web browser:

Step 1: Configure Local DNS Resolution
Map your server's IP address to the local domain in your hosts file.

*Linux/MacOS*: /etc/hosts

*Windows*: C:\Windows\System32\drivers\etc\hosts

Add the following line (replace [YOUR_VPS_IP] with your actual server IP):

Plaintext
[YOUR_VPS_IP]  k-guard.local
**Example: 114.35.18.15  k-guard.local**
Step 2: Secure Connection
Navigate to: https://k-guard.local

🔒 Security Note: Thanks to Nginx hardening (TLS 1.3), your session is fully encrypted and protected by the ACLs (Access Control Lists) defined during deployment. Access is restricted to authorized private networks only.

### Automated Workflow

* **Interactive Wizard**: Prompts for your domain/IP and generates a secure admin password.

* **Auto-Hardening**: Generates a unique SECRET_KEY and hashes your password using Bcrypt.

* **Local Build & Inject**: Builds Docker images and imports them directly into the K3s container runtime (Air-gapped friendly, no external registry required).

* **Kubernetes Orchestration**: Automatically deploys manifests (RBAC, Services, Ingress, Deployment).

* **Zero-Config Ingress**: Automates routing via Traefik/Nginx Ingress and natively handles static serving for Vue.js modules to prevent MIME type errors.


---------------------

Kamal Guidadou 2026
https://devopsnotes.org
https://blog.devopsnotes.org