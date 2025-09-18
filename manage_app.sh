#!/bin/bash

# 🚀 Calendar App Management Script
# Helps you start, stop, and manage your calendar app

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}🚀 Calendar App Manager${NC}"
echo "=================================="

case "$1" in
    "start")
        echo -e "${YELLOW}🔍 Checking for existing processes...${NC}"
        
        # Check if port 5001 is in use
        if lsof -i :5001 >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠️  Port 5001 is in use. Stopping existing processes...${NC}"
            pkill -f "python3.*app.py" || true
            sleep 2
        fi
        
        echo -e "${GREEN}🚀 Starting Calendar App...${NC}"
        source venv/bin/activate
        python3 app.py
        ;;
        
    "stop")
        echo -e "${YELLOW}🛑 Stopping Calendar App...${NC}"
        pkill -f "python3.*app.py" || echo "No processes found"
        echo -e "${GREEN}✅ App stopped${NC}"
        ;;
        
    "restart")
        echo -e "${YELLOW}🔄 Restarting Calendar App...${NC}"
        $0 stop
        sleep 2
        $0 start
        ;;
        
    "status")
        echo -e "${YELLOW}📊 App Status:${NC}"
        if lsof -i :5001 >/dev/null 2>&1; then
            echo -e "${GREEN}✅ App is running on http://localhost:5001${NC}"
            echo -e "${BLUE}🔐 Admin: http://localhost:5001/admin (admin/admin123)${NC}"
            echo -e "${BLUE}📡 RSS: http://localhost:5001/admin/rss-feeds${NC}"
        else
            echo -e "${RED}❌ App is not running${NC}"
        fi
        ;;
        
    "simple")
        echo -e "${GREEN}🚀 Starting Simple App (no RSS)...${NC}"
        source venv/bin/activate
        python3 start_simple_app.py
        ;;
        
    "test")
        echo -e "${YELLOW}🧪 Testing app endpoints...${NC}"
        if curl -s http://localhost:5001 >/dev/null; then
            echo -e "${GREEN}✅ Main page: http://localhost:5001${NC}"
        else
            echo -e "${RED}❌ Main page not accessible${NC}"
        fi
        
        if curl -s http://localhost:5001/api/events >/dev/null; then
            echo -e "${GREEN}✅ API: http://localhost:5001/api/events${NC}"
        else
            echo -e "${RED}❌ API not accessible${NC}"
        fi
        ;;
        
    *)
        echo -e "${BLUE}Usage: $0 {start|stop|restart|status|simple|test}${NC}"
        echo ""
        echo -e "${YELLOW}Commands:${NC}"
        echo -e "  ${GREEN}start${NC}    - Start the full calendar app"
        echo -e "  ${GREEN}stop${NC}     - Stop the calendar app"
        echo -e "  ${GREEN}restart${NC}  - Restart the calendar app"
        echo -e "  ${GREEN}status${NC}   - Check if app is running"
        echo -e "  ${GREEN}simple${NC}   - Start simple app (no RSS features)"
        echo -e "  ${GREEN}test${NC}     - Test app endpoints"
        echo ""
        echo -e "${BLUE}Examples:${NC}"
        echo -e "  $0 start    # Start the app"
        echo -e "  $0 status   # Check if running"
        echo -e "  $0 stop     # Stop the app"
        ;;
esac
