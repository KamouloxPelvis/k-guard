# --- STAGE 1: Frontend Build Process ---
# Using a lightweight Alpine image to compile Vue.js assets
FROM node:20-alpine AS build-frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- STAGE 2: Backend Runtime ---
# Using a slim Python image to minimize the attack surface
FROM python:3.11-slim
WORKDIR /app

# 1. System Dependencies
# Installing essential tools for SRE operations and security scanning
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" \
    && chmod +x kubectl && mv kubectl /usr/local/bin/ \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Dependency Management
# Leveraging Docker layer caching by copying requirements first
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Source Code Placement
# Copying backend and infrastructure components to their expected paths
COPY backend/ ./backend/
COPY tests/ ./tests/
COPY infra/ ./infra/

# 4. Frontend Integration
# Importing compiled static assets from Stage 1
COPY --from=build-frontend /app/frontend/dist /app/static

# 5. Runtime Configuration & Persistence
# Transition to the backend directory for the application runtime
WORKDIR /app/backend

# Initialize SQLite database and set appropriate file permissions
RUN touch kguard.db && chmod 777 kguard.db && chmod 777 .

# SRE Fix: Add the root directory to PYTHONPATH to allow relative 'backend.' imports
# This ensures uvicorn can locate modules correctly from within the /app/backend directory
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Service Execution
# Ensure all files are accessible with non-root compliant permissions
RUN chmod -R 755 /app

# Launch Uvicorn, pointing to the main app module
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]