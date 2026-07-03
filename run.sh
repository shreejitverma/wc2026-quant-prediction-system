#!/bin/bash
echo "Starting WC2026 Quant Dashboard..."

# Start FastAPI in background
uv run uvicorn src.wc2026.api.server:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Start Next.js in background
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "Dashboard running at http://localhost:3000"
echo "API running at http://localhost:8000/docs"
echo "Press Ctrl+C to stop both."

trap "kill $API_PID $FRONTEND_PID" EXIT
wait
