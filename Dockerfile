# --- STAGE 1 : Build du Frontend (Inchangé) ---
FROM node:20-alpine AS build-frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- STAGE 2 : Runtime Backend (FastAPI) + Frontend statique ---
FROM python:3.11-slim
WORKDIR /app

# Installation des dépendances système + TRIVY via script (Portable & Robuste)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 1. Installation des requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Setup du dossier Backend et permissions SQLite
WORKDIR /app/backend

# On crée le fichier et on s'assure que TOUT le dossier est scriptable
RUN touch kguard.db && \
    chmod 666 kguard.db && \
    chmod 777 /app/backend

# Optionnel mais recommandé pour le DevSecOps : 
# S'assurer que l'app peut écrire dans son propre répertoire
RUN chown -R 1000:1000 /app/backend

# Gestion de la DB SQLite et permissions
RUN touch kguard.db && chmod 666 kguard.db

# 3. Récupération du frontend
COPY --from=build-frontend /app/frontend/dist /app/static

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]