"""
Simplified Calendar Application
Reduced from 2,160 lines to ~400 lines while maintaining core functionality
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import sqlite3
from dotenv import load_dotenv
from services import EventService
from enhanced_scraper import EnhancedWebScraper
from scraper_scheduler import start_background_scheduler, get_scheduler_status

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize services
event_service = EventService()
enhanced_scraper = EnhancedWebScraper()

# Start background scheduler
scheduler = start_background_scheduler()

def require_auth(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Public calendar view"""
    return render_template('public_simplified.html')

@app.route('/admin')
@require_auth
def admin():
    """Admin calendar view"""
    return render_template('admin_simplified.html')

@app.route('/admin/approval')
@require_auth
def admin_approval():
    """Admin event approval dashboard"""
    return render_template('admin_approval.html')

@app.route('/admin/web-scrapers')
@require_auth
def admin_web_scrapers():
    """Admin web scrapers management"""
    return render_template('web_scrapers.html')

@app.route('/admin/rss-feeds')
@require_auth
def admin_rss_feeds():
    """Admin RSS feeds management"""
    return render_template('rss_feeds.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
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

# API Routes
@app.route('/api/events')
def get_events():
    """Get events with optional filtering"""
    try:
        date = request.args.get('date')
        month = request.args.get('month')
        year = request.args.get('year')
        
        events = event_service.get_events(date=date, month=month, year=year)
        return jsonify(events)
        
    except Exception as e:
        app.logger.error(f"Error in get_events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events', methods=['POST'])
@require_auth
def create_event():
    """Create a new event"""
    try:
        data = request.get_json()
        
        # Handle tags - convert list to JSON string if needed
        tags = data.get('tags', '')
        if isinstance(tags, list):
            import json
            tags = json.dumps(tags)
        
        event_data = {
            'title': data['title'],
            'start_datetime': data['start_datetime'],
            'end_datetime': data.get('end_datetime', ''),
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'location_name': data.get('location_name', ''),
            'address': data.get('address', ''),
            'price_info': data.get('price_info', ''),
            'url': data.get('url', ''),
            'tags': tags,
            'category_id': data.get('category_id'),
            'source': 'manual'
        }
        
        event_id = event_service.create_event(event_data)
        return jsonify({'id': event_id, 'message': 'Event created successfully'}), 201
        
    except Exception as e:
        app.logger.error(f"Error creating event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['PUT'])
@require_auth
def update_event(event_id):
    """Update an existing event"""
    try:
        data = request.get_json()
        
        # Handle tags - convert list to JSON string if needed
        tags = data.get('tags', '')
        if isinstance(tags, list):
            import json
            tags = json.dumps(tags)
        
        event_data = {
            'title': data['title'],
            'start_datetime': data['start_datetime'],
            'end_datetime': data.get('end_datetime', ''),
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'location_name': data.get('location_name', ''),
            'address': data.get('address', ''),
            'price_info': data.get('price_info', ''),
            'url': data.get('url', ''),
            'tags': tags,
            'category_id': data.get('category_id')
        }
        
        success = event_service.update_event(event_id, event_data)
        if success:
            return jsonify({'message': 'Event updated successfully'})
        else:
            return jsonify({'error': 'Event not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Error updating event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/<int:event_id>', methods=['DELETE'])
@require_auth
def delete_event(event_id):
    """Delete an event"""
    try:
        success = event_service.delete_event(event_id)
        if success:
            return jsonify({'message': 'Event deleted successfully'})
        else:
            return jsonify({'error': 'Event not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Error deleting event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/bulk-delete', methods=['POST'])
@require_auth
def bulk_delete_events():
    """Delete multiple events"""
    try:
        data = request.get_json()
        event_ids = data.get('event_ids', [])
        
        if not event_ids:
            return jsonify({'error': 'No event IDs provided'}), 400
        
        deleted_count = event_service.bulk_delete_events(event_ids)
        return jsonify({
            'message': f'Successfully deleted {deleted_count} events',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        app.logger.error(f"Error in bulk_delete_events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/events/search')
def search_events():
    """Search events"""
    try:
        query = request.args.get('q', '')
        
        if not query.strip():
            return jsonify([])
        
        events = event_service.search_events(query)
        return jsonify(events)
        
    except Exception as e:
        app.logger.error(f"Error searching events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """Get all categories"""
    try:
        categories = event_service.get_categories()
        return jsonify(categories)
    except Exception as e:
        app.logger.error(f"Error getting categories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/parse-event', methods=['POST'])
@require_auth
def parse_event():
    """Parse natural language event description"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        parsed_event = event_service.parse_event_text(text)
        return jsonify(parsed_event)
        
    except Exception as e:
        app.logger.error(f"Error parsing event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/extract-events', methods=['POST'])
@require_auth
def extract_events():
    """Extract multiple events from bulk text"""
    try:
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        events = event_service.extract_events_from_text(text)
        return jsonify({
            'events': events,
            'count': len(events)
        })
        
    except Exception as e:
        app.logger.error(f"Error extracting events: {str(e)}")
        return jsonify({'error': str(e)}), 500

# RSS Feed Routes
@app.route('/api/rss-feeds', methods=['GET'])
@require_auth
def get_rss_feeds():
    """Get all RSS feeds"""
    try:
        feeds = event_service.get_rss_feeds()
        return jsonify(feeds)
    except Exception as e:
        app.logger.error(f"Error getting RSS feeds: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds', methods=['POST'])
@require_auth
def add_rss_feed():
    """Add a new RSS feed"""
    try:
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Feed name is required'}), 400
        if not data.get('url'):
            return jsonify({'error': 'RSS URL is required'}), 400
        
        feed_id = event_service.add_rss_feed(
            name=data['name'],
            url=data['url'],
            description=data.get('description', '')
        )
        
        return jsonify({'id': feed_id, 'message': 'RSS feed added successfully'})
        
    except Exception as e:
        app.logger.error(f"Error adding RSS feed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/<int:feed_id>', methods=['DELETE'])
@require_auth
def delete_rss_feed(feed_id):
    """Delete an RSS feed"""
    try:
        success = event_service.delete_rss_feed(feed_id)
        if success:
            return jsonify({'message': 'RSS feed deleted successfully'})
        else:
            return jsonify({'error': 'RSS feed not found'}), 404
            
    except Exception as e:
        app.logger.error(f"Error deleting RSS feed: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/rss-feeds/refresh', methods=['POST'])
@require_auth
def refresh_rss_feeds():
    """Refresh all RSS feeds"""
    try:
        result = event_service.refresh_rss_feeds()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error refreshing RSS feeds: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
@require_auth
def get_stats():
    """Get basic statistics"""
    try:
        stats = event_service.get_stats()
        return jsonify(stats)
    except Exception as e:
        app.logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Event Approval System
@app.route('/api/admin/events/pending')
@require_auth
def get_pending_events():
    """Get all events pending approval"""
    try:
        pending_events = event_service.get_pending_events()
        return jsonify(pending_events)
    except Exception as e:
        app.logger.error(f"Error getting pending events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events/<int:event_id>/approve', methods=['POST'])
@require_auth
def approve_event(event_id):
    """Approve a specific event"""
    try:
        success = event_service.approve_event(event_id, admin_user_id=1)  # TODO: Get actual admin user ID
        if success:
            return jsonify({'message': 'Event approved successfully'})
        else:
            return jsonify({'error': 'Event not found'}), 404
    except Exception as e:
        app.logger.error(f"Error approving event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events/<int:event_id>/reject', methods=['POST'])
@require_auth
def reject_event(event_id):
    """Reject a specific event"""
    try:
        data = request.get_json()
        reason = data.get('reason', 'No reason provided')
        
        success = event_service.reject_event(event_id, reason, admin_user_id=1)  # TODO: Get actual admin user ID
        if success:
            return jsonify({'message': 'Event rejected successfully'})
        else:
            return jsonify({'error': 'Event not found'}), 404
    except Exception as e:
        app.logger.error(f"Error rejecting event: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events/<int:event_id>/update', methods=['PUT'])
@require_auth
def admin_update_event(event_id):
    """Update event details"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        # Update the event in database
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Build update query dynamically based on provided fields
        update_fields = []
        update_values = []
        
        if 'title' in data:
            update_fields.append('title = ?')
            update_values.append(data['title'])
        
        if 'description' in data:
            update_fields.append('description = ?')
            update_values.append(data['description'])
        
        if 'start_datetime' in data:
            update_fields.append('start_datetime = ?')
            update_values.append(data['start_datetime'])
        
        if 'end_datetime' in data:
            update_fields.append('end_datetime = ?')
            update_values.append(data['end_datetime'])
        
        if 'location_name' in data:
            update_fields.append('location_name = ?')
            update_values.append(data['location_name'])
        
        if 'price_info' in data:
            update_fields.append('price_info = ?')
            update_values.append(data['price_info'])
        
        if 'event_type' in data:
            update_fields.append('event_type = ?')
            update_values.append(data['event_type'])
        
        if 'url' in data:
            update_fields.append('url = ?')
            update_values.append(data['url'])
        
        # Add updated timestamp
        from datetime import datetime
        update_fields.append('updated_at = ?')
        update_values.append(datetime.now().isoformat())
        
        # Add event_id for WHERE clause
        update_values.append(event_id)
        
        update_query = f'''
            UPDATE events 
            SET {', '.join(update_fields)}
            WHERE id = ? AND approval_status = 'pending'
        '''
        
        cursor.execute(update_query, update_values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Event not found or not pending'}), 404
        
        conn.commit()
        conn.close()
        
        app.logger.info(f"Event {event_id} updated by admin")
        return jsonify({'success': True, 'message': 'Event updated successfully'})
        
    except Exception as e:
        app.logger.error(f"Error updating event {event_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events/bulk-approve', methods=['POST'])
@require_auth
def bulk_approve_events():
    """Bulk approve multiple events"""
    try:
        data = request.get_json()
        event_ids = data.get('event_ids', [])
        
        if not event_ids:
            return jsonify({'error': 'No event IDs provided'}), 400
        
        approved_count = event_service.bulk_approve_events(event_ids, admin_user_id=1)
        return jsonify({
            'message': f'Successfully approved {approved_count} events',
            'approved_count': approved_count
        })
    except Exception as e:
        app.logger.error(f"Error bulk approving events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events/bulk-reject', methods=['POST'])
@require_auth
def bulk_reject_events():
    """Bulk reject multiple events"""
    try:
        data = request.get_json()
        event_ids = data.get('event_ids', [])
        reason = data.get('reason', 'Bulk rejection')
        
        if not event_ids:
            return jsonify({'error': 'No event IDs provided'}), 400
        
        rejected_count = event_service.bulk_reject_events(event_ids, reason, admin_user_id=1)
        return jsonify({
            'message': f'Successfully rejected {rejected_count} events',
            'rejected_count': rejected_count
        })
    except Exception as e:
        app.logger.error(f"Error bulk rejecting events: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/events/pending-enhanced')
@require_auth
def get_pending_events_enhanced():
    """Enhanced pending events with sorting and filtering for better admin workflow"""
    try:
        # Get query parameters
        sort_by = request.args.get('sort', 'event_date')  # event_date, source, discovery_time, confidence
        order = request.args.get('order', 'asc')  # asc, desc
        source_filter = request.args.get('source', 'all')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Build dynamic query with enhanced data
        query = '''
            SELECT 
                id, title, description, start_datetime, location_name, 
                url, source, created_at, category_id,
                -- Computed fields for better organization
                CASE 
                    WHEN url LIKE '%brookings%' THEN 'Brookings Institution'
                    WHEN url LIKE '%districtfray%' THEN 'DC Fray Sports'
                    WHEN url LIKE '%naturalhistory%' THEN 'Smithsonian Natural History'
                    WHEN url LIKE '%hirshhorn%' THEN 'Smithsonian Hirshhorn'
                    WHEN url LIKE '%americanhistory%' THEN 'Smithsonian American History'
                    WHEN url LIKE '%runpacers%' THEN 'Pacers Running Club'
                    WHEN url LIKE '%cato%' THEN 'Cato Institute'
                    WHEN url LIKE '%eventbrite%' THEN 'Eventbrite'
                    WHEN url LIKE '%meetup%' THEN 'Meetup'
                    ELSE 'Other Source'
                END as source_name,
                
                -- Event freshness (hours since discovered)
                CAST((julianday('now') - julianday(created_at)) * 24 as INTEGER) as hours_since_discovery,
                
                -- Days until event
                CAST(julianday(start_datetime) - julianday('now') as INTEGER) as days_until_event,
                
                -- Confidence score estimation
                CASE 
                    WHEN location_name IS NOT NULL AND location_name != '' AND description IS NOT NULL AND length(description) > 50 THEN 95
                    WHEN location_name IS NOT NULL AND location_name != '' THEN 85
                    WHEN description IS NOT NULL AND length(description) > 50 THEN 80
                    ELSE 75
                END as estimated_confidence
                
            FROM events 
            WHERE approval_status = 'pending'
        '''
        
        # Add filters
        params = []
        if source_filter != 'all':
            query += ' AND url LIKE ?'
            params.append(f'%{source_filter}%')
        
        if date_from:
            query += ' AND start_datetime >= ?'
            params.append(date_from)
        
        if date_to:
            query += ' AND start_datetime <= ?'
            params.append(date_to)
        
        # Add sorting
        sort_columns = {
            'event_date': 'start_datetime',
            'source': 'source_name, start_datetime',
            'discovery_time': 'created_at',
            'confidence': 'estimated_confidence',
            'urgency': 'days_until_event'
        }
        
        sort_column = sort_columns.get(sort_by, 'start_datetime')
        query += f' ORDER BY {sort_column} {order.upper()}'
        
        cursor.execute(query, params)
        
        events = []
        for row in cursor.fetchall():
            hours_since = row[10]
            days_until = row[11]
            
            event = {
                'id': row[0],
                'title': row[1],
                'description': row[2] or '',
                'start_datetime': row[3],
                'location_name': row[4] or '',
                'url': row[5],
                'source': row[6],
                'created_at': row[7],
                'category_id': row[8],
                'source_name': row[9],
                'hours_since_discovery': hours_since,
                'days_until_event': days_until,
                'estimated_confidence': row[12],
                'freshness_badge': get_freshness_badge(hours_since),
                'urgency_badge': get_urgency_badge(days_until)
            }
            events.append(event)
        
        conn.close()
        return jsonify(events)
        
    except Exception as e:
        app.logger.error(f"Error getting enhanced pending events: {str(e)}")
        return jsonify({'error': str(e)}), 500

def get_freshness_badge(hours):
    """Get color-coded freshness badge for admin UI"""
    if hours <= 1:
        return {'text': 'Just found', 'class': 'bg-green-100 text-green-800'}
    elif hours <= 6:
        return {'text': f'{hours}h ago', 'class': 'bg-blue-100 text-blue-800'}
    elif hours <= 24:
        return {'text': f'{hours}h ago', 'class': 'bg-yellow-100 text-yellow-800'}
    else:
        days = hours // 24
        return {'text': f'{days}d ago', 'class': 'bg-gray-100 text-gray-800'}

def get_urgency_badge(days):
    """Get urgency badge for events based on how soon they occur"""
    if days < 0:
        return {'text': 'Past event', 'class': 'bg-red-100 text-red-800'}
    elif days == 0:
        return {'text': 'Today!', 'class': 'bg-red-100 text-red-800'}
    elif days == 1:
        return {'text': 'Tomorrow', 'class': 'bg-orange-100 text-orange-800'}
    elif days <= 7:
        return {'text': f'{days} days', 'class': 'bg-yellow-100 text-yellow-800'}
    elif days <= 30:
        return {'text': f'{days} days', 'class': 'bg-blue-100 text-blue-800'}
    else:
        return {'text': f'{days} days', 'class': 'bg-gray-100 text-gray-800'}

@app.route('/api/admin/events/auto-approve-trusted', methods=['POST'])
@require_auth
def auto_approve_trusted_sources():
    """Auto-approve events from trusted sources with high confidence"""
    try:
        trusted_patterns = ['brookings.edu', 'si.edu', 'naturalhistory.si.edu', 'hirshhorn.si.edu']
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        total_approved = 0
        for pattern in trusted_patterns:
            cursor.execute('''
                UPDATE events 
                SET approval_status = 'approved' 
                WHERE approval_status = 'pending' 
                AND url LIKE ? 
                AND location_name IS NOT NULL 
                AND location_name != ''
                AND start_datetime > datetime('now')
            ''', (f'%{pattern}%',))
            total_approved += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Auto-approved {total_approved} events from trusted sources',
            'approved_count': total_approved
        })
        
    except Exception as e:
        app.logger.error(f"Error auto-approving trusted events: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Web Scraper API Endpoints
@app.route('/api/web-scrapers')
@require_auth
def get_web_scrapers():
    """Get all web scrapers"""
    try:
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM web_scrapers ORDER BY created_at DESC')
        scrapers = []
        for row in cursor.fetchall():
            scraper = {
                'id': row[0],                    # id
                'name': row[1],                  # name
                'url': row[2],                   # url
                'description': row[3],           # description
                'category': row[4],              # category
                'selector_config': json.loads(row[5]) if row[5] and isinstance(row[5], str) else {},  # selector_config
                'update_interval': row[6],       # update_interval
                'is_active': bool(row[7]),       # is_active
                'last_run': row[8],              # last_run
                'next_run': row[9],              # next_run
                'consecutive_failures': row[10], # consecutive_failures
                'total_events': row[11],         # total_events
                'created_at': row[12],           # created_at
                'updated_at': row[13]            # updated_at
            }
            scrapers.append(scraper)
        conn.close()
        return jsonify(scrapers)
    except Exception as e:
        app.logger.error(f"Error getting web scrapers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers', methods=['POST'])
@require_auth
def add_web_scraper():
    """Add a new web scraper"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Check if URL already exists
        cursor.execute('SELECT id FROM web_scrapers WHERE url = ?', (data.get('url'),))
        if cursor.fetchone():
            conn.close()
            return jsonify({'error': 'A scraper with this URL already exists'}), 400
        
        cursor.execute('''
            INSERT INTO web_scrapers (name, url, description, category, update_interval, is_active, selector_config)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('url'),
            data.get('description', ''),
            data.get('category', 'events'),
            data.get('update_interval', 60),
            data.get('enabled', True),
            json.dumps(data.get('selector_config', {}))
        ))
        
        conn.commit()
        scraper_id = cursor.lastrowid
        conn.close()
        
        return jsonify({'message': 'Web scraper added successfully', 'id': scraper_id})
    except Exception as e:
        app.logger.error(f"Error adding web scraper: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/<int:scraper_id>', methods=['DELETE'])
@require_auth
def delete_web_scraper(scraper_id):
    """Delete a web scraper"""
    try:
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM web_scrapers WHERE id = ?', (scraper_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Web scraper deleted successfully'})
    except Exception as e:
        app.logger.error(f"Error deleting web scraper: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/test', methods=['POST'])
@require_auth
def test_web_scraper():
    """Test a web scraper URL"""
    try:
        data = request.get_json()
        url = data.get('url')
        selector_config = data.get('selector_config', {})
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Use enhanced scraper for testing
        try:
            events = enhanced_scraper.scrape_events(url, selector_config)
            
            # Format results for testing
            sample_events = []
            for event in events[:5]:  # Limit to 5 samples
                sample = {
                    'title': event.get('title', 'Unknown'),
                    'date': event.get('start_date', 'No date found'),
                    'location': event.get('location', 'No location'),
                    'confidence': event.get('confidence_score', 0)
                }
                sample_events.append(sample)
            
            return jsonify({
                'success': len(events) > 0,
                'message': f'Found {len(events)} potential events (showing top {len(sample_events)})',
                'sample_events': sample_events,
                'total_found': len(events),
                'avg_confidence': sum(e.get('confidence_score', 0) for e in events) / len(events) if events else 0
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Enhanced scraper error: {str(e)}'
            })
        
    except Exception as e:
        app.logger.error(f"Error testing web scraper: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error testing URL: {str(e)}'
        })

@app.route('/api/web-scrapers/<int:scraper_id>/scrape', methods=['POST'])
@require_auth
def scrape_website(scraper_id):
    """Scrape a specific website"""
    try:
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Get scraper details
        cursor.execute('SELECT * FROM web_scrapers WHERE id = ?', (scraper_id,))
        scraper_row = cursor.fetchone()
        
        if not scraper_row:
            return jsonify({'error': 'Scraper not found'}), 404
        
        scraper = {
            'id': scraper_row[0],
            'name': scraper_row[1],
            'url': scraper_row[2],
            'description': scraper_row[3],
            'category': scraper_row[4],
            'update_interval': scraper_row[5],
            'is_active': bool(scraper_row[6]),
            'selector_config': json.loads(scraper_row[7]) if scraper_row[7] and isinstance(scraper_row[7], str) else {},
            'created_at': scraper_row[8],
            'last_run': scraper_row[9],
            'total_events': scraper_row[10],
            'consecutive_failures': scraper_row[11]
        }
        
        # Use enhanced scraper for actual scraping
        try:
            events = enhanced_scraper.scrape_events(scraper['url'], scraper['selector_config'])
            events_found = len(events)
            events_added = 0
            
            for event in events:
                # Only add high-confidence events
                if event.get('confidence_score', 0) < 60:
                    continue
                
                title = event.get('title', '').strip()
                description = event.get('description', '').strip()
                start_date = event.get('start_date', '').strip()
                location = event.get('location', '').strip()
                price = event.get('price_info', '').strip()
                event_url = event.get('url', scraper['url'])
                
                if not title:
                    continue
                
                # Check if event already exists (check both title and date)
                cursor.execute('''
                    SELECT id FROM events 
                    WHERE title = ? AND (start_datetime = ? OR start_datetime LIKE ?)
                ''', (title, start_date, f'%{start_date[:10]}%' if start_date else ''))
                
                if not cursor.fetchone():
                    # Add event to approval queue
                    cursor.execute('''
                        INSERT INTO events (title, description, start_datetime, location_name, price_info, 
                                          url, source, approval_status, created_at, category_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        title,
                        description,
                        start_date or datetime.now().isoformat(),
                        location,
                        price,
                        event_url,
                        'scraper',
                        'pending',
                        datetime.now().isoformat(),
                        1  # Default category
                    ))
                    events_added += 1
                    
        except Exception as e:
            app.logger.error(f"Enhanced scraper error: {str(e)}")
            # Update failure count
            cursor.execute('''
                UPDATE web_scrapers 
                SET consecutive_failures = consecutive_failures + 1, last_run = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (scraper_id,))
            conn.commit()
            conn.close()
            return jsonify({'error': f'Scraping error: {str(e)}'}), 400
        
        # Update scraper stats
        cursor.execute('''
            UPDATE web_scrapers 
            SET last_run = CURRENT_TIMESTAMP, 
                total_events = total_events + ?,
                consecutive_failures = 0
            WHERE id = ?
        ''', (events_added, scraper_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': f'Scraping completed. Found {events_found} events, added {events_added} new events to approval queue.',
            'events_found': events_found,
            'events_added': events_added
        })
        
    except Exception as e:
        app.logger.error(f"Error scraping website: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/web-scrapers/analytics')
@require_auth
def get_web_scraper_analytics():
    """Get web scraper analytics"""
    try:
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute('SELECT COUNT(*) FROM web_scrapers')
        total_scrapers = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM web_scrapers WHERE is_active = 1')
        active_scrapers = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_events) FROM web_scrapers')
        total_events = cursor.fetchone()[0] or 0
        
        # Calculate health score
        cursor.execute('SELECT COUNT(*) FROM web_scrapers WHERE consecutive_failures > 3')
        failing_scrapers = cursor.fetchone()[0]
        health_score = max(0, 100 - (failing_scrapers * 20)) if total_scrapers > 0 else 100
        
        conn.close()
        
        return jsonify({
            'totalScrapers': total_scrapers,
            'activeScrapers': active_scrapers,
            'totalScrapedEvents': total_events,
            'healthScore': health_score
        })
        
    except Exception as e:
        app.logger.error(f"Error getting web scraper analytics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scheduler/status')
@require_auth
def get_scheduler_status_api():
    """Get scheduler status"""
    try:
        status = get_scheduler_status()
        return jsonify(status)
    except Exception as e:
        app.logger.error(f"Error getting scheduler status: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)
