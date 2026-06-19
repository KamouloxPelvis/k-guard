# Changelog

All notable changes to this project will be documented in this file.

## [1.3.1] - 2026-06-18

### Changed
- **Infrastructure**: Complete migration from Systemd/VPS-bound services to Kubernetes-native architecture (K3s).
- **Network Configuration**: Port changed from `8445` to `8000` to align with internal cluster networking.
- **Installer**: Refactored `main.go` to handle K8s namespace initialization and secret management.
- **Documentation**: Updated README to reflect K8s deployment procedures and removed obsolete Systemd management commands.
- **Frontend**: Stabilized `SentinelView` component with `v-show` directives and improved lifecycle handling (`onActivated`).

## [1.2.1] - 2026-06-15

### Fixed
Port Migration: Resolved network conflicts by migrating the API/Frontend service from port 8443 to 8445.

Auth Stability: Resolved internal 500 errors during authentication by optimizing middleware stack handling.

Asset Serving: Corrected static file resolution logic in FastAPI to properly serve the Vue.js frontend build from /frontend/dist.

Instrumentation: Refined Prometheus middleware to ensure compatible metric collection without breaking router path resolution.

Infrastructure
Updated systemd service configuration to align with the new port architecture.

Updated environment variable definitions to ensure robust path resolution across development and production environments.

## [1.2.0] - 2026-05-12

### Added
- **Universal Go Installer**: Implemented a robust binary-based installation engine for one-click deployments.
- **Automated Frontend Bridge**: The installer now automatically links the Vue.js production build (`dist`) to the FastAPI backend (`static`), ensuring "Zero-Touch" UI availability.
- **Global CLI Command**: Added the `kguard` command for instant access to logs, status, and Kubernetes diagnostics.

### Changed
- **Path Resolution**: Migrated from relative execution paths to absolute path detection using `os.Executable()`, making the installer bulletproof regardless of the working directory.
- **Service Management**: Refactored the Systemd unit logic to ensure a safe and idempotent restart sequence.
- **Code Standards**: Updated all internal installer comments to international English standards (Cisco/SRE compliant).

### Fixed
- **Runtime Error**: Resolved the critical "static/index.html not found" error by ensuring the deployment bridge is created before the service starts.
- **Idempotency**: Fixed "file exists" errors during re-installation by implementing proactive cleanup of legacy symbolic links.

## [1.1.5] - 2026-04-24

### Changed
- **Sentinel Audit Logic**: Pivoted diagnostics toward strict isolation validation (Zero-Trust) instead of simple connectivity.
- **Audit UI**: Cleaned up the test terminal to focus exclusively on critical security metrics (Internal Mesh & Egress).

### Fixed
- **False Negatives**: Removed failures related to external DNS in hardened environments, prioritizing proof of network air-gapping and isolation.

## [1.1.4] - 2026-04-24

### Added
- **Sentinel RBAC Identity**: Deployed a dedicated `ServiceAccount` (`sentinel-auditor`) for diagnostic pods, ensuring secure and authorized connectivity checks.
- **Enhanced SRE Diagnostics**: New `/debug-storage` backend endpoint to monitor Persistent Volume (PV) health and Trivy cache integrity.
- **Dynamic Port Mapping**: The Ansible engine now automatically extracts container ports to maintain service availability during Zero-Trust hardening.

### Changed
- **Webex Resilience**: Refactored `CiscoWebexNotifier` to support multiple JSON report schemas, preventing ChatOps notification failures.
- **Structured Logging**: Replaced standard outputs with a centralized SRE-compliant logging system (`INFO`, `WARNING`, `ERROR`).
- **Network Policy Hardening**: Updated `audit_exception.j2` with broader DNS selectors to ensure compatibility across various K3s distributions.

### Fixed
- **Sentinel Audit**: Resolved "All Fails" status in connectivity tests by aligning Network Policies and ServiceAccounts for the diagnostic pod.
- **Data Persistence**: Fixed background task crashes in `run_and_store_scan` when encountering unexpected report structures.
- **System Overview**: Fixed the `cluster-status` route to ensure the Dashboard correctly populates pod and node topology.

## [1.1.0] - 2026-04-23

### Added
- Strict TypeScript interfaces for Pods, Nodes, and Network Edges.
- New connectivity test terminal within the Network Sentinel UI.
- Security scoring logic based on micro-segmentation status.

### Changed
- **Major**: Migrated the entire network layer from Axios to the native Fetch API.
- Refactored the API service with a custom wrapper for enhanced error handling.
- Updated UI documentation and comments to international SRE standards.

### Fixed
- Resolved production UI crashes related to null data from the K3s API.
- Fixed Cisco Webex integration synchronization logic.
- Stabilized topology map rendering in SentinelView.

## [1.0.0] - 2026-03-09

### Added
- Initial release of K-Guard MVP.
- Trivy security scanning integration.
- ChatOps alerting via Cisco Webex.
- Interactive Swagger UI documentation.
- Network Sentinel powered by Ansible for Zero-Trust policies.