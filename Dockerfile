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

# Installation des dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 1. On installe les requirements à la racine
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. ON CHANGE LE WORKDIR ICI
# On se place DIRECTEMENT dans le dossier backend
WORKDIR /app/backend

# 3. On copie le contenu du dossier backend ICI (.)
COPY backend/ .

# Création manuelle du fichier vide pour garantir les permissions
# Cela évite que SQLite ne doive "créer" le fichier, il n'aura qu'à l'ouvrir.
RUN touch kguard.db && chmod 666 kguard.db

# Permissions sur le dossier pour les fichiers temporaires SQLite
RUN chmod 777 /app/backend

# 4. On récupère le frontend statique (on le met un niveau au-dessus pour rester propre)
COPY --from=build-frontend /app/frontend/dist /app/static

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Plus besoin de PYTHONPATH complexe, on est déjà dans le bon dossier
ENV PYTHONPATH=/app/backend

EXPOSE 8000

# Lancement simplifié : on est dans /app/backend, donc main:app suffit
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]