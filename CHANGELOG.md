# Changelog

## [1.1.0] - 2026-04-23

### Added
- Strict TypeScript interfaces for Kubernetes Pods, Nodes, and Network Edges.
- New connectivity test terminal in Network Sentinel UI.
- Security scoring logic based on micro-segmentation status.

### Changed
- **Major**: Migrated entire network layer from Axios to native Fetch API.
- Refactored API service with a custom wrapper for better error handling.
- Updated UI documentation and comments to international SRE standards.

### Fixed
- Resolved production UI crashes related to null data from the K3s API.
- Fixed Cisco Webex integration synchronization logic.
- Stabilized topology map rendering in SentinelView.

## [1.0.0] - 2026-03-09
### Added
- Initial release of K-Guard MVP.
- Trivy security scanning integration.
- Cisco Webex ChatOps alerting.
- Interactive Swagger UI documentation.
- Ansible-powered Network Sentinel for Zero-Trust policies.