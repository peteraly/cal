#!/usr/bin/env python3
"""
Startup script for the Calendar App
"""
import os
import sys
import subprocess

def main():
    """Start the calendar app"""
    print("🚀 Starting Calendar App...")
    print("=" * 50)
    
    # Check if virtual environment exists
    if not os.path.exists('venv'):
        print("❌ Virtual environment not found!")
        print("Please run: python3 -m venv venv")
        print("Then: source venv/bin/activate && pip install -r requirements.txt")
        return 1
    
    # Check if requirements are installed
    try:
        import flask
        import dotenv
    except ImportError:
        print("❌ Dependencies not installed!")
        print("Please run: source venv/bin/activate && pip install -r requirements.txt")
        return 1
    
    print("✅ Dependencies found")
    print("🌐 Starting Flask server on http://localhost:5001")
    print("📱 Public view: http://localhost:5001")
    print("🔐 Admin login: http://localhost:5001/admin/login")
    print("👤 Login: admin / admin123")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the Flask app
    try:
        from app import app, init_db
        init_db()
        app.run(debug=True, port=5001)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
        return 0
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
