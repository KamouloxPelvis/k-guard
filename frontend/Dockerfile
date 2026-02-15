# --- ÉTAPE 1 : BUILD ---
FROM node:lts-alpine AS build-stage

WORKDIR /app

# On garde l'essentiel pour la compilation
RUN apk add --no-cache python3 make g++

COPY package*.json ./
RUN npm install

# Plus besoin d'ARG ou d'ENV pour l'URL API ici !
ENV NODE_ENV=production

COPY . .
RUN npm run build

# --- ÉTAPE 2 : PRODUCTION ---
FROM nginx:stable-alpine AS production-stage

# Nettoyage
RUN rm -rf /usr/share/nginx/html/*

# Copie du build
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Ta config Nginx personnalisée
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]