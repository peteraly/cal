#!/bin/bash

echo "🚀 Starting Calendar App..."

# Activate virtual environment
source venv/bin/activate

# Start the app
echo "📱 Starting Flask app on http://localhost:5001"
echo "💡 Press Ctrl+C to stop the server"
echo ""

python3 app.py

