# ---- Stage 1: build the frontend ----
FROM node:20-slim AS frontend-builder

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
