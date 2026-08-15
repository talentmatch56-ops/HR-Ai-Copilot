@echo off
title HR AI Copilot Launchpad
echo ===================================================
echo             LAUNCHING HR AI COPILOT
echo ===================================================
echo.

echo [1/3] Spinning up FastAPI Backend Service...
start cmd /k "echo --- Backend Server --- && cd backend && pip install -r requirements.txt && uvicorn main:app --app-dir app --reload --port 8000"

echo [2/3] Starting MCP Tool Server...
start cmd /k "echo --- MCP Server --- && cd mcp-server && pip install -r requirements.txt && python server.py"

echo [3/3] Preparing Next.js 15 Frontend...
start cmd /k "echo --- Next.js Frontend --- && cd frontend && npm install --legacy-peer-deps && npm run dev"

echo.
echo ===================================================
echo Services are boot strapping!
echo.
echo Dashboard: http://localhost:3000
echo Backend API: http://localhost:8000
echo ===================================================
pause
