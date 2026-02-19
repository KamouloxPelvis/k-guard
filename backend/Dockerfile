FROM python:3.10-slim

# 1. Installation de Trivy et des dépendances de base
# Ajout de libffi-dev et musl-dev si bcrypt pose problème en compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    ca-certificates \
    python3-dev \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin v0.49.1 \
    && rm -rf /var/lib/apt/lists/*

# 2. Création de l'utilisateur "pseudo" (Kamal)
RUN groupadd -g 1000 kguard && \
    useradd -u 1000 -g kguard -m -s /bin/bash pseudo

WORKDIR /app

# 3. Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copie du code et gestion des droits
COPY . .

# Force Python à regarder dans le dossier courant pour les imports
ENV PYTHONPATH=/app
ENV TRIVY_CACHE_DIR=/data/trivy-cache
ENV TRIVY_HOME=/data/trivy-cache

# On s'assure que "pseudo" possède bien tout le dossier /app
RUN mkdir -p /data/trivy-cache && \
    chown -R pseudo:kguard /app /data/trivy-cache

# 5. Switch vers l'utilisateur 1000 (Kamal)
USER 1000

EXPOSE 8000

# 6. Lancement
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips='*'"]