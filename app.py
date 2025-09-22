from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date, timedelta
import sqlite3
import os
from functools import wraps
import hashlib
from dotenv import load_dotenv
from ai_parser import EventParser, suggest_recurrence, analyze_event_importance, SearchParser
from sync_service import SyncService
from rss_manager import RSSManager, start_rss_scheduler, get_scheduler_status
from web_scraper_manager import WebScraperManager, start_web_scraper_scheduler, get_scraper_scheduler_status
import json
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database setup
DATABASE = 'calendar.db'

# Kennedy Center URL constant
KENNEDY_CENTER_CALENDAR_URL = 'https://www.kennedy-center.org/whats-on/calendar/'

# Initialize sync service
sync_service = SyncService(DATABASE)

# Initialize RSS manager and Web Scraper manager
rss_manager = RSSManager(DATABASE)
web_scraper_manager = WebScraperManager(DATABASE)

def require_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

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
    
    # Create events table with category reference, tags, pricing, and URL
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
            category_id INTEGER,
            tags TEXT,
            price_info TEXT,
            url TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Add URL column to existing events table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN url TEXT')
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Create monitored_urls table for scraper
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            name TEXT,
            enabled BOOLEAN DEFAULT 1,
            scrape_frequency TEXT DEFAULT 'daily',
            last_scraped TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create scraper_logs table for tracking scraper activities
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraper_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER,
            status TEXT NOT NULL,
            message TEXT,
            events_found INTEGER DEFAULT 0,
            events_added INTEGER DEFAULT 0,
            error_details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (url_id) REFERENCES monitored_urls (id)
        )
    ''')
    
    # Create scraped_events table for events pending review
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraped_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER,
            title TEXT NOT NULL,
            start_datetime TEXT,
            description TEXT,
            location TEXT,
            location_name TEXT,
            address TEXT,
            price_info TEXT,
            url TEXT,
            raw_data TEXT,
            event_hash TEXT,
            confidence_score REAL DEFAULT 0.0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (url_id) REFERENCES monitored_urls (id)
        )
    ''')
    
    # Add event_hash and confidence_score columns to existing tables if they don't exist
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN event_hash TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN confidence_score REAL DEFAULT 0.0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE scraped_events ADD COLUMN event_hash TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE scraped_events ADD COLUMN confidence_score REAL DEFAULT 0.0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN tags TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Host column removed - no longer needed
    
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN price_info TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add location_name column to existing events table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN location_name TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add address column to existing events table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN address TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add location_name column to existing scraped_events table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE scraped_events ADD COLUMN location_name TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add address column to existing scraped_events table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE scraped_events ADD COLUMN address TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add end_datetime column to existing events table if it doesn't exist
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN end_datetime TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Insert default categories if they don't exist
    default_categories = [
        ('Work', '#3B82F6'),      # Blue
        ('Personal', '#10B981'),  # Green
        ('Health', '#F59E0B'),    # Yellow
        ('Travel', '#8B5CF6'),    # Purple
        ('Social', '#EF4444'),    # Red
        ('Other', '#6B7280')      # Gray
    ]
    
    for name, color in default_categories:
        cursor.execute('INSERT OR IGNORE INTO categories (name, color) VALUES (?, ?)', (name, color))
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_kennedy_center_url(event_data):
    """Ensure Kennedy Center events use the correct calendar URL"""
    if event_data.get('location_name', '').find('Kennedy Center') != -1:
        event_data['url'] = KENNEDY_CENTER_CALENDAR_URL
    return event_data

def parse_price_info(text):
    """
    Parse price information from text.
    Returns a string like "Free", "$25", or "Free; dog show $25"
    """
    if not text:
        return "Free"
    
    text_lower = text.lower()
    
    # Check for explicit "free" mentions
    if 'free' in text_lower and '$' not in text:
        return "Free"
    
    # Look for dollar amounts
    dollar_patterns = [
        r'\$(\d+(?:\.\d{2})?)',  # $25, $25.50
        r'(\d+(?:\.\d{2})?)\s*dollars?',  # 25 dollars, 25.50 dollar
        r'(\d+(?:\.\d{2})?)\s*\$',  # 25$
    ]
    
    prices = []
    for pattern in dollar_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            price = f"${match}"
            if price not in prices:
                prices.append(price)
    
    # Check for "free" in context
    has_free = 'free' in text_lower
    
    if prices and has_free:
        # Mixed pricing like "Free; dog show $25"
        return f"Free; {', '.join(prices)}"
    elif prices:
        # Just prices
        return ', '.join(prices)
    elif has_free:
        return "Free"
    else:
        return "Free"  # Default to free if no pricing info found

def extract_multiple_events(text):
    """
    Enhanced event extraction using multiple NLP techniques.
    Returns a list of event text blocks.
    """
    events = []
    
    # Clean up the text first
    text = re.sub(r'Return to menu', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n\s*\n', '\n', text)  # Remove extra blank lines
    
    # Method 1: Look for explicit date headers (most reliable)
    date_patterns = [
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}',
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\d{1,2}',
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',
    ]
    
    date_matches = []
    for pattern in date_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            date_matches.append((match.start(), match.group()))
    
    if date_matches:
        # Split by date markers
        date_matches.sort(key=lambda x: x[0])
        for i, (pos, date_text) in enumerate(date_matches):
            start_pos = 0 if i == 0 else date_matches[i-1][0]
            end_pos = len(text) if i == len(date_matches) - 1 else pos
            
            event_text = text[start_pos:end_pos].strip()
            if event_text and len(event_text) > 100:
                cleaned = clean_event_text(event_text)
                if cleaned:
                    events.append(cleaned)
        return events
    
    # Method 2: Enhanced event trigger detection
    event_triggers = [
        # Event types
        r'\b(concert|show|festival|exhibition|workshop|class|meeting|conference|seminar|lecture|talk|presentation|demo|demo|tasting|tour|walk|run|race|game|match|performance|play|musical|dance|party|gala|fundraiser|auction|sale|market|fair|carnival|parade|celebration|ceremony|opening|launch|premiere|screening|film|movie|theater|theatre)\b',
        # Time-based patterns
        r'\b(at|from|starting|beginning|commencing)\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?|AM|PM)\b',
        # Location patterns
        r'\b(at|in|@)\s+[A-Z][A-Za-z\s&\',\-\.]+(?:Center|Theater|Theatre|Museum|Library|Park|Hall|Arena|Stadium|Club|Bar|Restaurant|Cafe|Gallery|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue)\b',
        # Price patterns
        r'\$\d+(?:\.\d{2})?|\b(?:free|Free|FREE)\b',
    ]
    
    # Find potential event boundaries using multiple techniques
    potential_events = []
    
    # Technique 1: Look for title patterns first (more reliable)
    lines = text.split('\n')
    title_events = []
    current_event = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line looks like an event title
        is_title = (len(line) > 10 and len(line) < 100 and 
                   line[0].isupper() and 
                   not line.endswith('.') and 
                   not line.endswith('?') and
                   not line.endswith('!') and
                   ('at ' in line.lower() or 'in ' in line.lower() or 
                    any(word in line.lower() for word in ['festival', 'concert', 'show', 'event', 'exhibition', 'workshop', 'class', 'meeting', 'tasting', 'tour', 'performance', 'party', 'gala', 'sale', 'market', 'fair', 'celebration', 'opening', 'launch', 'screening', 'theater', 'theatre'])))
        
        if is_title and current_event:
            event_text = '\n'.join(current_event).strip()
            if len(event_text) > 100:
                title_events.append(event_text)
            current_event = [line]
        else:
            current_event.append(line)
    
    # Add the last event
    if current_event:
        event_text = '\n'.join(current_event).strip()
        if len(event_text) > 100:
            title_events.append(event_text)
    
    # Use title-based events if we found any
    if title_events:
        potential_events = title_events
    else:
        # Fallback: Split by event trigger sentences (but be more conservative)
        sentences = re.split(r'[.!?]+', text)
        current_event = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if this sentence contains event triggers
            has_trigger = any(re.search(trigger, sentence, re.IGNORECASE) for trigger in event_triggers)
            
            if has_trigger and current_event and len(' '.join(current_event)) > 200:
                # Only split if we have substantial content
                event_text = ' '.join(current_event).strip()
                if len(event_text) > 100:
                    potential_events.append(event_text)
                current_event = [sentence]
            else:
                current_event.append(sentence)
        
        # Add the last event
        if current_event:
            event_text = ' '.join(current_event).strip()
            if len(event_text) > 100:
                potential_events.append(event_text)
    
    
    # Clean and validate events
    for event_text in potential_events:
        cleaned = clean_event_text(event_text)
        if cleaned:
            events.append(cleaned)
    
    # Final fallback: split by double newlines
    if not events:
        potential_events = [event.strip() for event in text.split('\n\n') if event.strip() and len(event.strip()) > 100]
        for event_text in potential_events:
            cleaned = clean_event_text(event_text)
            if cleaned:
                events.append(cleaned)
    
    return events

def clean_event_text(text):
    """
    Clean up event text by removing unwanted content and formatting.
    """
    # Remove common unwanted phrases
    unwanted_phrases = [
        r'Return to menu',
        r'^[A-Za-z\s]+,\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}$',  # Date headers
        r'^[A-Za-z\s]+,\s+\d{1,2}$',  # Simple date headers
    ]
    
    for phrase in unwanted_phrases:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove extra whitespace and blank lines
    text = re.sub(r'\n\s*\n', '\n', text)
    text = re.sub(r'^\s+|\s+$', '', text, flags=re.MULTILINE)
    
    # Only return if the text has substantial content
    if len(text.strip()) > 100:
        return text.strip()
    return None

def login_required(f):
    """Decorator to require login for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Public calendar view"""
    return render_template('public.html')

@app.route('/admin')
@login_required
def admin():
    """Admin calendar view"""
    return render_template('admin_new.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Simple password check (in production, use proper hashing)
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        if username == 'admin' and password == admin_password:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin/table')
@login_required
def admin_table():
    """Admin events table dashboard"""
    return render_template('admin_table.html')

@app.route('/admin/stats')
@login_required
def admin_stats():
    """Admin statistics dashboard"""
    return render_template('admin_stats.html')

# API Routes
@app.route('/api/events')
def get_events():
    """Get events for a specific month or date"""
    try:
        # Initialize database if it doesn't exist
        init_db()
        
        month = request.args.get('month')
        year = request.args.get('year')
        date_param = request.args.get('date')
        
        conn = get_db_connection()
        
        if date_param:
            # Get events for specific date with category info
            cursor = conn.execute('''
                SELECT e.*, c.name as category_name, c.color as category_color 
                FROM events e 
                LEFT JOIN categories c ON e.category_id = c.id 
                WHERE DATE(e.start_datetime) = ? 
                ORDER BY e.start_datetime
            ''', (date_param,))
        elif month and year:
            # Get events for specific month with category info
            cursor = conn.execute('''
                SELECT e.*, c.name as category_name, c.color as category_color 
                FROM events e 
                LEFT JOIN categories c ON e.category_id = c.id 
                WHERE strftime("%m", e.start_datetime) = ? AND strftime("%Y", e.start_datetime) = ? 
                ORDER BY e.start_datetime
            ''', (month.zfill(2), year))
        else:
            # Get all events with category info
            cursor = conn.execute('''
                SELECT e.*, c.name as category_name, c.color as category_color 
                FROM events e 
                LEFT JOIN categories c ON e.category_id = c.id 
                ORDER BY e.start_datetime
            ''')
        
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(events)
        
    except Exception as e:
        app.logger.error(f"Error in get_events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
@login_required
def create_event():
    """Create a new event"""
    data = request.get_json()
    
    # Handle tags - convert list to JSON string if needed
    tags = data.get('tags', '')
    if isinstance(tags, list):
        tags = json.dumps(tags)
    
    conn = get_db_connection()
    cursor = conn.execute(
        'INSERT INTO events (title, start_datetime, end_datetime, description, location, location_name, address, category_id, tags, price_info, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (data['title'], data['start_datetime'], data.get('end_datetime', ''), data.get('description', ''), data.get('location', ''), data.get('location_name', ''), data.get('address', ''), data.get('category_id'), tags, data.get('price_info', ''), data.get('url', ''), datetime.now().isoformat())
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    
    return jsonify({'id': event_id, 'message': 'Event created successfully'}), 201

@app.route('/api/events/<int:event_id>', methods=['PUT'])
@login_required
def update_event(event_id):
    """Update an existing event"""
    data = request.get_json()
    
    # Handle tags - convert list to JSON string if needed
    tags = data.get('tags', '')
    if isinstance(tags, list):
        tags = json.dumps(tags)
    
    conn = get_db_connection()
    cursor = conn.execute(
        'UPDATE events SET title = ?, start_datetime = ?, end_datetime = ?, description = ?, location = ?, location_name = ?, address = ?, category_id = ?, tags = ?, price_info = ?, url = ? WHERE id = ?',
        (data['title'], data['start_datetime'], data.get('end_datetime', ''), data.get('description', ''), data.get('location', ''), data.get('location_name', ''), data.get('address', ''), data.get('category_id'), tags, data.get('price_info', ''), data.get('url', ''), event_id)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Event updated successfully'})

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@login_required
def delete_event(event_id):
    """Delete an event"""
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Event deleted successfully'})

@app.route('/api/admin/events/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_events():
    """Delete multiple events"""
    try:
        data = request.get_json()
        event_ids = data.get('event_ids', [])
        
        if not event_ids:
            return jsonify({'error': 'No event IDs provided'}), 400
        
        conn = get_db_connection()
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?'] * len(event_ids))
        cursor = conn.execute(f'DELETE FROM events WHERE id IN ({placeholders})', event_ids)
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Successfully deleted {deleted_count} events',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        app.logger.error(f"Error in bulk_delete_events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """Get all categories"""
    conn = get_db_connection()
    cursor = conn.execute('SELECT * FROM categories ORDER BY name')
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(categories)

@app.route('/api/events/search')
def search_events():
    """Search events using natural language query"""
    query = request.args.get('q', '')
    
    if not query.strip():
        return jsonify([])
    
    try:
        # Parse the search query
        search_parser = SearchParser()
        filters = search_parser.parse_search_query(query)
        
        # Build SQL query based on filters
        conn = get_db_connection()
        
        # Base query
        sql = '''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            WHERE 1=1
        '''
        params = []
        
        # Apply filters
        if 'keywords' in filters:
            keyword_conditions = []
            for keyword in filters['keywords']:
                keyword_conditions.append('(e.title LIKE ? OR e.description LIKE ? OR e.location LIKE ?)')
                params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
            if keyword_conditions:
                sql += ' AND (' + ' OR '.join(keyword_conditions) + ')'
        
        if 'tags' in filters:
            tag_conditions = []
            for tag in filters['tags']:
                tag_conditions.append('e.tags LIKE ?')
                params.append(f'%{tag}%')
            if tag_conditions:
                sql += ' AND (' + ' OR '.join(tag_conditions) + ')'
        
        if 'date_range' in filters:
            date_range = filters['date_range']
            if 'start' in date_range:
                sql += ' AND DATE(e.start_datetime) >= ?'
                params.append(date_range['start'])
            if 'end' in date_range:
                sql += ' AND DATE(e.start_datetime) <= ?'
                params.append(date_range['end'])
        
        if 'time_range' in filters:
            time_range = filters['time_range']
            if 'start' in time_range:
                sql += ' AND TIME(e.start_datetime) >= ?'
                params.append(time_range['start'])
            if 'end' in time_range:
                sql += ' AND TIME(e.start_datetime) <= ?'
                params.append(time_range['end'])
        
        if 'location' in filters:
            sql += ' AND e.location LIKE ?'
            params.append(f'%{filters["location"]}%')
        
        if 'category' in filters:
            sql += ' AND c.name = ?'
            params.append(filters['category'])
        
        # Order by date
        sql += ' ORDER BY e.start_datetime'
        
        cursor = conn.execute(sql, params)
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(events)
        
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.route('/api/ai/parse-event', methods=['POST'])
@login_required
def parse_event():
    """Parse natural language event description"""
    data = request.get_json()
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        parser = EventParser()
        parsed_event = parser.parse_natural_language(text)
        
        # Convert tags list to JSON string for database storage
        if isinstance(parsed_event.get('tags'), list):
            parsed_event['tags'] = json.dumps(parsed_event['tags'])
        
        # Extract price information from the original text
        if 'description' in parsed_event:
            price_info = parse_price_info(parsed_event['description'])
            parsed_event['price_info'] = price_info
        else:
            parsed_event['price_info'] = parse_price_info(text)
        
        return jsonify(parsed_event)
    except Exception as e:
        return jsonify({'error': f'Parsing failed: {str(e)}'}), 500

@app.route('/api/ai/extract-events', methods=['POST'])
@login_required
def extract_events():
    """Extract multiple events from bulk text using multiple methods"""
    data = request.get_json()
    text = data.get('text', '')
    method = data.get('method', 'enhanced')  # enhanced, advanced, llm
    
    if not text:
        return jsonify({'error': 'No text provided'}), 400
    
    try:
        parsed_events = []
        
        if method == 'llm' and os.getenv('OPENAI_API_KEY'):
            # Use LLM-based extraction (most powerful)
            parsed_events = extract_events_llm(text)
        elif method == 'advanced':
            # Use advanced NLP (spaCy/NLTK)
            try:
                from advanced_parser import extract_events_advanced
                advanced_events = extract_events_advanced(text)
                parsed_events = [convert_advanced_to_standard(event) for event in advanced_events]
            except ImportError:
                # Fallback to enhanced method
                parsed_events = extract_events_enhanced(text)
        else:
            # Use enhanced rule-based extraction (default)
            parsed_events = extract_events_enhanced(text)
        
        return jsonify({
            'events': parsed_events,
            'count': len(parsed_events),
            'method': method
        })
    except Exception as e:
        return jsonify({'error': f'Extraction failed: {str(e)}'}), 500

def extract_events_enhanced(text):
    """Enhanced rule-based event extraction"""
    # Split text into potential events
    events = extract_multiple_events(text)
    
    # Parse each event
    parsed_events = []
    parser = EventParser()
    
    for event_text in events:
        if event_text.strip():
            parsed_event = parser.parse_natural_language(event_text)
            
            # Extract price information
            if 'description' in parsed_event:
                price_info = parse_price_info(parsed_event['description'])
                parsed_event['price_info'] = price_info
            else:
                parsed_event['price_info'] = parse_price_info(event_text)
            
            # Only include events that have at least a title
            if parsed_event.get('title'):
                parsed_events.append(parsed_event)
    
    return parsed_events

def extract_events_llm(text):
    """Extract events using OpenAI LLM"""
    try:
        import openai
        
        prompt = f"""You are an expert event extraction system. Extract ALL events from the following text and return them as a JSON array.

For each event, provide:
- title: concise name of the event
- date: normalized date (YYYY-MM-DD format if possible, otherwise approximate)
- time: start time in HH:MM format if available
- location: venue or address if mentioned
- description: detailed event description
- price_info: cost information (e.g., "Free", "$25", "Free; $25")

Return ONLY a valid JSON array, no other text.

Text to analyze:
{text}"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a precise event extraction system. Always return valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse the JSON response
        import json
        events = json.loads(result)
        
        # Ensure all events have required fields
        for event in events:
            if 'price_info' not in event:
                event['price_info'] = 'Free'
        
        return events
        
    except Exception as e:
        print(f"LLM extraction failed: {e}")
        # Fallback to enhanced method
        return extract_events_enhanced(text)

def convert_advanced_to_standard(advanced_event):
    """Convert advanced parser event format to standard format"""
    return {
        'title': advanced_event.get('title', ''),
        'date': advanced_event.get('date', ''),
        'time': advanced_event.get('time', ''),
        'location': advanced_event.get('location', ''),
        'description': advanced_event.get('description', ''),
        'price_info': advanced_event.get('price_info', 'Free')
    }

@app.route('/api/ai/suggest-recurrence', methods=['POST'])
@login_required
def suggest_recurrence_endpoint():
    """Suggest recurrence patterns for events"""
    data = request.get_json()
    event_data = data.get('event')
    
    if not event_data:
        return jsonify({'suggestion': None})
    
    try:
        # Get recent similar events
        conn = get_db_connection()
        cursor = conn.execute('''
            SELECT * FROM events 
            WHERE title LIKE ? 
            ORDER BY start_datetime DESC 
            LIMIT 10
        ''', (f"%{event_data.get('title', '')}%",))
        
        recent_events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        suggestion = suggest_recurrence(recent_events)
        return jsonify({'suggestion': suggestion})
    except Exception as e:
        return jsonify({'error': f'Suggestion failed: {str(e)}'}), 500

@app.route('/api/ai/analyze-importance', methods=['POST'])
@login_required
def analyze_importance():
    """Analyze event importance for highlighting"""
    data = request.get_json()
    event_data = data.get('event')
    
    if not event_data:
        return jsonify({'importance': 'normal', 'reason': ''})
    
    try:
        analysis = analyze_event_importance(event_data)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/api/admin/events-table')
@login_required
def get_events_table():
    """Get all events in table format for admin dashboard"""
    try:
        conn = get_db_connection()
        
        # Get all events with category info
        cursor = conn.execute('''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            ORDER BY e.start_datetime DESC
        ''')
        
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify({
            'events': events,
            'total': len(events)
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_events_table: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/stats')
@login_required
def get_admin_stats():
    """Get admin statistics"""
    try:
        conn = get_db_connection()
        
        # Total events
        cursor = conn.execute('SELECT COUNT(*) as total FROM events')
        total_events = cursor.fetchone()['total']
        
        # Events by category
        cursor = conn.execute('''
            SELECT c.name, c.color, COUNT(e.id) as count 
            FROM categories c 
            LEFT JOIN events e ON c.id = e.category_id 
            GROUP BY c.id, c.name, c.color 
            ORDER BY count DESC
        ''')
        events_by_category = [dict(row) for row in cursor.fetchall()]
        
        # Most frequent day/time
        cursor = conn.execute('''
            SELECT 
                strftime('%w', start_datetime) as day_of_week,
                strftime('%H', start_datetime) as hour,
                COUNT(*) as count
            FROM events 
            GROUP BY day_of_week, hour 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        frequent_times = [dict(row) for row in cursor.fetchall()]
        
        # Recent events
        cursor = conn.execute('''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            ORDER BY e.start_datetime DESC 
            LIMIT 10
        ''')
        recent_events = [dict(row) for row in cursor.fetchall()]
        
        # Parse tags for analysis
        tag_counts = {}
        for event in recent_events:
            if event.get('tags'):
                try:
                    tags = json.loads(event['tags']) if isinstance(event['tags'], str) else event['tags']
                    for tag in tags:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
                except:
                    pass
        
        conn.close()
        
        return jsonify({
            'total_events': total_events,
            'events_by_category': events_by_category,
            'frequent_times': frequent_times,
            'recent_events': recent_events,
            'tag_counts': tag_counts
        })
    except Exception as e:
        return jsonify({'error': f'Stats failed: {str(e)}'}), 500

@app.route('/api/subscriptions/events')
def get_subscribed_events():
    """Get events based on subscription preferences"""
    # Get subscription data from request headers or query params
    subscriptions_json = request.headers.get('X-Subscriptions', '{}')
    try:
        subscriptions = json.loads(subscriptions_json)
    except:
        subscriptions = {}
    
    if not subscriptions:
        return jsonify([])
    
    conn = get_db_connection()
    
    # Build query based on subscriptions
    conditions = []
    params = []
    
    # Event subscriptions
    if 'event' in subscriptions and subscriptions['event']:
        event_ids = [str(eid) for eid in subscriptions['event']]
        conditions.append(f"e.id IN ({','.join(['?'] * len(event_ids))})")
        params.extend(event_ids)
    
    # Host subscriptions removed - no longer supported
    
    # Venue subscriptions
    if 'venue' in subscriptions and subscriptions['venue']:
        venue_conditions = []
        for venue in subscriptions['venue']:
            venue_conditions.append("e.location LIKE ?")
            params.append(f'%{venue}%')
        if venue_conditions:
            conditions.append(f"({' OR '.join(venue_conditions)})")
    
    # Tag subscriptions
    if 'tag' in subscriptions and subscriptions['tag']:
        tag_conditions = []
        for tag in subscriptions['tag']:
            tag_conditions.append("e.tags LIKE ?")
            params.append(f'%{tag}%')
        if tag_conditions:
            conditions.append(f"({' OR '.join(tag_conditions)})")
    
    if not conditions:
        conn.close()
        return jsonify([])
    
    # Build final query
    sql = f'''
        SELECT e.*, c.name as category_name, c.color as category_color 
        FROM events e 
        LEFT JOIN categories c ON e.category_id = c.id 
        WHERE {' OR '.join(conditions)}
        ORDER BY e.start_datetime
    '''
    
    cursor = conn.execute(sql, params)
    events = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(events)

@app.route('/api/subscriptions/suggestions')
def get_subscription_suggestions():
    """Get subscription suggestions based on existing events"""
    conn = get_db_connection()
    
    # Host field removed - no longer supported
    
    # Get unique venues
    cursor = conn.execute('SELECT DISTINCT location FROM events WHERE location IS NOT NULL AND location != ""')
    venues = [row['location'] for row in cursor.fetchall()]
    
    # Get unique tags
    cursor = conn.execute('SELECT DISTINCT tags FROM events WHERE tags IS NOT NULL AND tags != ""')
    all_tags = set()
    for row in cursor.fetchall():
        try:
            tags = json.loads(row['tags'])
            if isinstance(tags, list):
                all_tags.update(tags)
        except:
            pass
    
    conn.close()
    
    return jsonify({
        'venues': venues,
        'tags': list(all_tags)
    })

# Sync API Endpoints
@app.route('/api/sync/batch', methods=['POST'])
def batch_sync():
    """Handle batch synchronization from admin dashboard"""
    try:
        data = request.get_json()
        sync_operations = data.get('operations', [])
        sync_session_id = data.get('sync_session_id', f"sync_{datetime.now().timestamp()}")
        
        if not sync_operations:
            return jsonify({'error': 'No operations provided'}), 400
        
        # Process batch sync
        results = sync_service.batch_sync_from_admin(sync_operations, sync_session_id)
        
        return jsonify({
            'success': True,
            'sync_session_id': sync_session_id,
            'results': results
        })
        
    except Exception as e:
        app.logger.error(f"Batch sync error: {str(e)}")
        return jsonify({'error': f'Sync failed: {str(e)}'}), 500

@app.route('/api/sync/history')
def get_sync_history():
    """Get sync history"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = sync_service.get_sync_history(limit)
        return jsonify(history)
    except Exception as e:
        app.logger.error(f"Sync history error: {str(e)}")
        return jsonify({'error': f'Failed to get sync history: {str(e)}'}), 500

@app.route('/api/sync/statistics')
def get_sync_statistics():
    """Get sync statistics"""
    try:
        stats = sync_service.get_sync_statistics()
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Sync statistics error: {str(e)}")
        return jsonify({'error': f'Failed to get sync statistics: {str(e)}'}), 500

@app.route('/api/sync/status')
def get_sync_status():
    """Get current sync status"""
    try:
        # Get recent sync activity
        recent_history = sync_service.get_sync_history(10)
        stats = sync_service.get_sync_statistics()
        
        # Check for recent failures
        recent_failures = [h for h in recent_history if not h['success']]
        
        return jsonify({
            'status': 'healthy' if len(recent_failures) == 0 else 'issues',
            'recent_activity': recent_history,
            'statistics': stats,
            'recent_failures': recent_failures
        })
    except Exception as e:
        app.logger.error(f"Sync status error: {str(e)}")
        return jsonify({'error': f'Failed to get sync status: {str(e)}'}), 500

# Scraper API Routes
@app.route('/api/scraper/urls', methods=['GET'])
@login_required
def get_monitored_urls():
    """Get all monitored URLs"""
    try:
        conn = get_db_connection()
        urls = conn.execute('''
            SELECT id, url, name, enabled, scrape_frequency, last_scraped, created_at
            FROM monitored_urls 
            ORDER BY created_at DESC
        ''').fetchall()
        
        return jsonify([dict(url) for url in urls])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/urls', methods=['POST'])
@login_required
def add_monitored_url():
    """Add a new URL to monitor"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        name = data.get('name', '').strip()
        scrape_frequency = data.get('scrape_frequency', 'daily')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO monitored_urls (url, name, scrape_frequency)
            VALUES (?, ?, ?)
        ''', (url, name or url, scrape_frequency))
        conn.commit()
        
        return jsonify({'message': 'URL added successfully'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'URL already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/urls/<int:url_id>', methods=['PUT'])
@login_required
def update_monitored_url(url_id):
    """Update a monitored URL"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        enabled = data.get('enabled', True)
        scrape_frequency = data.get('scrape_frequency', 'daily')
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE monitored_urls 
            SET name = ?, enabled = ?, scrape_frequency = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, enabled, scrape_frequency, url_id))
        conn.commit()
        
        return jsonify({'message': 'URL updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/urls/<int:url_id>', methods=['DELETE'])
@login_required
def delete_monitored_url(url_id):
    """Delete a monitored URL"""
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM monitored_urls WHERE id = ?', (url_id,))
        conn.commit()
        
        return jsonify({'message': 'URL deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/logs', methods=['GET'])
@login_required
def get_scraper_logs():
    """Get scraper activity logs"""
    try:
        limit = request.args.get('limit', 50, type=int)
        conn = get_db_connection()
        logs = conn.execute('''
            SELECT sl.*, mu.url, mu.name
            FROM scraper_logs sl
            LEFT JOIN monitored_urls mu ON sl.url_id = mu.id
            ORDER BY sl.created_at DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        
        return jsonify([dict(log) for log in logs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/events', methods=['GET'])
@login_required
def get_scraped_events():
    """Get events pending review"""
    try:
        status = request.args.get('status', 'pending')
        conn = get_db_connection()
        events = conn.execute('''
            SELECT se.*, mu.url as source_url, mu.name as source_name
            FROM scraped_events se
            LEFT JOIN monitored_urls mu ON se.url_id = mu.id
            WHERE se.status = ?
            ORDER BY se.created_at DESC
        ''', (status,)).fetchall()
        
        return jsonify([dict(event) for event in events])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/events/<int:event_id>/approve', methods=['POST'])
@login_required
def approve_scraped_event(event_id):
    """Approve a scraped event and add it to the main events table"""
    try:
        conn = get_db_connection()
        
        # Get the scraped event
        scraped_event = conn.execute('''
            SELECT * FROM scraped_events WHERE id = ?
        ''', (event_id,)).fetchone()
        
        if not scraped_event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Add to main events table with tracking data
        cursor = conn.execute('''
            INSERT INTO events (title, start_datetime, description, location, location_name, address, price_info, url, event_hash, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            scraped_event['title'],
            scraped_event['start_datetime'],
            scraped_event['description'],
            scraped_event['location'],
            scraped_event.get('location_name', ''),
            scraped_event.get('address', ''),
            scraped_event['price_info'],
            scraped_event['url'],
            scraped_event.get('event_hash', ''),
            scraped_event.get('confidence_score', 0.0)
        ))
        
        new_event_id = cursor.lastrowid
        
        # Update scraped event status
        conn.execute('''
            UPDATE scraped_events SET status = 'approved' WHERE id = ?
        ''', (event_id,))
        
        conn.commit()
        
        # Log the approval
        conn.execute('''
            INSERT INTO scraper_logs (url_id, status, message, events_found, events_added)
            VALUES (?, 'success', 'Event approved and added to calendar', 0, 1)
        ''', (scraped_event['url_id'],))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Event approved and added successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/events/<int:event_id>/reject', methods=['POST'])
@login_required
def reject_scraped_event(event_id):
    """Reject a scraped event"""
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE scraped_events SET status = 'rejected' WHERE id = ?
        ''', (event_id,))
        conn.commit()
        
        return jsonify({'message': 'Event rejected'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/run', methods=['POST'])
@login_required
def run_scraper():
    """Manually trigger scraper for all enabled URLs"""
    try:
        from scraper_service import ScraperService
        scraper = ScraperService()
        result = scraper.run_scraping_cycle()
        
        return jsonify({
            'message': 'Scraping cycle completed',
            'results': result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraper/test-thingstodo', methods=['POST'])
@login_required
def test_thingstodo_scraper():
    """Test the ThingsToDo scraper with a specific URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        from scraper_service import ScraperService
        scraper = ScraperService()
        
        if not scraper.is_thingstodo_url(url):
            return jsonify({'error': 'URL must be from thingstododc.com'}), 400
        
        events = scraper.scrape_thingstodo_event(url)
        
        return jsonify({
            'message': 'Scraping completed',
            'url': url,
            'events_found': len(events),
            'events': events
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/import/washington-post', methods=['POST'])
@login_required
def import_washington_post_events():
    """Import events from Washington Post events file"""
    try:
        from washington_post_parser import WashingtonPostParser
        
        # Get the file content from the request
        data = request.get_json()
        file_content = data.get('content', '').strip()
        
        if not file_content:
            return jsonify({'error': 'File content is required'}), 400
        
        # Parse the events
        parser = WashingtonPostParser()
        events = parser.parse_content(file_content)
        
        if not events:
            return jsonify({'error': 'No valid events found in the file'}), 400
        
        # Convert to dict format for database insertion
        events_data = parser.to_dict_list()
        
        # Insert events into database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        imported_count = 0
        skipped_count = 0
        
        for event_data in events_data:
            try:
                # Check if event already exists (by title and date)
                cursor.execute('''
                    SELECT id FROM events 
                    WHERE title = ? AND start_datetime = ?
                ''', (event_data['title'], event_data['start_datetime']))
                
                if cursor.fetchone():
                    skipped_count += 1
                    continue
                
                # Insert new event
                cursor.execute('''
                    INSERT INTO events (
                        title, start_datetime, end_datetime, description,
                        location_name, address, price_info, url, tags, category_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_data['title'],
                    event_data['start_datetime'],
                    event_data['end_datetime'],
                    event_data['description'],
                    event_data['location_name'],
                    event_data['address'],
                    event_data['price_info'],
                    event_data['url'],
                    event_data['tags'],
                    1,  # Default to Literature category
                    datetime.now().isoformat()
                ))
                
                imported_count += 1
                
            except Exception as e:
                print(f"Error importing event '{event_data.get('title', 'Unknown')}': {e}")
                skipped_count += 1
                continue
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Import completed',
            'imported': imported_count,
            'skipped': skipped_count,
            'total_parsed': len(events)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# RSS Feed Management Routes
@app.route('/admin/rss-feeds')
@require_auth
def rss_feeds_dashboard():
    """RSS Feeds management dashboard"""
    return render_template('rss_feeds.html')

@app.route('/api/rss-feeds', methods=['GET'])
@require_auth
def get_rss_feeds():
    """Get all RSS feeds"""
    try:
        feeds = rss_manager.get_all_feeds()
        return jsonify(feeds)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds', methods=['POST'])
@require_auth
def add_rss_feed():
    """Add a new RSS feed"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Feed name is required'}), 400
        if not data.get('url'):
            return jsonify({'error': 'RSS URL is required'}), 400
            
        success, message = rss_manager.add_feed(
            name=data['name'],
            url=data['url'],
            description=data.get('description', ''),
            category=data.get('category', 'General'),
            update_interval=data.get('update_interval', 30),
            enabled=data.get('enabled', True)
        )
        
        if not success:
            return jsonify({'error': message}), 400
        return jsonify({'message': message})
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/rss-feeds/<int:feed_id>', methods=['PUT'])
@require_auth
def update_rss_feed(feed_id):
    """Update an RSS feed"""
    try:
        data = request.get_json()
        rss_manager.update_feed(feed_id, data)
        return jsonify({'message': 'Feed updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/<int:feed_id>', methods=['DELETE'])
@require_auth
def delete_rss_feed(feed_id):
    """Delete an RSS feed"""
    try:
        rss_manager.delete_feed(feed_id)
        return jsonify({'message': 'Feed deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/<int:feed_id>/refresh', methods=['POST'])
@require_auth
def refresh_rss_feed(feed_id):
    """Manually refresh a specific RSS feed"""
    try:
        result = rss_manager.refresh_feed(feed_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/refresh-all', methods=['POST'])
@require_auth
def refresh_all_rss_feeds():
    """Manually refresh all RSS feeds"""
    try:
        result = rss_manager.refresh_all_feeds()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/logs', methods=['GET'])
@require_auth
def get_rss_logs():
    """Get RSS feed logs"""
    try:
        logs = rss_manager.get_logs(limit=request.args.get('limit', 100))
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/categories', methods=['GET'])
@require_auth
def get_rss_categories():
    """Get RSS feed categories"""
    try:
        categories = rss_manager.get_categories()
        return jsonify(categories)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>/override', methods=['POST'])
@require_auth
def override_event_source(event_id):
    """Override event source (mark as manually added)"""
    try:
        data = request.get_json()
        rss_manager.override_event_source(event_id, data.get('reason', 'Manual override'))
        return jsonify({'message': 'Event source overridden successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/test', methods=['POST'])
@require_auth
def test_rss_feed():
    """Test an RSS feed URL"""
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'success': False, 'message': 'URL is required'}), 400
        
        # Test the feed URL
        result = rss_manager.test_feed_url(url)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/rss-feeds/analytics', methods=['GET'])
def get_rss_analytics():
    """Get RSS feeds analytics"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Events today
        cursor.execute('''
            SELECT COUNT(*) FROM events 
            WHERE DATE(created_at) = DATE('now')
        ''')
        events_today = cursor.fetchone()[0]
        
        # Events this week
        cursor.execute('''
            SELECT COUNT(*) FROM events 
            WHERE DATE(created_at) >= DATE('now', '-7 days')
        ''')
        events_this_week = cursor.fetchone()[0]
        
        # Total events
        cursor.execute('SELECT COUNT(*) FROM events')
        total_events = cursor.fetchone()[0]
        
        # Feed health calculation
        cursor.execute('''
            SELECT 
                COUNT(*) as total_feeds,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_feeds,
                SUM(CASE WHEN consecutive_failures > 0 THEN 1 ELSE 0 END) as error_feeds
            FROM rss_feeds
        ''')
        feed_stats = cursor.fetchone()
        total_feeds, active_feeds, error_feeds = feed_stats
        
        health_score = 0
        if active_feeds > 0:
            health_score = max(0, 100 - (error_feeds / active_feeds * 100))
        
        # Average response time (estimate from logs)
        cursor.execute('''
            SELECT AVG(response_time_ms) FROM rss_feed_logs 
            WHERE response_time_ms IS NOT NULL 
            AND check_time >= DATE('now', '-1 day')
        ''')
        avg_response_time = cursor.fetchone()[0] or 500
        
        # Recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM rss_feed_logs 
            WHERE DATE(check_time) = DATE('now')
        ''')
        feeds_checked = cursor.fetchone()[0]
        
        # Last update
        cursor.execute('''
            SELECT MAX(check_time) FROM rss_feed_logs
        ''')
        last_update = cursor.fetchone()[0]
        
        conn.close()
        
        analytics = {
            'eventsToday': events_today,
            'eventsThisWeek': events_this_week,
            'healthScore': round(health_score, 1),
            'avgResponseTime': round(avg_response_time, 0),
            'totalEvents': total_events,
            'feedsChecked': feeds_checked,
            'errorsResolved': 0,  # Could be calculated from logs
            'avgProcessingTime': round(avg_response_time * 0.4, 0),  # Estimate
            'lastUpdate': last_update
        }
        
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/<int:feed_id>/events', methods=['GET'])
@require_auth
def get_feed_events(feed_id):
    """Get events for a specific RSS feed"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get feed name
        cursor.execute('SELECT name FROM rss_feeds WHERE id = ?', (feed_id,))
        feed_result = cursor.fetchone()
        if not feed_result:
            return jsonify({'success': False, 'message': 'Feed not found'}), 404
        
        feed_name = feed_result[0]
        
        # Get events for this feed
        limit = request.args.get('limit', 50)
        cursor.execute('''
            SELECT e.id, e.title, e.description, e.start_datetime, e.end_datetime,
                   e.location_name, e.address, e.price_info, e.url, e.tags, e.category_id, e.created_at
            FROM events e
            INNER JOIN event_sources es ON e.id = es.event_id
            WHERE es.feed_id = ?
            ORDER BY e.start_datetime DESC
            LIMIT ?
        ''', (feed_id, int(limit)))
        
        events = []
        for row in cursor.fetchall():
            event = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'start_datetime': row[3],
                'end_datetime': row[4],
                'location_name': row[5],
                'address': row[6],
                'price_info': row[7],
                'url': row[8],
                'tags': row[9],
                'category_id': row[10],
                'created_at': row[11]
            }
            events.append(event)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'feed_name': feed_name,
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/rss-feeds/scheduler-status', methods=['GET'])
@require_auth
def get_scheduler_status_api():
    """Get RSS scheduler status"""
    try:
        status = get_scheduler_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Web Scraper Routes
@app.route('/admin/web-scrapers')
@require_auth
def web_scrapers_dashboard():
    """Web scrapers management dashboard"""
    return render_template('web_scrapers.html')

@app.route('/api/web-scrapers', methods=['GET'])
@require_auth
def get_web_scrapers():
    """Get all web scrapers"""
    try:
        scrapers = web_scraper_manager.get_all_scrapers()
        return jsonify(scrapers)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers', methods=['POST'])
@require_auth
def add_web_scraper():
    """Add a new web scraper"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Scraper name is required'}), 400
        if not data.get('url'):
            return jsonify({'error': 'URL is required'}), 400
            
        success, message = web_scraper_manager.add_scraper(
            name=data['name'],
            url=data['url'],
            description=data.get('description', ''),
            category=data.get('category', 'events'),
            selector_config=data.get('selector_config', {}),
            update_interval=data.get('update_interval', 60),
            enabled=data.get('enabled', True)
        )
        
        if not success:
            return jsonify({'error': message}), 400
        return jsonify({'message': message})
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/web-scrapers/<int:scraper_id>', methods=['PUT'])
@require_auth
def update_web_scraper(scraper_id):
    """Update a web scraper"""
    try:
        data = request.get_json()
        success = web_scraper_manager.update_scraper(scraper_id, data)
        if success:
            return jsonify({'message': 'Scraper updated successfully'})
        else:
            return jsonify({'error': 'Failed to update scraper'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/<int:scraper_id>', methods=['DELETE'])
@require_auth
def delete_web_scraper(scraper_id):
    """Delete a web scraper"""
    try:
        success = web_scraper_manager.delete_scraper(scraper_id)
        if success:
            return jsonify({'message': 'Scraper deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete scraper'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/<int:scraper_id>/scrape', methods=['POST'])
@require_auth
def scrape_website(scraper_id):
    """Manually trigger a website scrape"""
    try:
        result = web_scraper_manager.scrape_website(scraper_id)
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/scrape-all', methods=['POST'])
@require_auth
def scrape_all_websites():
    """Manually trigger all active scrapers"""
    try:
        scrapers = web_scraper_manager.get_all_scrapers()
        active_scrapers = [s for s in scrapers if s['is_active']]
        
        results = []
        for scraper in active_scrapers:
            result = web_scraper_manager.scrape_website(scraper['id'])
            results.append({
                'scraper_id': scraper['id'],
                'scraper_name': scraper['name'],
                'result': result
            })
        
        return jsonify({
            'message': f'Scraping completed for {len(active_scrapers)} scrapers',
            'results': results
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/logs', methods=['GET'])
@require_auth
def get_web_scraper_logs():
    """Get web scraper logs"""
    try:
        scraper_id = request.args.get('scraper_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        logs = web_scraper_manager.get_scraper_logs(scraper_id, limit)
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/test', methods=['POST'])
@require_auth
def test_web_scraper():
    """Test a web scraper URL and configuration"""
    try:
        data = request.get_json()
        url = data.get('url')
        selector_config = data.get('selector_config', {})
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        result = web_scraper_manager.test_scraper_url(url, selector_config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/analytics', methods=['GET'])
def get_web_scraper_analytics():
    """Get web scraper analytics"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Total scrapers
        cursor.execute('SELECT COUNT(*) FROM web_scrapers')
        total_scrapers = cursor.fetchone()[0]
        
        # Active scrapers
        cursor.execute('SELECT COUNT(*) FROM web_scrapers WHERE is_active = 1')
        active_scrapers = cursor.fetchone()[0]
        
        # Scrapers with errors
        cursor.execute('SELECT COUNT(*) FROM web_scrapers WHERE consecutive_failures > 0')
        error_scrapers = cursor.fetchone()[0]
        
        # Total events from scrapers
        cursor.execute('SELECT SUM(total_events) FROM web_scrapers')
        total_scraped_events = cursor.fetchone()[0] or 0
        
        # Recent scraping activity
        cursor.execute('''
            SELECT COUNT(*) FROM web_scraper_logs 
            WHERE DATE(run_time) = DATE('now')
        ''')
        scrapes_today = cursor.fetchone()[0]
        
        # Average response time
        cursor.execute('''
            SELECT AVG(response_time_ms) FROM web_scraper_logs 
            WHERE response_time_ms IS NOT NULL 
            AND DATE(run_time) >= DATE('now', '-7 days')
        ''')
        avg_response_time = cursor.fetchone()[0] or 0
        
        conn.close()
        
        analytics = {
            'totalScrapers': total_scrapers,
            'activeScrapers': active_scrapers,
            'errorScrapers': error_scrapers,
            'totalScrapedEvents': total_scraped_events,
            'scrapesToday': scrapes_today,
            'avgResponseTime': round(avg_response_time, 0),
            'healthScore': max(0, 100 - (error_scrapers / max(active_scrapers, 1) * 100))
        }
        
        return jsonify(analytics)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/<int:scraper_id>/events', methods=['GET'])
@require_auth
def get_scraper_events(scraper_id):
    """Get events from a specific web scraper"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get events from this scraper
        cursor.execute('''
            SELECT e.id, e.title, e.description, e.start_datetime, e.end_datetime,
                   e.location_name, e.address, e.price_info, e.url, e.tags,
                   e.created_at, wse.scraped_at
            FROM events e
            JOIN web_scraper_events wse ON e.id = wse.event_id
            WHERE wse.scraper_id = ? AND wse.is_active = 1
            ORDER BY e.created_at DESC
        ''', (scraper_id,))
        
        events = []
        for row in cursor.fetchall():
            # Ensure all required fields exist with default values to prevent Alpine.js errors
            event = {
                'id': row[0] or f"event_{scraper_id}_{len(events)}",  # Fallback ID
                'title': row[1] or 'Untitled Event',
                'description': row[2] or '',
                'start_datetime': row[3] or '',
                'end_datetime': row[4] or '',
                'location_name': row[5] or '',
                'address': row[6] or '',
                'price_info': row[7] or '',
                'url': row[8] or '',
                'tags': row[9] or '',
                'created_at': row[10] or '',
                'scraped_at': row[11] or '',
                'after': '',  # Add missing field with default value
                'formatted_date': format_date_for_display(row[3]) if row[3] else 'Date TBD',
                'formatted_time': format_time_for_display(row[3]) if row[3] else ''
            }
            events.append(event)
        
        conn.close()
        
        # Remove any potential duplicates by ID to prevent Alpine.js duplicate key errors
        unique_events = []
        seen_ids = set()
        for event in events:
            if event['id'] not in seen_ids:
                unique_events.append(event)
                seen_ids.add(event['id'])
        
        return jsonify({
            'events': unique_events,
            'count': len(unique_events),
            'scraper_id': scraper_id
        })
        
    except Exception as e:
        logger.error(f"Error fetching scraper events: {e}")
        return jsonify({'error': str(e), 'events': [], 'count': 0}), 500

def format_date_for_display(datetime_string):
    """Format datetime for frontend display"""
    try:
        if not datetime_string or datetime_string == 'Invalid Date':
            return 'Date TBD'
        
        from datetime import datetime
        dt = datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except:
        return 'Date TBD'

def format_time_for_display(datetime_string):
    """Format time for frontend display"""
    try:
        if not datetime_string or datetime_string == 'Invalid Date':
            return ''
        
        from datetime import datetime
        dt = datetime.fromisoformat(datetime_string.replace('Z', '+00:00'))
        return dt.strftime('%I:%M %p')
    except:
        return ''

@app.route('/api/web-scrapers/scheduler-status', methods=['GET'])
@require_auth
def get_web_scraper_scheduler_status():
    """Get web scraper scheduler status"""
    try:
        status = get_scraper_scheduler_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/fix-invalid-dates', methods=['POST'])
@require_auth
def fix_invalid_dates():
    """Fix invalid dates in the events database"""
    try:
        from admin_date_fixer import fix_invalid_dates, create_validation_rules
        
        # Fix invalid dates
        result = fix_invalid_dates()
        
        # Create validation rules
        validation_result = create_validation_rules()
        
        return jsonify({
            'status': 'success',
            'message': f"Fixed {result['fixed']} events, skipped {result['skipped']}",
            'details': {
                'fixed': result['fixed'],
                'skipped': result['skipped'],
                'total': result['total'],
                'validation_created': validation_result['status'] == 'success'
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/admin/date-status')
@require_auth
def get_date_status():
    """Get current date status statistics"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Get total events
        cursor.execute('SELECT COUNT(*) FROM events')
        total_events = cursor.fetchone()[0]
        
        # Get invalid dates
        cursor.execute('''
            SELECT COUNT(*) FROM events 
            WHERE start_datetime IS NULL OR start_datetime = '' OR start_datetime = 'Invalid Date'
        ''')
        invalid_dates = cursor.fetchone()[0]
        
        # Get valid dates
        cursor.execute('''
            SELECT COUNT(*) FROM events 
            WHERE start_datetime IS NOT NULL AND start_datetime != '' 
            AND start_datetime != 'Invalid Date' AND datetime(start_datetime) IS NOT NULL
        ''')
        valid_dates = cursor.fetchone()[0]
        
        # Get TBD dates (events with reasonable future dates)
        cursor.execute('''
            SELECT COUNT(*) FROM events 
            WHERE start_datetime LIKE '%TBD%' OR start_datetime LIKE '%TBA%'
        ''')
        tbd_dates = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_events': total_events,
            'invalid_dates': invalid_dates,
            'valid_dates': valid_dates,
            'tbd_dates': tbd_dates
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/invalid-dates-list')
@require_auth
def get_invalid_dates_list():
    """Get list of events with invalid dates"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, start_datetime, url
            FROM events
            WHERE start_datetime IS NULL OR start_datetime = '' OR start_datetime = 'Invalid Date'
            ORDER BY id
        ''')
        
        events = []
        for row in cursor.fetchall():
            events.append({
                'id': row[0],
                'title': row[1],
                'start_datetime': row[2],
                'url': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print('Starting RSS feed scheduler...')
    start_rss_scheduler()
    print('RSS scheduler started successfully!')
    
    print('Starting web scraper scheduler...')
    start_web_scraper_scheduler()
    print('Web scraper scheduler started successfully!')
    
    init_db()
    app.run(debug=True, port=5001)
