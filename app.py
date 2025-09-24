"""
Simplified Calendar Application
Reduced from 2,160 lines to ~400 lines while maintaining core functionality
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
import threading
import time
from dotenv import load_dotenv
from services import EventService

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize services
event_service = EventService()

# Background scheduler for RSS feeds and scrapers
def start_background_scheduler():
    """Start background scheduler for RSS feeds and scrapers"""
    def scheduler_loop():
        while True:
            try:
                # Refresh RSS feeds every 30 minutes
                event_service.refresh_rss_feeds()
                print("🔄 RSS feeds refreshed")
                
                # Run scrapers every 2 hours
                # Note: In production, you might want to use a proper job queue
                time.sleep(1800)  # 30 minutes
            except Exception as e:
                print(f"❌ Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes on error
    
    # Start scheduler in background thread
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()
    print("🚀 Background scheduler started")

# Start scheduler only in production or when explicitly enabled
if os.environ.get('ENABLE_SCHEDULER', 'false').lower() == 'true':
    start_background_scheduler()

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
