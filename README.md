
⚠️ Warning: Disclaimer

*K-Guard is engineered in alignment with industry security standards and follows the [![OpenSSF Baseline](https://www.bestpractices.dev/projects/12124/baseline)](https://www.bestpractices.dev/projects/12124)*

*While security is a core priority, this software is provided as a personal and experimental Minimum Viable Product (MVP). It is designed as a research tool for exploring DevSecOps security architectures. As an evolving Open Source project, K-Guard is subject to continuous improvement and community-driven hardening.*

**K-Guard** is a security governance and observability platform for K3s clusters. It automates the full security lifecycle: Auditing (**Trivy**), Network Remediation (**Network Sentinel/Ansible**), and ChatOps Alerting (**Cisco Webex**).

---

## 📍 Summary

* [🧪 Tech Stack](#en-tech-stack)
* [🚀 Key Features](#en-key-features)
* [📖 API Documentation & Reference](#en-api-documentation--reference)
* [🛠️ Installation & Setup](#en-installation--setup)
    * [1. CLI Installer (Go)](#en-1-cli-installer-go)
    * [⚠️ CNI Recommendation](#en-network-isolation-recommendation)
    * [2. Auto-check & Dependencies](#en-2-auto-check--dependencies)
    * [3. Quick Start](#en-3-quick-start-procedure)
    * [4. Infrastructure & RBAC](#en-4-infrastructure--rbac)
* [🛰️ Cisco Webex Integration](#en-cisco-webex-integration)
* [🛡️ Network Policy (Network Sentinel)](#en-network-policy--network-sentinel)
* [👤 Contact & Credits](#en-contact--credits)

---

## 🧪 <a name="en-tech-stack"></a>Tech Stack

* **Backend**: FastAPI (Python), Ansible Core, Trivy.
* **Frontend**: Vue.js 3, Tailwind CSS, Axios (JWT Auth).
* **Installer**: Go (Bubble Tea / Lipgloss).
* **OS/Infra**: Ubuntu 24.04 LTS, K3s, Kamatera VPS.

---

## 🚀 <a name="en-key-features"></a>Key Features

* **Trivy Security Engine**: Scans container images for vulnerabilities directly from the UI.

![K-Guard System Overview](frontend/public/screenshots/kguard-3.png)

![K-Guard System Overview](frontend/public/screenshots/kguard-4.png)

* **Network Sentinel**: Implements idempotent Zero-Trust NetworkPolicies via Ansible playbooks.

![K-Guard System Overview](frontend/public/screenshots/kguard-5.png)

* **Cisco Webex ChatOps**: Real-time incident alerting with persistent integration settings in SQLite.

![K-Guard System Overview](frontend/public/screenshots/kguard-10.png)

![K-Guard System Overview](frontend/public/screenshots/kguard-12.png)

* **SRE Control Center**: Live monitoring of cluster latency, storage diagnostics, and pod health.

![K-Guard System Overview](frontend/public/screenshots/kguard-1.png)

![K-Guard System Overview](frontend/public/screenshots/kguard-2.png)

---

## 📖 API Documentation & Reference

K-Guard automatically generates interactive API documentation using **Swagger UI (OpenAPI 3.1)**. This allows developers and security auditors to explore and test all endpoints directly from the browser.

- **Interactive UI:** `https://<your-domain-or-ip>/docs`
- **Features documented:** - 🔍 K3s Infrastructure Metrics
  - 🔐 Authentication & Token management
  - 💓 System Health Checks (Liveness Probes)

> **Note:** Accessing the documentation via HTTPS is required. If using a self-signed certificate, you may need to bypass the browser security warning.

---

K-Guard génère automatiquement une documentation API interactive via **Swagger UI (OpenAPI 3.1)**. Cela permet aux développeurs et aux auditeurs de sécurité d'explorer et de tester tous les points de terminaison (endpoints) directement depuis le navigateur.

- **Interface Interactive :** `https://<votre-domaine-ou-ip>/docs`
- **Fonctionnalités documentées :**
    - 🔍 Métriques d'Infrastructure K3s
    - 🔐 Authentification & Gestion des tokens (JWT)
    - 💓 Tests de santé système (Liveness Probes)

> **Note :** L'accès à la documentation via HTTPS est obligatoire. Si vous utilisez un certificat auto-signé, vous devrez valider l'exception de sécurité dans votre navigateur pour accéder à l'interface.

---

## 🛠️ <a name="en-installation--setup"></a>Installation & Setup

![K-Guard System Overview](frontend/public/screenshots/install.png)

### <a name="en-1-cli-installer-go"></a>1. CLI Installer (Go)
Full stack deployment via a specialized **Go** installer:
* Checks system dependencies and Docker socket accessibility.
* Handles secure credential hashing with `bcrypt`.
* Syncs secrets to K3s and deploys core manifests.

### <a name="en-network-isolation-recommendation"></a>⚠️ *Network Isolation Recommendation (CNI)*
*To ensure strict micro-segmentation via Network Policies, implementing an advanced CNI (Calico, Cilium, Kube-router) is critical. Using the default Flannel CNI will keep the application functional, but East-West (inter-pod) filtering rules will be ignored by the cluster*.

### <a name="en-2-auto-check--dependencies"></a>2. Auto-check & Dependencies
The assistant launches a "Pre-flight check" script to validate the secure configuration of Docker and the K3s API. Host prerequisites:
* K3s (`curl -sfL https://get.k3s.io | sh -`).
* Docker (`sudo apt install docker.io -y`).
* Python 3 & Pip.

### <a name="en-3-quick-start-procedure"></a>3. Quick Start Procedure
```bash
# Clone the repository
git clone [https://gitlab.com/portfolio-kamal-guidadou/k-guard.git](https://gitlab.com/portfolio-kamal-guidadou/k-guard.git)

cd k-guard/installer

# Grant execution rights
chmod +x kguard-installer

# Launch installation
./kguard-installer
```
---

### <a name="en-4-infrastructure--rbac"></a>4. Infrastructure & RBAC
* **Persistence**: Uses a 5GB `PersistentVolumeClaim` (PVC) for the Trivy database cache, ensuring ultra-fast recurrent scans.
* **RBAC Policy**: Granular `ClusterRole` configuration specifically allowing metrics retrieval, Pod remediation, and `NetworkPolicy` management.
* **Performance**: Resource limits optimized for a Kamatera VPS (Requests: 500m CPU / 1Gi RAM | Limits: 1.5 CPU / 2Gi RAM).

---

## 🛰️ <a name="en-cisco-webex-integration"></a>Cisco Webex Integration

Transform technical security audits into real-time operational alerts :
1.  **Enable**: Toggle the Webex notifier directly from the **Settings** panel.
2.  **Configure**: Enter your `Bot Access Token` and your `Target Room ID`.
3.  **Validate**: Settings are persisted in the `kguard.db` SQLite database only after a successful connectivity test.

![K-Guard System Overview](frontend/public/screenshots/kguard-9.png)

---

## 🛡️ <a name="en-network-policy--network-sentinel"></a>Network Policy ( Network Sentinel )

K-Guard enforces a Zero-Trust security posture via idempotent Ansible playbooks :
* **Default Deny**: Global Ingress and Egress isolation for all protected namespaces (`k-guard`, `blog-prod`, `portfolio-prod`, etc.).
* **Selective Egress**: Authorized outgoing traffic only to critical APIs (Webex, Google Indexing, MongoDB Atlas) on port 443.
* **Visual Topology**: Dynamic traffic mapping and visual identification of vulnerable nodes within the cluster.

![K-Guard System Overview](frontend/public/screenshots/kguard-6.png)

---

## 👤 <a name="en-contact--credits"></a>Contact & Credits

© 2026 - **Kamal Guidadou** *DevSecOps, SRE & Cloud Security*

* 🌐 **Portfolio**: [https://portfolio.devopsnotes.org](https://portfolio.devopsnotes.org)
* ✍️ **Tech Blog**: [https://blog.devopsnotes.org](https://blog.devopsnotes.org)