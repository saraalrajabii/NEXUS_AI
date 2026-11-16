# Production image for the NEXUS frontend.
# Stage 1 builds the React app into static files; stage 2 serves them with Caddy (see Caddyfile).
# Local development does NOT use this file — keep using `npm run dev`.

FROM node:24.16.0-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2.11.8-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
# The base image already runs: caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
