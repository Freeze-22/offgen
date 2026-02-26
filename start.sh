#!/bin/bash
echo ""
echo "╔══════════════════════════════════╗"
echo "║      STARTING OFFREPL            ║"
echo "╚══════════════════════════════════╝"
echo ""

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo "🚀 Starting Ollama..."
    ollama serve &
    sleep 2
fi

# Start backend
echo "⚙️  Starting backend on :8000"
cd ~/Downloads/offrepl
PYTHONPATH=. python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

sleep 2

# Start frontend
echo "🎨 Starting frontend on :5173"
cd ~/Downloads/offrepl/frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ OffRepl is running!"
echo "   Open:  http://localhost:5173"
echo "   API:   http://localhost:8000"
echo "   Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" EXIT INT TERM
wait
