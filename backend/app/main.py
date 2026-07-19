from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from .routers import puzzle

app = FastAPI(title="Guess the Country")

# CORS middleware for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(puzzle.router)

# Mount static files (built frontend) in production
frontend_dist = os.path.join(os.path.dirname(__file__), '../../frontend/dist')
if os.path.exists(frontend_dist):
    app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='static')


@app.get('/health')
async def health_check():
    return {'status': 'ok'}
