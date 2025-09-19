#!/usr/bin/env python3
"""
RSS Feed Management System
Handles RSS feed processing, event extraction, and database management
"""

import sqlite3
import feedparser
import requests
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import time
import logging
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET
import schedule
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSManager:
    def __init__(self, db_path: str = 'calendar.db'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; EventCalendar/1.0)'
        })
    
    def validate_rss_url(self, url: str) -> Tuple[bool, str]:
        """Validate if URL is a valid RSS feed"""
        try:
            # Check if URL is accessible with longer timeout for slow feeds
            response = self.session.head(url, timeout=30)
            if response.status_code != 200:
                return False, f"URL returned status code {response.status_code}"
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'xml' not in content_type and 'rss' not in content_type:
                return False, "URL does not appear to be an RSS feed (invalid content type)"
            
            # Fetch and parse the feed with timeout
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            if feed.bozo:
                return False, f"Invalid RSS format: {feed.bozo_exception}"
            
            if not feed.entries:
                return False, "RSS feed contains no entries"
            
            return True, "Valid RSS feed"
            
        except requests.RequestException as e:
            return False, f"Network error: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def test_feed_url(self, url: str) -> Dict:
        """Test an RSS feed URL and return detailed information"""
        try:
            # Validate the URL first
            is_valid, message = self.validate_rss_url(url)
            
            if not is_valid:
                return {
                    'success': False,
                    'message': message,
                    'events': 0
                }
            
            # Fetch the feed content with timeout
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse the feed content
            feed = feedparser.parse(response.content)
            
            # Count potential events
            event_count = 0
            for entry in feed.entries:
                # Simple heuristic to determine if it's an event
                title = entry.get('title', '').lower()
                description = entry.get('description', '').lower()
                
                # Look for event-related keywords
                event_keywords = ['event', 'concert', 'show', 'performance', 'exhibition', 'workshop', 'meeting', 'conference', 'festival']
                if any(keyword in title or keyword in description for keyword in event_keywords):
                    event_count += 1
            
            return {
                'success': True,
                'message': f"Feed is valid and accessible. Found {len(feed.entries)} total items, {event_count} potential events.",
                'events': event_count,
                'total_items': len(feed.entries),
                'feed_title': feed.feed.get('title', 'Unknown'),
                'feed_description': feed.feed.get('description', 'No description available')
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error testing feed: {str(e)}",
                'events': 0
            }
    
    def add_feed(self, name: str, url: str, description: str = "", 
                 category: str = "events", update_interval: int = 30, enabled: bool = True) -> Tuple[bool, str]:
        """Add a new RSS feed"""
        # Validate the feed first
        is_valid, message = self.validate_rss_url(url)
        if not is_valid:
            return False, message
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if feed already exists
            cursor.execute('SELECT id FROM rss_feeds WHERE url = ?', (url,))
            if cursor.fetchone():
                return False, "RSS feed already exists"
            
            # Insert new feed
            cursor.execute('''
                INSERT INTO rss_feeds (name, url, description, category, update_interval, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, url, description, category, update_interval, enabled))
            
            feed_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Perform initial pull
            self.process_feed(feed_id)
            
            return True, f"RSS feed added successfully. Initial pull completed."
            
        except Exception as e:
            return False, f"Database error: {str(e)}"
    
    def process_feed(self, feed_id: int) -> Dict[str, int]:
        """Process a single RSS feed and extract events"""
        start_time = time.time()
        results = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get feed information
            cursor.execute('SELECT name, url FROM rss_feeds WHERE id = ?', (feed_id,))
            feed_info = cursor.fetchone()
            if not feed_info:
                return results
            
            feed_name, feed_url = feed_info
            
            # Fetch and parse the RSS feed with timeout
            response = self.session.get(feed_url, timeout=30)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                self.log_feed_check(feed_id, 'error', 0, 0, 0, f"RSS parsing error: {feed.bozo_exception}")
                return results
            
            # Process each entry
            for entry in feed.entries:
                try:
                    event_data = self.extract_event_data(entry, feed_name)
                    if event_data:
                        result = self.add_or_update_event(event_data, feed_id, entry.get('link', ''))
                        results[result] += 1
                    else:
                        results['skipped'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing entry: {str(e)}")
                    results['errors'] += 1
            
            # Update feed status
            response_time = int((time.time() - start_time) * 1000)
            self.log_feed_check(feed_id, 'success', results['added'], results['updated'], 
                              results['skipped'], response_time=response_time)
            
            # Update last checked time
            cursor.execute('''
                UPDATE rss_feeds 
                SET last_checked = ?, last_successful_check = ?, consecutive_failures = 0
                WHERE id = ?
            ''', (datetime.now().isoformat(), datetime.now().isoformat(), feed_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error processing feed {feed_id}: {str(e)}")
            self.log_feed_check(feed_id, 'error', 0, 0, 0, str(e))
            results['errors'] += 1
        
        return results
    
    def extract_event_data(self, entry, feed_name: str) -> Optional[Dict]:
        """Extract event data from RSS entry"""
        try:
            # Basic event data
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            description = entry.get('description', '').strip()
            if not description:
                description = entry.get('summary', '').strip()
            
            # Try to extract date/time information
            start_datetime = None
            end_datetime = None
            
            # Check for published date
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                start_datetime = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                start_datetime = datetime(*entry.updated_parsed[:6])
            
            # Try to extract date from title or description
            if not start_datetime:
                date_match = re.search(r'(\w+day,?\s+\w+\s+\d{1,2},?\s+\d{4})', title + ' ' + description)
                if date_match:
                    try:
                        start_datetime = datetime.strptime(date_match.group(1), '%A, %B %d, %Y')
                    except:
                        try:
                            start_datetime = datetime.strptime(date_match.group(1), '%A %B %d, %Y')
                        except:
                            pass
            
            # Default to current date if no date found
            if not start_datetime:
                start_datetime = datetime.now()
            
            # Set end time (default 2 hours later)
            end_datetime = start_datetime + timedelta(hours=2)
            
            # Extract location information
            location = self.extract_location(description)
            
            # Determine category
            category_id = self.determine_category(title, description, feed_name)
            
            return {
                'title': title,
                'start_datetime': start_datetime.isoformat(),
                'end_datetime': end_datetime.isoformat(),
                'description': description,
                'location_name': location,
                'address': location,
                'price_info': 'Free',  # Default, could be extracted from description
                'url': entry.get('link', ''),
                'tags': f'rss,{feed_name.lower().replace(" ", "-")}',
                'category_id': category_id
            }
            
        except Exception as e:
            logger.error(f"Error extracting event data: {str(e)}")
            return None
    
    def extract_location(self, text: str) -> str:
        """Extract location information from text"""
        # Common DC area locations
        dc_locations = [
            'Washington, DC', 'Washington DC', 'DC', 'Washington D.C.',
            'Georgetown', 'Dupont Circle', 'Adams Morgan', 'Capitol Hill',
            'National Mall', 'Kennedy Center', 'Smithsonian', 'Library of Congress'
        ]
        
        for location in dc_locations:
            if location.lower() in text.lower():
                return location
        
        return 'Washington, DC'  # Default location
    
    def determine_category(self, title: str, description: str, feed_name: str) -> int:
        """Determine event category based on content"""
        text = (title + ' ' + description + ' ' + feed_name).lower()
        
        if any(word in text for word in ['book', 'author', 'reading', 'literature', 'poetry']):
            return 1  # Literature
        elif any(word in text for word in ['music', 'concert', 'symphony', 'orchestra', 'band']):
            return 2  # Music
        elif any(word in text for word in ['theater', 'theatre', 'play', 'drama', 'performance']):
            return 3  # Theater
        elif any(word in text for word in ['art', 'gallery', 'museum', 'exhibition', 'painting']):
            return 4  # Art
        else:
            return 1  # Default to Literature
    
    def add_or_update_event(self, event_data: Dict, feed_id: int, source_url: str) -> str:
        """Add new event or update existing one"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if event already exists by source URL
            cursor.execute('''
                SELECT e.id FROM events e
                JOIN event_sources es ON e.id = es.event_id
                WHERE es.feed_id = ? AND es.source_url = ?
            ''', (feed_id, source_url))
            
            existing_event = cursor.fetchone()
            
            if existing_event:
                # Update existing event (but respect manual overrides)
                event_id = existing_event[0]
                
                # Check for manual overrides
                cursor.execute('''
                    SELECT field_name FROM manual_overrides WHERE event_id = ?
                ''', (event_id,))
                overrides = [row[0] for row in cursor.fetchall()]
                
                # Update only non-overridden fields
                update_fields = []
                update_values = []
                
                for field, value in event_data.items():
                    if field not in overrides and field != 'tags':  # Skip tags for updates
                        update_fields.append(f"{field} = ?")
                        update_values.append(value)
                
                if update_fields:
                    update_values.append(event_id)
                    cursor.execute(f'''
                        UPDATE events SET {', '.join(update_fields)}
                        WHERE id = ?
                    ''', update_values)
                
                # Update event source timestamp
                cursor.execute('''
                    UPDATE event_sources SET last_updated = ?
                    WHERE event_id = ? AND feed_id = ?
                ''', (datetime.now().isoformat(), event_id, feed_id))
                
                result = 'updated'
            else:
                # Add new event
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
                    event_data['category_id'],
                    datetime.now().isoformat()
                ))
                
                event_id = cursor.lastrowid
                
                # Add event source
                cursor.execute('''
                    INSERT INTO event_sources (event_id, feed_id, source_url, source_id)
                    VALUES (?, ?, ?, ?)
                ''', (event_id, feed_id, source_url, source_url))
                
                result = 'added'
            
            conn.commit()
            return result
            
        except Exception as e:
            logger.error(f"Error adding/updating event: {str(e)}")
            return 'error'
        finally:
            conn.close()
    
    def log_feed_check(self, feed_id: int, status: str, events_added: int, 
                      events_updated: int, events_skipped: int, 
                      error_message: str = None, response_time: int = None):
        """Log feed check results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rss_feed_logs 
            (feed_id, status, events_added, events_updated, events_skipped, error_message, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (feed_id, status, events_added, events_updated, events_skipped, error_message, response_time))
        
        # Update consecutive failures
        if status == 'error':
            cursor.execute('''
                UPDATE rss_feeds SET consecutive_failures = consecutive_failures + 1
                WHERE id = ?
            ''', (feed_id,))
        else:
            cursor.execute('''
                UPDATE rss_feeds SET consecutive_failures = 0
                WHERE id = ?
            ''', (feed_id,))
        
        conn.commit()
        conn.close()
    
    def get_feed_status(self, feed_id: int = None) -> List[Dict]:
        """Get status information for feeds"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if feed_id:
            cursor.execute('''
                SELECT f.*, 
                       (SELECT COUNT(*) FROM event_sources es WHERE es.feed_id = f.id) as total_events,
                       (SELECT COUNT(*) FROM rss_feed_logs rfl WHERE rfl.feed_id = f.id AND rfl.status = 'error') as error_count
                FROM rss_feeds f WHERE f.id = ?
            ''', (feed_id,))
        else:
            cursor.execute('''
                SELECT f.*, 
                       (SELECT COUNT(*) FROM event_sources es WHERE es.feed_id = f.id) as total_events,
                       (SELECT COUNT(*) FROM rss_feed_logs rfl WHERE rfl.feed_id = f.id AND rfl.status = 'error') as error_count
                FROM rss_feeds f ORDER BY f.name
            ''')
        
        feeds = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return feeds
    
    def get_feed_logs(self, feed_id: int = None, limit: int = 50) -> List[Dict]:
        """Get feed activity logs"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if feed_id:
            cursor.execute('''
                SELECT rfl.*, f.name as feed_name
                FROM rss_feed_logs rfl
                JOIN rss_feeds f ON rfl.feed_id = f.id
                WHERE rfl.feed_id = ?
                ORDER BY rfl.check_time DESC
                LIMIT ?
            ''', (feed_id, limit))
        else:
            cursor.execute('''
                SELECT rfl.*, f.name as feed_name
                FROM rss_feed_logs rfl
                JOIN rss_feeds f ON rfl.feed_id = f.id
                ORDER BY rfl.check_time DESC
                LIMIT ?
            ''', (limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return logs
    
    def process_all_feeds(self) -> Dict[str, int]:
        """Process all active feeds"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM rss_feeds WHERE is_active = 1')
        feed_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        total_results = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': 0}
        
        for feed_id in feed_ids:
            results = self.process_feed(feed_id)
            for key, value in results.items():
                total_results[key] += value
        
        return total_results
    
    def get_all_feeds(self) -> List[Dict]:
        """Get all RSS feeds"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.id, f.name, f.url, f.description, f.category, f.is_active, 
                   f.last_checked, f.created_at, f.update_interval, f.consecutive_failures,
                   COUNT(es.event_id) as total_events,
                   l.check_time as last_check_time,
                   l.response_time_ms as last_response_time
            FROM rss_feeds f
            LEFT JOIN event_sources es ON f.id = es.feed_id
            LEFT JOIN (
                SELECT feed_id, check_time, response_time_ms,
                       ROW_NUMBER() OVER (PARTITION BY feed_id ORDER BY check_time DESC) as rn
                FROM rss_feed_logs
            ) l ON f.id = l.feed_id AND l.rn = 1
            GROUP BY f.id, f.name, f.url, f.description, f.category, f.is_active, 
                     f.last_checked, f.created_at, f.update_interval, f.consecutive_failures,
                     l.check_time, l.response_time_ms
            ORDER BY f.created_at DESC
        ''')
        
        feeds = []
        for row in cursor.fetchall():
            feed = {
                'id': row[0],
                'name': row[1],
                'url': row[2],
                'description': row[3],
                'category': row[4],
                'enabled': bool(row[5]),
                'is_active': bool(row[5]),  # Keep both for compatibility
                'last_checked': row[6],
                'created_at': row[7],
                'update_interval': row[8],
                'consecutive_failures': row[9] or 0,
                'total_events': row[10] or 0,
                'last_check_time': row[11],
                'last_response_time': row[12] or 0
            }
            feeds.append(feed)
        
        conn.close()
        return feeds
    
    def update_feed(self, feed_id: int, data: Dict) -> bool:
        """Update an RSS feed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE rss_feeds 
                SET name = ?, url = ?, description = ?, category = ?, 
                    is_active = ?, update_interval = ?
                WHERE id = ?
            ''', (
                data.get('name'),
                data.get('url'),
                data.get('description', ''),
                data.get('category', 'General'),
                data.get('enabled', True),
                data.get('update_interval', 60),
                feed_id
            ))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating feed {feed_id}: {e}")
            return False
        finally:
            conn.close()
    
    def delete_feed(self, feed_id: int) -> bool:
        """Delete an RSS feed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM rss_feeds WHERE id = ?', (feed_id,))
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting feed {feed_id}: {e}")
            return False
        finally:
            conn.close()
    
    def refresh_feed(self, feed_id: int) -> Dict:
        """Manually refresh a specific RSS feed"""
        try:
            result = self.process_feed(feed_id)
            return {
                'success': True,
                'feed_id': feed_id,
                'events_added': result.get('events_added', 0),
                'message': f"Feed refreshed successfully. Added {result.get('events_added', 0)} events."
            }
        except Exception as e:
            return {
                'success': False,
                'feed_id': feed_id,
                'error': str(e)
            }
    
    def refresh_all_feeds(self) -> Dict:
        """Manually refresh all RSS feeds"""
        try:
            result = self.process_all_feeds()
            return {
                'success': True,
                'feeds_processed': len([f for f in self.get_all_feeds() if f['is_active']]),
                'events_added': result.get('added', 0),
                'events_updated': result.get('updated', 0),
                'message': f"Refreshed feeds. Added {result.get('added', 0)} new events, updated {result.get('updated', 0)} existing events."
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_logs(self, limit: int = 100) -> List[Dict]:
        """Get RSS feed logs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.id, l.feed_id, f.name as feed_name, l.status, 
                   l.events_added, l.message, l.checked_at
            FROM rss_feed_logs l
            LEFT JOIN rss_feeds f ON l.feed_id = f.id
            ORDER BY l.checked_at DESC
            LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            log = {
                'id': row[0],
                'feed_id': row[1],
                'feed_name': row[2],
                'status': row[3],
                'events_added': row[4],
                'message': row[5],
                'checked_at': row[6]
            }
            logs.append(log)
        
        conn.close()
        return logs
    
    def get_categories(self) -> List[str]:
        """Get available RSS feed categories"""
        return [
            'General',
            'Events',
            'News',
            'Entertainment',
            'Sports',
            'Technology',
            'Business',
            'Education',
            'Community',
            'Arts'
        ]
    
    def override_event_source(self, event_id: int, reason: str) -> bool:
        """Override event source (mark as manually added)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO manual_overrides (event_id, reason, created_at)
                VALUES (?, ?, ?)
            ''', (event_id, reason, datetime.now().isoformat()))
            
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error overriding event source {event_id}: {e}")
            return False
        finally:
            conn.close()

# Example usage
if __name__ == "__main__":
    rss_manager = RSSManager()
    
    # Add a sample feed
    success, message = rss_manager.add_feed(
        name="Washingtonian Events",
        url="https://www.washingtonian.com/tag/neighborhood-guide/feed/",
        description="Local events from Washingtonian magazine",
        category="events",
        update_interval=30
    )
    
    print(f"Feed addition: {success} - {message}")
    
    # Process all feeds
    results = rss_manager.process_all_feeds()
    print(f"Processing results: {results}")

# Global scheduler instance
_scheduler_thread = None
_scheduler_running = False

def start_rss_scheduler():
    """Start the RSS feed scheduler in a background thread"""
    global _scheduler_thread, _scheduler_running
    
    if _scheduler_running:
        logger.info("RSS scheduler is already running")
        return
    
    def run_scheduler():
        global _scheduler_running
        _scheduler_running = True
        logger.info("RSS scheduler started")
        
        # Schedule RSS feed updates every hour
        schedule.every().hour.do(lambda: RSSManager().process_all_feeds())
        
        # Run scheduler
        while _scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        
        logger.info("RSS scheduler stopped")
    
    _scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    _scheduler_thread.start()
    logger.info("RSS feed scheduler started successfully!")

def get_scheduler_status():
    """Get the current status of the RSS scheduler"""
    global _scheduler_running, _scheduler_thread
    
    return {
        'running': _scheduler_running,
        'thread_alive': _scheduler_thread.is_alive() if _scheduler_thread else False,
        'next_run': str(schedule.next_run()) if schedule.jobs else None,
        'job_count': len(schedule.jobs)
    }

def stop_rss_scheduler():
    """Stop the RSS feed scheduler"""
    global _scheduler_running
    _scheduler_running = False
    schedule.clear()
    logger.info("RSS scheduler stopped")

