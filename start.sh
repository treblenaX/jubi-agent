#!/bin/bash
# Jubi Agent Startup Script
# Starts server first, then client

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
CLIENT_DIR="$SCRIPT_DIR/client/jubi-client"

echo "🚀 Starting Jubi Agent..."

# Start server first (needs to be ready before client connects)
cd "$SERVER_DIR"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 2024 --reload &
SERVER_PID=$!
echo "Server started (PID: $SERVER_PID)"

# Small delay to ensure server is ready
sleep 2

# Start client dev server in background
cd "$CLIENT_DIR"
./node_modules/.bin/vite dev --host 0.0.0.0 &
CLIENT_PID=$!
echo "Client started (PID: $CLIENT_PID)"

echo ""
echo "✅ Jubi Agent is running!"
echo "   Client: http://localhost:5173/"
echo "   API:    http://localhost:2024"
echo ""
echo "To stop: kill $SERVER_PID $CLIENT_PID"

# Wait for both processes
wait
