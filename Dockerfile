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

# 1. Dépendances système + Trivy (Portable)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Installation des requirements (Optimisation cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Setup du code Backend
# On copie le CONTENU du dossier local backend dans /app/backend du conteneur
COPY backend/ ./backend/
WORKDIR /app/backend

# 4. Fix des permissions SQLite pour K-Guard
RUN touch kguard.db && chmod 777 kguard.db && chmod 777 .

# 5. Récupération du frontend
COPY --from=build-frontend /app/frontend/dist /app/static

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

EXPOSE 8000

# Commande de lancement
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]