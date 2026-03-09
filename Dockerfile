# --- STAGE 1: Frontend Build Process ---
# Using a lightweight Alpine image to build the Vue.js assets
FROM node:20-alpine AS build-frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- STAGE 2: Backend Runtime (FastAPI) + Static Frontend ---
# Slim Python image to reduce attack surface and image size
FROM python:3.11-slim
WORKDIR /app

# 1. System Dependencies + Trivy & Kubectl Installation
# Installing curl and certificates, then downloading Trivy and Kubectl binaries
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl && mv kubectl /usr/local/bin/ \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Dependency Management (Cache Optimization)
# Copying only requirements first to leverage Docker layer caching
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Backend & SRE Scripts Setup
# Copying the local backend source code into the container
COPY backend/ ./backend/
# SRE Fix: Explicitly copying infrastructure and test scripts into the container
COPY test/ /app/test/
COPY infra/ /app/infra/
WORKDIR /app/backend

# 4. Persistence Setup (K-Guard SQLite permissions)
# Ensuring the local database and directory are writable for the non-root user
RUN touch kguard.db && chmod 777 kguard.db && chmod 777 .

# 5. Frontend Integration
# Pulling the compiled static assets from Stage 1 into the backend static folder
COPY --from=build-frontend /app/frontend/dist /app/static

# Runtime Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

EXPOSE 8000

# Service Execution Command
# Running Uvicorn on all interfaces to be accessible via Kubernetes Services
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]