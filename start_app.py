#!/usr/bin/env python3
"""
🚀 Calendar App Startup Script
Handles all potential issues and ensures the app starts correctly
"""

import os
import sys
import subprocess
from pathlib import Path

def print_colored(text, color="white"):
    """Print colored text"""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m", 
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "white": "\033[0m"
    }
    print(f"{colors.get(color, '')}{text}\033[0m")

def check_requirements():
    """Check if all requirements are met"""
    print_colored("🔍 Checking requirements...", "yellow")
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print_colored("❌ Error: app.py not found. Please run this script from the calendar project directory.", "red")
        return False
    
    # Check if virtual environment exists
    if not Path("venv").exists():
        print_colored("❌ Error: Virtual environment not found. Please create it first:", "red")
        print("python3 -m venv venv")
        return False
    
    return True

def activate_venv():
    """Activate virtual environment and check Python path"""
    print_colored("🔧 Activating virtual environment...", "yellow")
    
    # Get the virtual environment Python path
    venv_python = Path("venv/bin/python3")
    if not venv_python.exists():
        print_colored("❌ Error: Virtual environment Python not found.", "red")
        return False
    
    print_colored(f"🐍 Using Python: {venv_python.absolute()}", "yellow")
    return str(venv_python.absolute())

def check_flask(python_path):
    """Check if Flask is installed and working"""
    print_colored("🔍 Checking Flask installation...", "yellow")
    
    try:
        result = subprocess.run([python_path, "-c", "import flask; print('Flask version:', flask.__version__)"], 
                              capture_output=True, text=True, check=True)
        print_colored(f"✅ {result.stdout.strip()}", "green")
        return True
    except subprocess.CalledProcessError:
        print_colored("📦 Installing dependencies...", "yellow")
        try:
            subprocess.run([python_path, "-m", "pip", "install", "-r", "requirements.txt"], 
                          check=True)
            print_colored("✅ Dependencies installed successfully!", "green")
            return True
        except subprocess.CalledProcessError as e:
            print_colored(f"❌ Error installing dependencies: {e}", "red")
            return False

def start_app(python_path):
    """Start the Flask application"""
    print_colored("🚀 Starting Flask application...", "green")
    print_colored("📱 App will be available at: http://localhost:5001", "blue")
    print_colored("🔐 Admin login: http://localhost:5001/admin (admin/admin123)", "blue")
    print_colored("📊 API: http://localhost:5001/api/events", "blue")
    print_colored("💡 Press Ctrl+C to stop the server", "yellow")
    print("=" * 50)
    
    try:
        # Start the app
        subprocess.run([python_path, "app.py"], check=True)
    except KeyboardInterrupt:
        print_colored("\n👋 App stopped by user.", "yellow")
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Error starting app: {e}", "red")
        return False
    
    return True

def main():
    """Main startup function"""
    print_colored("🚀 Starting Calendar App...", "blue")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Activate virtual environment
    python_path = activate_venv()
    if not python_path:
        sys.exit(1)
    
    # Check Flask
    if not check_flask(python_path):
        sys.exit(1)
    
    # Start the app
    if not start_app(python_path):
        sys.exit(1)

if __name__ == "__main__":
    main()
