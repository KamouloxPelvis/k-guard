# --- STAGE 1: Frontend Build Process ---
FROM node:22-bullseye AS build-frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# --- STAGE 2: Backend Runtime ---
# Using a slim Python image to minimize the attack surface
FROM python:3.11-slim-bookworm 
WORKDIR /app

# 1. System Dependencies
# Minimalist approach: keep only what's necessary for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Dependency Management
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 3. Source Code Placement
COPY backend/ ./backend/
COPY tests/ ./tests/
COPY infra/ ./infra/

# 4. Frontend Integration
COPY --from=build-frontend /app/frontend/dist /app/static

# 5. Runtime Configuration
WORKDIR /app/backend

# SRE Fix: Add the root directory to PYTHONPATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# 6. Service Execution
# Drop privileges to non-root user (ID 1000 is standard for most images)
USER 1000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]