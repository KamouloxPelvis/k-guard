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

# Installation des dépendances système + TRIVY (Dépôt Officiel Stable)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    lsb-release \
    ca-certificates \
    && mkdir -p /usr/share/keyrings \
    && curl -tfL https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y trivy \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 1. Installation des requirements (Placé avant le COPY backend pour optimiser le cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Setup du dossier Backend
COPY backend/ ./backend
WORKDIR /app/backend

# Gestion de la DB SQLite et permissions
RUN touch kguard.db && chmod 666 kguard.db

# 3. Récupération du frontend
COPY --from=build-frontend /app/frontend/dist /app/static

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]