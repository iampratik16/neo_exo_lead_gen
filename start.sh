#!/bin/zsh
source ~/.zshrc

echo "Starting Neo Eco Cleaning — Lead Generator Backend API..."
cd backend
source venv/bin/activate
nohup uvicorn main:app --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

echo "Starting Frontend..."
cd frontend
nohup npm run dev -- --port 5173 > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "================================================"
echo "  Neo Eco Cleaning — Lead Generator Started!"
echo "================================================"
echo "  Backend running on http://localhost:8000"
echo "  Frontend running on http://localhost:5173"
echo "  To stop, run: kill $BACKEND_PID $FRONTEND_PID"
echo "================================================"

exit 0
