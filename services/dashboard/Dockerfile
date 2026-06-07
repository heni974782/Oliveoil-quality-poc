# Stage 1 — build React app
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json .
RUN npm install

COPY . .

# Token injected at build time via docker-compose build arg.
# Baked into the JS bundle — acceptable for a POC internal dashboard.
ARG VITE_API_TOKEN
ENV VITE_API_TOKEN=${VITE_API_TOKEN}

RUN npm run build

# Stage 2 — serve with Nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
