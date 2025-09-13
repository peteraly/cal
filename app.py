from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, date, timedelta
import sqlite3
import os
from functools import wraps
import hashlib
from dotenv import load_dotenv
from ai_parser import EventParser, suggest_recurrence, analyze_event_importance, SearchParser
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
    
    # Create events table with category reference, tags, host, and pricing
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            start_datetime TEXT NOT NULL,
            description TEXT,
            location TEXT,
            category_id INTEGER,
            tags TEXT,
            host TEXT,
            price_info TEXT,
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN tags TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN host TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute('ALTER TABLE events ADD COLUMN price_info TEXT')
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
        if not session.get('logged_in'):
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
        admin_password = os.environ.get('ADMIN_PASSWORD', 'test')
        if username == 'admin' and password == admin_password:
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error='Invalid credentials')
    
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    session.pop('logged_in', None)
    return redirect(url_for('index'))

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
        'INSERT INTO events (title, start_datetime, description, location, category_id, tags, host, price_info) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (data['title'], data['start_datetime'], data.get('description', ''), data.get('location', ''), data.get('category_id'), tags, data.get('host', ''), data.get('price_info', ''))
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
        'UPDATE events SET title = ?, start_datetime = ?, description = ?, location = ?, category_id = ?, tags = ?, host = ?, price_info = ? WHERE id = ?',
        (data['title'], data['start_datetime'], data.get('description', ''), data.get('location', ''), data.get('category_id'), tags, data.get('host', ''), data.get('price_info', ''), event_id)
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
    
    # Host subscriptions
    if 'host' in subscriptions and subscriptions['host']:
        host_conditions = []
        for host in subscriptions['host']:
            host_conditions.append("e.host LIKE ?")
            params.append(f'%{host}%')
        if host_conditions:
            conditions.append(f"({' OR '.join(host_conditions)})")
    
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
    
    # Get unique hosts
    cursor = conn.execute('SELECT DISTINCT host FROM events WHERE host IS NOT NULL AND host != ""')
    hosts = [row['host'] for row in cursor.fetchall()]
    
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
        'hosts': hosts,
        'venues': venues,
        'tags': list(all_tags)
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5001)
