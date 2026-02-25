🇺🇸 [English Version](#english)

# 🛡️ K-Guard v1.5 : Opérateur DevSecOps & SOAR pour Clusters Kubernetes

## ⚠️ WARNING / SECURITY DISCLAIMER

*Cet outil est un Proof of Concept (PoC) orienté recherche en cybersécurité, développé pour un usage en environnement de développement contrôlé. En raison de l'accès privilégié au daemon Docker (socket) et aux droits RBAC étendus, le déploiement de K-Guard dans un environnement de production non durci peut exposer l'infrastructure à des risques critiques (Privilege Escalation, Container Breakout). Ne déployez pas ce composant sur un réseau exposé sans une architecture Zero Trust stricte, des Network Policies restrictives et une authentification forte.*

K-Guard agit comme un **SOAR** (Security Orchestration, Automation, and Response) allégé et un outil de **CSPM** (Cloud Security Posture Management) dédié à la défense active des clusters Kubernetes (K3s). Son objectif est de garantir le Maintien en Condition de Sécurité (MCS) de l'infrastructure cloud via une automatisation complète de la réponse aux incidents.

🎯 **Capacités Cybersécurité & SRE :**

* 🚨 **Incident Response (IR) & MTTR :** Automatisation de la détection d'anomalies et pilotage direct de l'API Kubernetes pour endiguer les compromissions et opérer une remédiation rapide, minimisant le Mean Time To Remediate.
* 🛡️ **Continuous Vulnerability Management :** Intégration Shift-Left avec le moteur Trivy pour l'audit en temps réel des images conteneurisées. Déclenchement de "Smart Patches" via GitLab CI/CD pour forcer le rebuild des images dès l'apparition de CVE (Common Vulnerabilities and Exposures) critiques.
* 🔒 **Hardening & Zero Trust (RBAC) :** Application stricte du principe de moindre privilège via des ServiceAccounts isolés. Sécurisation périmétrique (Ingress) renforcée par ACLs (filtrage RFC 1918).
* ⚡ **Résilience Cloud-Native (Self-Healing) :** Monitoring de la dérive de configuration (Configuration Drift) et restauration automatisée des workloads pour assurer la haute disponibilité de la surface d'attaque applicative.

---

## 📍 Sommaire
- [🚀 Fonctionnalités Clés](#features)
- [🛠️ Stack Technique & Architecture](#stack)
- [🎯 Politique de Sécurité & RBAC](#rbac)
- [🛠️ Déploiement & Configuration](#install)
- [🆙 Changelog (v1.5)](#changelog)
- [👤 Contact](#contact)

---

<div id="features"></div>

## 🚀 Fonctionnalités Clés

* **Observabilité & Health Monitoring** : Télémétrie dynamique de l'empreinte ressource (CPU/RAM) avec scoring de criticité intelligent (Bleu/Orange/Rouge) pour prévenir les attaques par déni de service (DoS).

![Dashboard](frontend/public/screenshots/kguard-1.png)
*Dashboard des déploiements avec calcul de la charge matérielle*

* **Audit de Sécurité Continu** : Scan automatisé des workloads via Trivy pour identifier les failles de sécurité (CVE) introduites dans la Supply Chain logicielle.

![Update Required View](frontend/public/screenshots/kguard-4.png)
*Affichage centralisé des vulnérabilités critiques et hautes*

* **Dynamic Risk Scoring** : Interprétation automatique de la posture de sécurité globale avec des états d'alerte contextualisés (SECURE, WATCH OUT, UPDATE REQUIRED).

* **Gestion Opérationnelle Sécurisée** : Accès chiffré aux logs des Pods en temps réel et interface de remédiation manuelle pour isoler ou redémarrer les services compromis.

![Logs](frontend/public/screenshots/kguard-2.png)
*Il suffit de cliquer sur l'un des pods du cluster pour consulter son log*

### 💡 *Threat Intelligence - Mode Démo :*
En maintenant la touche `Shift` lors d'un clic sur "Launch Scan", K-Guard force intentionnellement l'analyse d'une image obsolète et vulnérable (`nginx:1.18`) pour valider la chaîne de détection des CVE.

![Vulnerabilities' Details](frontend/public/screenshots/kguard-5.png)
*Détail des vulnérabilités trouvées par Trivy*

---

<div id="stack"></div>

## 🛠️ Stack Technique & Architecture

* **Frontend** : Vue 3, TypeScript, Tailwind CSS (Interface analytique "Cyber").
* **Backend** : FastAPI (Python), client officiel Kubernetes (RBAC-aware).
* **Scanner de Vulnérabilités** : Trivy Engine (Aqua Security).
* **Infrastructure cible** : Cluster K3s sur environnement Linux (VPS Ubuntu).
* **Stratégie d'Audit Local (Air-Gapped Access)** : Montage restreint du `/var/run/docker.sock` en lecture dans le backend. Permet à Trivy d'analyser les couches du système de fichiers conteneur directement sur l'hôte, empêchant toute exfiltration de données vers un registre externe.

---

<div id="rbac"></div>

## 🎯 Politique de Sécurité & RBAC

* **Réduction de la Surface d'Attaque (ASR)** : Durcissement des images de base (Alpine, Distroless/Slim) pour éradiquer les vecteurs d'attaque liés aux dépendances OS superflues.
* **Infrastructure as Code (IaC) Immuable** : Déploiement déclaratif 100% automatisé (Manifests YAML) assurant l'intégrité et la reproductibilité de l'architecture.
* **Gouvernance RBAC** : Définition de Rôles/ClusterRoles granulaires pour les ServiceAccounts, interdisant formellement l'élévation de privilèges ou les altérations hors périmètre.

---

<div id="install"></div>

## 🛠️ Déploiement & Configuration

![Installation](frontend/public/screenshots/install.png)

### Compatibilité & Pré-requis d'Infrastructure

Avant l'initialisation de K-Guard, validez la topologie de votre environnement :

* **Moteur d'Orchestration :** Optimisé pour **K3s**. Compatible avec tout orchestrateur **CNCF-compliant** (Vanilla K8s, MicroK8s, Minikube).
* **Gestion des Volumes (CSI/PVC) :** K-Guard provisionne un **PersistentVolumeClaim (2Gi)** sécurisé pour stocker les signatures de vulnérabilités Trivy hors du cycle de vie des pods.
    * **StorageClass :** Une `StorageClass` par défaut est requise (`local-path` recommandé sur K3s).
    * *Audit :* Vérifiez avec `kubectl get storageclass`.
* **Architecture Matérielle :** Binaires multi-arch (x86_64, ARM64).

### ⚠️ *Recommandation d'Isolation Réseau (CNI)*
*Pour garantir un cloisonnement étanche (Micro-segmentation) via les Network Policies, l'implémentation d'un CNI avancé (Calico, Cilium, Kube-router) est critique. L'utilisation du CNI Flannel par défaut laissera l'application fonctionnelle, mais les règles de filtrage Est-Ouest (inter-pods) seront ignorées par le cluster.*

### Auto-check & Dépendances

L'assistant lance un script de "Pre-flight check" pour valider la configuration sécurisée de Docker et de l'API K3s. Pré-requis sur l'hôte :

* K3s (`curl -sfL https://get.k3s.io | sh -`)
* Docker (`sudo apt install docker.io -y`)
* Python 3 & Pip

### 1. Procédure d'Amorçage Rapide

```bash
# Récupération du dépôt
git clone [https://gitlab.com/portfolio-kamal-guidadou/k-guard.git](https://gitlab.com/portfolio-kamal-guidadou/k-guard.git)

cd k-guard/installer

# Accorder les droits d'exécution
chmod +x kguard-installer

# Lancer l'installation
./kguard-installer
```

### 2. Accès au Panel de Contrôle (Post-Déploiement)

L'accès au dashboard de K-Guard se fait par l'IP de votre IP sur le port 30002 (ex: http://VPS_IP:30002)
*Vérifiez vos règles de pare-feu !*

### Que fait le script de déploiement ?

* **Secure Wizard** : Collecte interactive du domaine et génération d'un mot de passe administrateur fort.
* **Gestion des Secrets** : Génération cryptographique de la `SECRET_KEY` et hachage du mot de passe en Bcrypt (Work factor adapté).
* **Build Local Isolée** : Compilation des images Docker et injection directe dans le socket K3s (contourne la nécessité d'un Container Registry vulnérable aux attaques de type Supply Chain).
* **Orchestration K8s** : Déploiement déterministe des manifests (RBAC, Services, Network Policies, Ingress).
* **Zéro-Config Ingress** : Auto-configuration du reverse-proxy (Traefik/Nginx) et durcissement des headers HTTP pour la distribution des assets statiques (Vue.js).

*Découvrez l'article complet sur la genèse du projet : [K-Guard : Orchestration, SRE et Audit de Sécurité sur K3s](https://blog.devopsnotes.org/articles/k-guard-orchestration-sre-et-audit-de-scurit-sur-k3s)*

---

<div id="changelog"></div>

## 🆙 Changelog : Version 1.5 - 16/02/2026

**Mise à jour Majeure : SRE & Sécurité Opérationnelle**

Cette version marque la transition de K-Guard vers une architecture "Production-Ready", articulée autour du concept du Zero Trust et de l'orchestration Kubernetes native.

### 🛡️ Durcissement Backend (Rootless Execution) :
* Migration du processus FastAPI pour s'exécuter sous un **pseudo non-privilégié** (UID 1000), prévenant les risques d'exécution de code arbitraire (RCE) en tant que root.
* Refonte Agnostique du Stockage : Les bases de données Trivy (`/data/trivy-cache`) sont désormais cloisonnées hors du répertoire utilisateur, empêchant la compromission des fichiers systèmes locaux.

### 🔄 Remédiation Cloud-Native (Zero-Downtime) :
* Révocation de la méthode obsolète de redémarrage par destruction abrupte des Pods (SIGKILL).
* Adoption du **Strategic Merge Patch** : Les redémarrages sont pilotés via l'injection d'annotations dans les métadonnées. L'orchestrateur gère désormais un Rolling Update propre, garantissant la continuité de service (ZDD).

### 🔑 Optimisation IAM & RBAC (Moindre Privilège) :
* Restriction drastique du ClusterRole : Révocation définitive du verbe `delete`.
* Ciblage granulaire : Les droits `patch` et `update` sont strictement limités à la ressource `Deployment` pour autoriser le flux de CI/CD (Smart Patch) sans compromettre le reste du namespace.

### 🔌 Intégration Sécurisée de l'Infrastructure :
* Sécurisation de l'accès au socket Docker via l'attribut `supplementalGroups` dans le `SecurityContext` du Pod.
* Conformité Nginx : Migration du listener frontend sur le port 8080 pour valider l'exécution non-root.

### 🌐 Accessibilité Internationale :
* Traduction intégrale de la documentation et de la TUI en anglais pour répondre aux standards de la communauté DevSecOps internationale.

---

<div id="contact"></div>

## 👤 Contact & Crédits

© 2026 - **Kamal Guidadou** *DevSecOps, SRE & Cloud Security*

* 🌐 **Portfolio** : [https://portfolio.devopsnotes.org](https://portfolio.devopsnotes.org)
* ✍️ **Blog Cyber/Tech** : [https://blog.devopsnotes.org](https://blog.devopsnotes.org)

<br><br><br>

---
---

<div id="english"></div>
🇺🇸 English Version

# 🛡️ K-Guard v1.5: DevSecOps Operator & Kubernetes SOAR

## ⚠️ SECURITY DISCLAIMER & WARNING

*This tool is a Cybersecurity Research and Learning project (Proof of Concept) designed for controlled development environments. Due to its direct access to the Docker daemon (socket) and elevated RBAC privileges, deploying K-Guard in an unhardened production environment may expose your infrastructure to critical threats, including privilege escalation and container breakout. Do not deploy this component on an exposed network without implementing a strict Zero Trust architecture, restrictive Network Policies, and robust authentication mechanisms.*

K-Guard operates as a lightweight **SOAR** (Security Orchestration, Automation, and Response) and **CSPM** (Cloud Security Posture Management) tool tailored for active defense in K3s clusters. It ensures continuous Cloud Security Posture through automated incident response and threat remediation.

🎯 **Core DevSecOps & SRE Capabilities:**

* 🚨 **Incident Response (IR) & MTTR:** Automates anomaly detection and natively drives the Kubernetes API to contain breaches and apply rapid remediation, significantly lowering the Mean Time To Remediate.
* 🛡️ **Continuous Vulnerability Management:** Shift-Left integration with the Trivy engine for real-time container image auditing. Triggers automated "Smart Patches" via GitLab CI/CD, forcing secure image rebuilds upon critical CVE detection.
* 🔒 **Hardening & Zero Trust (RBAC):** Strictly enforces Least Privilege principles via isolated ServiceAccounts. Enhances perimeter security with robust Ingress ACLs (RFC 1918 filtering).
* ⚡ **Cloud-Native Resilience (Self-Healing):** Monitors configuration drift and provides automated workload restoration to guarantee maximum availability of the application attack surface.

---

## 📍 Table of Contents
- [🚀 Core Features](#en-features)
- [🛠️ Technical Stack & Architecture](#en-stack)
- [🎯 Security Policy & RBAC](#en-rbac)
- [🛠️ Deployment & Configuration](#en-install)
- [🆙 Changelog (v1.5)](#en-changelog)
- [👤 Contact](#en-contact)

---

<div id="en-features"></div>

## 🚀 Core Features

* **Observability & Health Monitoring**: Dynamic telemetry mapping of CPU/RAM footprint, featuring intelligent risk scoring (Blue/Orange/Red) to detect potential Denial of Service (DoS) conditions.

![Dashboard](frontend/public/screenshots/kguard-1.png)
*Deployment Dashboard featuring real-time hardware resource consumption analysis*

* **Continuous Security Audit**: Automated workload scanning powered by Trivy to identify software supply chain vulnerabilities (CVEs).

![Update Required View](frontend/public/screenshots/kguard-5.png)

* **Dynamic Risk Scoring**: Contextualized interpretation of the overall security posture (SECURE, WATCH OUT, UPDATE REQUIRED).

* **Secure Operational Management**: Encrypted real-time Pod log streaming and a manual remediation interface to securely restart or isolate compromised services.

![Logs](frontend/public/screenshots/kguard-2.png)

### 💡 *Threat Intelligence - Demo Mode:*
By holding `Shift` while clicking "Launch Scan", K-Guard intentionally forces an audit on a legacy, highly vulnerable image (`nginx:1.18`) to validate the CVE detection pipeline.

![Security View](frontend/public/screenshots/kguard-3.png)

---

<div id="en-stack"></div>

## 🛠️ Technical Stack & Architecture

* **Frontend**: Vue 3, TypeScript, Tailwind CSS (Immersive "Cyber" UI).
* **Backend**: FastAPI (Python), Kubernetes Python Client (RBAC-aware).
* **Vulnerability Engine**: Trivy (Aqua Security).
* **Target Infrastructure**: K3s Cluster on Linux environments (Ubuntu VPS).
* **Local Audit Strategy (Air-Gapped Access)**: Read-only mounting of `/var/run/docker.sock` into the backend. This allows Trivy to analyze container filesystem layers directly on the host, preventing external data exfiltration to vulnerable container registries.

---

<div id="en-rbac"></div>

## 🎯 Security Policy & RBAC

* **Attack Surface Reduction (ASR)**: Utilization of hardened base images (Alpine, Distroless/Slim) to eliminate attack vectors linked to unnecessary OS dependencies.
* **Immutable Infrastructure as Code (IaC)**: 100% automated declarative deployment via YAML manifests, ensuring architectural integrity and reproducibility.
* **RBAC Governance**: Granular Role/ClusterRole definitions for ServiceAccounts, strictly preventing privilege escalation and unauthorized out-of-scope modifications.

---

<div id="en-install"></div>

## 🛠️ Deployment & Configuration

![Installation](frontend/public/screenshots/install.png)

### Compatibility & Infrastructure Requirements

Before initializing K-Guard, validate your environment's topology:

* **Orchestration Engine:** Optimized for **K3s**. Fully compatible with any **CNCF-compliant** orchestrator (Vanilla K8s, MicroK8s, Minikube).
* **Storage Management (CSI/PVC):** K-Guard provisions a secure **2Gi PersistentVolumeClaim** to safely store Trivy vulnerability signatures outside the pod lifecycle.
    * **StorageClass:** A default `StorageClass` is mandatory (e.g., `local-path` on K3s).
    * *Audit:* Verify using `kubectl get storageclass`.
* **Architecture:** Multi-arch binaries (x86_64, ARM64).

### ⚠️ *Network Isolation Recommendation (CNI)*
*To ensure strict micro-segmentation via Network Policies, deploying an advanced CNI (Calico, Cilium, Kube-router) is critical. While using the default Flannel CNI keeps the application functional, East-West (inter-pod) filtering rules will not be enforced by the cluster.*

### Pre-flight Checks & Dependencies

The setup wizard executes a validation script (`check_env.py`) to confirm secure Docker and K3s API configurations. Host requirements:

* K3s (`curl -sfL https://get.k3s.io | sh -`)
* Docker (`sudo apt install docker.io -y`)
* Python 3 & Pip

### 1. Quick Start Procedure

```bash
# Clone the repository
git clone [https://gitlab.com/portfolio-kamal-guidadou/k-guard.git](https://gitlab.com/portfolio-kamal-guidadou/k-guard.git)
cd k-guard/installer

# Apply strict execution permissions
chmod +x kguard-installer

# Launch installation
./kguard-installer
```

### 2. Accessing the Control Panel (Post-Deployment)

Control panel is accessible after installation via your VPS IP on port 30002 (e.g : http://VPS_IP:30002)
*Please check your firewall !*

### Automated Setup Workflow

* **Secure Wizard**: Interactively collects your domain and generates a robust admin password.
* **Secrets Management**: Cryptographically generates the `SECRET_KEY` and hashes the password via Bcrypt (appropriate work factor).
* **Isolated Local Build**: Compiles Docker images and injects them directly into the K3s socket (bypassing the need for a Container Registry, mitigating Supply Chain attack vectors).
* **K8s Orchestration**: Deterministic deployment of manifests (RBAC, Services, Network Policies, Ingress).
* **Zero-Config Ingress**: Auto-configures the reverse-proxy (Traefik/Nginx) and hardens HTTP headers for static asset distribution (Vue.js).

---

<div id="en-changelog"></div>

## 🆙 Changelog: Version 1.5 - 16/02/2026

**Major Release: SRE & Operational Security**

This update represents K-Guard's transition to a "Production-Ready" architecture, firmly rooted in Zero Trust concepts and native Kubernetes orchestration.

### 🛡️ Backend Hardening (Rootless Execution):
* Migrated the FastAPI process to run under a **non-privileged pseudo** (UID 1000), effectively mitigating Arbitrary Code Execution (RCE) risks as root.
* Agnostic Storage Redesign: Trivy databases (`/data/trivy-cache`) are now isolated outside the user directory, preventing local system file compromise.

### 🔄 Cloud-Native Remediation (Zero-Downtime):
* Deprecated the unsafe method of abruptly destroying Pods (SIGKILL).
* Adopted **Strategic Merge Patching**: Restarts are now driven by injecting metadata annotations. The orchestrator cleanly manages a Rolling Update, guaranteeing Zero Downtime Deployment (ZDD).

### 🔑 IAM & RBAC Optimization (Least Privilege):
* Drastic ClusterRole restriction: Permanent revocation of the `delete` verb.
* Granular scoping: The `patch` and `update` permissions are strictly bound to the `Deployment` resource to allow CI/CD workflows (Smart Patch) without compromising the rest of the namespace.

### 🔌 Secure Infrastructure Integration:
* Secured Docker socket access by leveraging the `supplementalGroups` attribute within the Pod's `SecurityContext`.
* Nginx Compliance: Migrated the frontend listener to port 8080 to enforce non-root execution.

### 🌐 Global Accessibility:
* Full English localization of documentation and the TUI, aligning with international DevSecOps community standards.

---

<div id="en-contact"></div>

## 👤 Contact & Credits

© 2026 - **Kamal Guidadou**
*DevSecOps, SRE & Cloud Security*

* 🌐 **Portfolio**: [https://portfolio.devopsnotes.org](https://portfolio.devopsnotes.org)
* ✍️ **Tech & Cyber Blog**: [https://blog.devopsnotes.org](https://blog.devopsnotes.org)