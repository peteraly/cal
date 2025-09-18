#!/usr/bin/env python3
"""
Simple app starter without RSS scheduler to test basic functionality
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date, timedelta
import sqlite3
import os
from functools import wraps
import hashlib
from dotenv import load_dotenv
import json
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database setup
DATABASE = 'calendar.db'

def init_db():
    """Initialize the database with events and categories tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT NOT NULL
        )
    ''')
    
    # Create events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT,
            description TEXT,
            location TEXT,
            location_name TEXT,
            address TEXT,
            price_info TEXT,
            url TEXT,
            tags TEXT,
            category_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Insert default categories if they don't exist
    default_categories = [
        ('Literature', '#3B82F6'),
        ('Music', '#10B981'),
        ('Theater', '#F59E0B'),
        ('Art', '#EF4444'),
        ('Dance', '#8B5CF6'),
        ('Film', '#06B6D4'),
        ('Comedy', '#84CC16'),
        ('Education', '#F97316'),
        ('Community', '#EC4899'),
        ('Other', '#6B7280')
    ]
    
    for name, color in default_categories:
        cursor.execute('INSERT OR IGNORE INTO categories (name, color) VALUES (?, ?)', (name, color))
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    """Public calendar view"""
    return render_template('public.html')

@app.route('/admin')
def admin():
    """Admin dashboard"""
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_new.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login"""
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':  # Simple password for demo
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Invalid password')
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/api/events')
def get_events():
    """Get all events"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT e.*, c.name as category_name, c.color as category_color
        FROM events e
        LEFT JOIN categories c ON e.category_id = c.id
        ORDER BY e.start_datetime ASC
    ''')
    
    events = []
    for row in cursor.fetchall():
        event = {
            'id': row[0],
            'title': row[1],
            'start_datetime': row[2],
            'end_datetime': row[3],
            'description': row[4],
            'location': row[5],
            'location_name': row[6],
            'address': row[7],
            'price_info': row[8],
            'url': row[9],
            'tags': row[10],
            'category_id': row[11],
            'created_at': row[12],
            'updated_at': row[13],
            'category_name': row[14],
            'category_color': row[15]
        }
        events.append(event)
    
    conn.close()
    return jsonify(events)

if __name__ == '__main__':
    print('🚀 Starting Simple Calendar App...')
    init_db()
    print('✅ Database initialized')
    print('📱 App will be available at: http://localhost:5001')
    print('💡 Press Ctrl+C to stop')
    app.run(debug=True, port=5001, host='127.0.0.1')
