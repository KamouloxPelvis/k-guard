FROM python:3.10-slim

# 1. Installation de Trivy et des dépendances de base
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    ca-certificates \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v0.49.1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Création de l'utilisateur "pseudo" (UID 1000)
# On évite d'utiliser root pour l'exécution
RUN groupadd -g 1000 kguard && \
    useradd -u 1000 -g kguard -m -s /bin/bash pseudo

WORKDIR /app

# 3. Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copie du code et gestion des droits
COPY . .

# Définition du chemin neutre (utilisé par K8s pour le montage)
ENV TRIVY_CACHE_DIR=/data/trivy-cache
# On définit aussi TRIVY_HOME pour que l'outil sache où chercher sa DB
ENV TRIVY_HOME=/data/trivy-cache

# Création du dossier neutre avec les bons droits pour "pseudo"
RUN mkdir -p /data/trivy-cache && \
    chown -R pseudo:kguard /app /data/trivy-cache

# 5. Switch vers l'utilisateur non-privilégié
USER 1000

EXPOSE 8000

# 6. Lancement (On garde tes flags de proxy)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips='*'"]