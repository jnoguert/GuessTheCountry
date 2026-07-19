from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .routers import puzzle

app = FastAPI(title="Guess the Country")

# CORS middleware for dev setups where the frontend runs on its own port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(puzzle.router)


@app.get('/health')
async def health_check():
    return {'status': 'ok'}


# Serve the built frontend from the same origin (single-container deploys,
# Docker, Codespaces). Mounted LAST so it never shadows /api or /health.
for candidate in ('../../frontend/dist', '../static'):
    frontend_dist = os.path.join(os.path.dirname(__file__), candidate)
    if os.path.isdir(frontend_dist):
        app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='static')
        break
