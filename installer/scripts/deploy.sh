stages:
  - build
  - deploy

build_images:
  stage: build
  image: docker:24.0.5
  services:
    - docker:24.0.5-dind
  script:
    - echo "🚀 Déploiement/Mise à jour du cluster k3s sur $VPS_IP..."
    - ssh $VPS_USER@$VPS_IP "kubectl apply -f /home/kamal/infrastructure/apps/k-guard/k8s/ -n k-guard"
    - ssh $VPS_USER@$VPS_IP "kubectl rollout restart deployment kguard-deployment -n k-guard"
    - ssh $VPS_USER@$VPS_IP "kubectl rollout status deployment kguard-deployment -n k-guard --timeout=60s"
  only:
    - main

deploy_to_k3s:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client curl
    - eval $(ssh-agent -s)
    # On utilise cat pour lire le fichier de clé (type File) et on force le format
    - cat "$CI_CD_SSH_KEY" | tr -d '\r' > temp_key
    - chmod 600 temp_key
    - ssh-add temp_key
    - rm temp_key
    - mkdir -p ~/.ssh
    - chmod 700 ~/.ssh
    - ssh-keyscan $VPS_IP >> ~/.ssh/known_hosts
    - chmod 644 ~/.ssh/known_hosts
  script:
    - echo "🚀 Mise à jour du cluster k3s sur $VPS_IP..."
    - ssh $VPS_USER@$VPS_IP "kubectl rollout restart deployment kguard-deployment -n k-guard"
    - ssh $VPS_USER@$VPS_IP "kubectl rollout status deployment kguard-deployment -n k-guard --timeout=60s"
  after_script:
    - |
      if [ "$CI_JOB_STATUS" == "success" ]; then
        curl -X POST -H "Content-Type: application/json" -d "{\"content\": \"🛡️ **K-GUARD** (k3s) : Déploiement réussi par **$GITLAB_USER_NAME** ! ✅\"}" $DISCORD_WEBHOOK_URL
      else
        curl -X POST -H "Content-Type: application/json" -d "{\"content\": \"⚠️ **K-GUARD** (k3s) : Échec critique du déploiement ! ❌\"}" $DISCORD_WEBHOOK_URL
      fi
  only:
    - main