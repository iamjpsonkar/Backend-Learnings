# ui/Dockerfile — React/Vite dashboard
# Multi-stage: Node build → Nginx serve

FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (for layer caching)
COPY package.json ./
RUN npm install --frozen-lockfile 2>/dev/null || npm install

# Copy source and build
COPY . .

ARG VITE_API_URL=http://localhost:4567
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ─────────────────────────────────────────────
# Runtime: serve static files with Nginx
# ─────────────────────────────────────────────
FROM nginx:alpine AS runtime

LABEL com.cloudlabs.project="local-cloud-lab"
LABEL com.cloudlabs.service="ui"

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx config for SPA (React Router support)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
