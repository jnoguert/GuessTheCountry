#!/bin/bash

# GuessTheCountry - Codespace Launcher
# Run this with: bash start-codespace.sh

echo "================================"
echo "Guess the Country - Codespace Setup"
echo "================================"
echo ""

# Ensure we're at the repo root
if [ ! -f "backend/requirements.txt" ]; then
  echo "Error: Not at repo root. Run from the repository root directory."
  exit 1
fi

echo "✓ Found repository structure"
echo ""

# Backend setup
echo "Setting up backend..."
cd backend
pip install -q -r requirements.txt
echo "✓ Backend dependencies installed"
cd ..

# Frontend setup
echo "Setting up frontend..."
cd frontend
npm install -q --no-audit
echo "✓ Frontend dependencies installed"
cd ..

echo ""
echo "================================"
echo "Ready to run!"
echo "================================"
echo ""
echo "Terminal 1 - Backend:"
echo "  cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Terminal 2 - Frontend:"
echo "  cd frontend && npm run dev -- --host 0.0.0.0"
echo ""
echo "Then open the Codespace URL (port 5173)"
echo ""
