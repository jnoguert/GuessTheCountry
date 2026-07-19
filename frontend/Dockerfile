FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --no-audit

# Copy source
COPY . .

# API base URL must be baked in at build time (Vite static build)
ARG VITE_API_BASE=http://localhost:8000/api
ENV VITE_API_BASE=$VITE_API_BASE

# Build
RUN npm run build

# Production stage
FROM node:20-slim

WORKDIR /app

# Install serve to run the static app
RUN npm install -g serve

# Copy built app from builder
COPY --from=builder /app/dist ./dist

EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:5173', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})" || exit 1

# Serve the app
CMD ["serve", "-s", "dist", "-l", "5173"]
