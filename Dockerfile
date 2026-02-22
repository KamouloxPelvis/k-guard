# --- STAGE 1 : Build du Frontend (Vue.js 3) ---
FROM node:20-alpine AS build-frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- STAGE 2 : Runtime Backend (FastAPI) + Frontend statique ---
FROM python:3.11-slim
WORKDIR /app

# Installation des dépendances système pour la sécurité et le réseau
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code Backend
COPY backend/ ./backend

# Récupération du build Frontend du Stage 1
# On le place là où FastAPI pourra servir les fichiers statiques
COPY --from=build-frontend /app/frontend/dist ./static

# Variables d'environnement pour durcir l'exécution
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Lancement de l'application via Uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]