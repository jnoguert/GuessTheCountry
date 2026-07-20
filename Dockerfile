# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend-builder

# Vite bakes these into the static bundle at build time, not read at
# container runtime -- they must be passed as --build-arg (see
# docker-compose.yml's build.args), a plain `environment:` entry on the
# service has no effect on an already-built image. Optional: leaving them
# unset just means the leaderboard doesn't appear.
ARG VITE_SUPABASE_URL=""
ARG VITE_SUPABASE_ANON_KEY=""
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}

WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit
COPY frontend/ .
RUN npm run build

# ---- Stage 2: Python backend serving API + built frontend ----
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/pipeline ./pipeline
COPY backend/data ./data

# Built frontend, served by FastAPI from the same origin
COPY --from=frontend-builder /build/dist ./static

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=10s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
