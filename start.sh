#!/bin/bash

echo "Starting Bassi Leads Backend API..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --reload --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "Starting Frontend..."
cd frontend
nohup npm run dev -- --port 5173 > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "=========================================="
echo "Bassi Leads App Started!"
echo "Backend running on http://localhost:8000"
echo "Frontend running on http://localhost:5173"
echo "To stop, run: kill $BACKEND_PID $FRONTEND_PID"
echo "=========================================="

# Keep script running to prevent nohup deaths sometimes, or just exit.
exit 0
