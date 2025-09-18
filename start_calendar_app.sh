#!/bin/bash

# 🚀 Calendar App Startup Script
# This script handles all potential issues and ensures the app starts correctly

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Calendar App...${NC}"
echo "=================================="

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${YELLOW}📁 Working directory: $(pwd)${NC}"

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}❌ Error: app.py not found. Please run this script from the calendar project directory.${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: Virtual environment not found. Please create it first:${NC}"
    echo "python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Verify we're using the right Python
PYTHON_PATH=$(which python3)
echo -e "${YELLOW}🐍 Using Python: $PYTHON_PATH${NC}"

# Check if Flask is installed
echo -e "${YELLOW}🔍 Checking Flask installation...${NC}"
if ! python3 -c "import flask" 2>/dev/null; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    pip install -r requirements.txt
fi

# Verify Flask is working
echo -e "${YELLOW}✅ Verifying Flask...${NC}"
python3 -c "import flask; print('Flask version:', flask.__version__)"

# Check if database exists
if [ ! -f "calendar.db" ]; then
    echo -e "${YELLOW}📊 Database not found. It will be created on first run.${NC}"
fi

# Start the application
echo -e "${GREEN}🚀 Starting Flask application...${NC}"
echo -e "${BLUE}📱 App will be available at: http://localhost:5001${NC}"
echo -e "${YELLOW}💡 Press Ctrl+C to stop the server${NC}"
echo "=================================="

# Start the app with error handling
python3 app.py
