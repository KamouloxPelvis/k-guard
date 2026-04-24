# Changelog

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [1.1.4] - 2026-04-24

### Added
- **Sentinel RBAC Identity**: Déploiement d'une `ServiceAccount` dédiée (`sentinel-auditor`) pour les pods de diagnostic, garantissant des tests de connectivité sécurisés et autorisés.
- **Enhanced SRE Diagnostics**: Nouvel endpoint backend `/debug-storage` pour surveiller l'état des volumes persistants (PV) et l'intégrité du cache Trivy.
- **Dynamic Port Mapping**: Le moteur Ansible extrait désormais automatiquement les ports des conteneurs pour maintenir la disponibilité des services pendant le durcissement Zero-Trust.

### Changed
- **Webex Resilience**: Refactorisation du `CiscoWebexNotifier` pour supporter plusieurs schémas JSON de rapports, évitant les échecs de notification ChatOps.
- **Structured Logging**: Remplacement des sorties standards par un système de logs centralisé conforme aux normes SRE (`INFO`, `WARNING`, `ERROR`).
- **Network Policy Hardening**: Mise à jour de `audit_exception.j2` avec des sélecteurs DNS élargis pour assurer la compatibilité avec toutes les distributions K3s.

### Fixed
- **Sentinel Audit**: Résolution du statut "All Fails" dans les tests de connectivité en alignant les Network Policies et les ServiceAccounts du pod diagnostic.
- **Data Persistence**: Correction des crashs de tâches de fond dans `run_and_store_scan` lors de la réception de structures de rapports inattendues.
- **System Overview**: Correction de la route `cluster-status` pour garantir que le Dashboard affiche correctement la topologie des pods et des nœuds.

## [1.1.0] - 2026-04-23

### Added
- Interfaces TypeScript strictes pour les Pods, Nodes et Network Edges.
- Nouveau terminal de test de connectivité dans l'UI Network Sentinel.
- Logique de score de sécurité basée sur le statut de micro-segmentation.

### Changed
- **Major**: Migration de la couche réseau d'Axios vers l'API native Fetch.
- Refactorisation du service API avec un wrapper personnalisé pour une meilleure gestion des erreurs.
- Mise à jour de la documentation UI et des commentaires selon les standards SRE internationaux.

### Fixed
- Correction des crashs UI en production liés aux données nulles de l'API K3s.
- Correction de la logique de synchronisation de l'intégration Cisco Webex.
- Stabilisation du rendu de la carte topologique dans SentinelView.

## [1.0.0] - 2026-03-09

### Added
- Release initiale du MVP K-Guard.
- Intégration du moteur de scan de sécurité Trivy.
- Alertes ChatOps via Cisco Webex.
- Documentation interactive Swagger UI.
- Network Sentinel propulsé par Ansible pour les politiques Zero-Trust.