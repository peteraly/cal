#!/usr/bin/env python3
"""
Comprehensive diagnostic script for the calendar app
"""

import sys
import os
import subprocess
import importlib.util

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n📋 {title}")
    print("-" * 40)

def check_python_environment():
    print_section("Python Environment")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path[:3]}...")  # Show first 3 paths

def check_virtual_environment():
    print_section("Virtual Environment")
    venv_path = os.path.join(os.getcwd(), 'venv')
    if os.path.exists(venv_path):
        print("✅ Virtual environment directory exists")
        
        # Check if we're in a virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("✅ Currently running in virtual environment")
        else:
            print("❌ NOT running in virtual environment")
            
        # Check venv Python executable
        venv_python = os.path.join(venv_path, 'bin', 'python3')
        if os.path.exists(venv_python):
            print(f"✅ Virtual environment Python exists: {venv_python}")
        else:
            print(f"❌ Virtual environment Python not found: {venv_python}")
    else:
        print("❌ Virtual environment directory not found")

def check_python_packages():
    print_section("Python Packages")
    
    packages_to_check = [
        'flask',
        'sqlite3',
        'requests',
        'feedparser',
        'schedule'
    ]
    
    for package in packages_to_check:
        try:
            if package == 'sqlite3':
                import sqlite3
                print(f"✅ {package}: {sqlite3.version}")
            else:
                module = importlib.import_module(package)
                version = getattr(module, '__version__', 'unknown')
                print(f"✅ {package}: {version}")
        except ImportError as e:
            print(f"❌ {package}: Not installed ({e})")

def check_project_files():
    print_section("Project Files")
    
    required_files = [
        'app.py',
        'calendar.db',
        'requirements.txt',
        'templates/',
        'static/',
        'rss_manager.py',
        'rss_scheduler.py'
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                print(f"✅ {file_path}/ (directory)")
            else:
                size = os.path.getsize(file_path)
                print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path}: Not found")

def check_database():
    print_section("Database")
    
    db_path = 'calendar.db'
    if os.path.exists(db_path):
        print(f"✅ Database file exists: {db_path}")
        
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            print(f"✅ Database tables: {[table[0] for table in tables]}")
            
            # Check events count
            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]
            print(f"✅ Events in database: {event_count}")
            
            conn.close()
        except Exception as e:
            print(f"❌ Database error: {e}")
    else:
        print(f"❌ Database file not found: {db_path}")

def check_network_ports():
    print_section("Network Ports")
    
    import socket
    
    def check_port(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    
    ports_to_check = [5000, 5001, 5002, 8000, 8080]
    
    for port in ports_to_check:
        if check_port(port):
            print(f"⚠️  Port {port}: In use")
        else:
            print(f"✅ Port {port}: Available")

def check_flask_app():
    print_section("Flask App Test")
    
    try:
        # Try to import the app
        sys.path.insert(0, os.getcwd())
        from app import app
        print("✅ Flask app imported successfully")
        
        # Check app routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.rule} -> {rule.endpoint}")
        
        print(f"✅ App has {len(routes)} routes")
        print("📋 Key routes:")
        for route in routes[:10]:  # Show first 10 routes
            print(f"   {route}")
        if len(routes) > 10:
            print(f"   ... and {len(routes) - 10} more")
            
    except Exception as e:
        print(f"❌ Flask app error: {e}")
        import traceback
        traceback.print_exc()

def check_rss_system():
    print_section("RSS System")
    
    try:
        from rss_manager import RSSManager
        print("✅ RSS Manager imported successfully")
        
        # Test RSS manager
        rss_manager = RSSManager('calendar.db')
        feeds = rss_manager.get_feed_status()
        print(f"✅ RSS feeds in database: {len(feeds)}")
        
        for feed in feeds:
            print(f"   📡 {feed['name']}: {feed['total_events']} events")
            
    except Exception as e:
        print(f"❌ RSS system error: {e}")

def run_simple_flask_test():
    print_section("Simple Flask Test")
    
    try:
        from flask import Flask
        app = Flask(__name__)
        
        @app.route('/')
        def test():
            return 'Test successful!'
        
        print("✅ Simple Flask app created successfully")
        print("💡 To test: Run this app and visit http://localhost:5001")
        
    except Exception as e:
        print(f"❌ Simple Flask test failed: {e}")

def main():
    print_header("Calendar App Diagnostic")
    print("This script will check all components of your calendar app")
    
    check_python_environment()
    check_virtual_environment()
    check_python_packages()
    check_project_files()
    check_database()
    check_network_ports()
    check_flask_app()
    check_rss_system()
    run_simple_flask_test()
    
    print_header("Diagnostic Complete")
    print("Review the results above to identify any issues.")
    print("✅ = Working correctly")
    print("❌ = Issue found")
    print("⚠️  = Warning")

if __name__ == '__main__':
    main()

