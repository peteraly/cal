#!/bin/bash

echo "🔄 Restarting Calendar Application..."

# Kill any existing Python processes on port 5001
echo "🛑 Stopping existing processes..."
pkill -f "python3 app.py" 2>/dev/null || true

# Wait a moment for processes to stop
sleep 2

# Check if port 5001 is still in use
if lsof -i :5001 >/dev/null 2>&1; then
    echo "⚠️  Port 5001 is still in use. Killing processes..."
    lsof -ti :5001 | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Navigate to the project directory
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"

# Activate virtual environment
echo "🐍 Activating virtual environment..."
source venv/bin/activate

# Start the application
echo "🚀 Starting application..."
python3 app.py
