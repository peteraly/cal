#!/usr/bin/env python3
"""
Simplified Calendar Application Startup Script
"""

import os
import sys
from app_simplified import app

if __name__ == '__main__':
    print("🚀 Starting Simplified Calendar Application...")
    print("📊 Database: 3 tables (simplified from 15+)")
    print("🔧 API Endpoints: 10 (simplified from 30+)")
    print("📱 Frontend: Clean, responsive design")
    print("🤖 Features: Event management, RSS feeds, AI parsing")
    print("")
    print("🌐 Public view: http://localhost:5001")
    print("👤 Admin view: http://localhost:5001/admin")
    print("🔑 Admin login: admin / admin123")
    print("")
    
    # Run the application
    app.run(debug=True, port=5001, host='0.0.0.0')
