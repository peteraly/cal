"""
Web scraping service for automated event discovery.
Handles fetching, parsing, and storing events from monitored URLs.
"""

import requests
import sqlite3
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
import time
import json
from ai_parser import EventParser
from event_tracker import event_tracker
from thingstodo_scraper import ThingsToDoScraper

class ScraperService:
    """Service for scraping events from monitored URLs."""
    
    def __init__(self, database_path: str = 'calendar.db'):
        self.database_path = database_path
        self.parser = EventParser()
        self.thingstodo_scraper = ThingsToDoScraper()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_db_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def is_thingstodo_url(self, url: str) -> bool:
        """Check if URL is from thingstododc.com."""
        return 'thingstododc.com' in url.lower()
    
    def scrape_thingstodo_event(self, url: str) -> List[Dict]:
        """Scrape a single thingstododc.com event page."""
        try:
            # Use the specialized scraper
            scraped_data = self.thingstodo_scraper.scrape_event(url)
            
            # Check for errors
            if 'error' in scraped_data:
                print(f"Error scraping {url}: {scraped_data['error']}")
                return []
            
            # Convert to the format expected by the existing system
            event = {
                'title': scraped_data.get('title', ''),
                'date': scraped_data.get('start_date', ''),
                'time': scraped_data.get('start_time', ''),
                'endTime': scraped_data.get('end_time', ''),
                'location': scraped_data.get('location', ''),
                'price': scraped_data.get('price', 0.0),
                'description': scraped_data.get('description', ''),
                'url': scraped_data.get('url', url),
                'raw_data': json.dumps(scraped_data)
            }
            
            # Only return if we have at least a title
            if event['title']:
                return [event]
            else:
                return []
                
        except Exception as e:
            print(f"Error in scrape_thingstodo_event: {str(e)}")
            return []
    
    def run_scraping_cycle(self) -> Dict:
        """Run scraping cycle for all enabled URLs."""
        results = {
            'total_urls': 0,
            'successful': 0,
            'failed': 0,
            'events_found': 0,
            'events_added': 0,
            'details': []
        }
        
        try:
            conn = self.get_db_connection()
            urls = conn.execute('''
                SELECT * FROM monitored_urls WHERE enabled = 1
            ''').fetchall()
            
            results['total_urls'] = len(urls)
            
            for url_record in urls:
                try:
                    result = self.scrape_url(url_record)
                    results['details'].append(result)
                    
                    if result['status'] == 'success':
                        results['successful'] += 1
                        results['events_found'] += result['events_found']
                        results['events_added'] += result['events_added']
                    else:
                        results['failed'] += 1
                        
                except Exception as e:
                    self.log_activity(
                        url_record['id'], 
                        'error', 
                        f'Unexpected error: {str(e)}',
                        error_details=str(e)
                    )
                    results['failed'] += 1
                    results['details'].append({
                        'url': url_record['url'],
                        'status': 'error',
                        'message': str(e)
                    })
                
                # Rate limiting - wait between requests
                time.sleep(2)
            
            conn.close()
            
        except Exception as e:
            print(f"Error in scraping cycle: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def scrape_url(self, url_record: sqlite3.Row) -> Dict:
        """Scrape a single URL for events."""
        url = url_record['url']
        url_id = url_record['id']
        
        result = {
            'url': url,
            'status': 'unknown',
            'message': '',
            'events_found': 0,
            'events_added': 0
        }
        
        try:
            # Check if this is a thingstododc.com URL and use specialized scraper
            if self.is_thingstodo_url(url):
                events = self.scrape_thingstodo_event(url)
                result['events_found'] = len(events) if events else 0
            else:
                # Use the general scraper for other URLs
                response = self.fetch_page(url)
                if not response:
                    result['status'] = 'error'
                    result['message'] = 'Failed to fetch page'
                    self.log_activity(url_id, 'error', 'Failed to fetch page')
                    return result
                
                # Extract text content
                text_content = self.extract_text_content(response.text, url)
                if not text_content:
                    result['status'] = 'error'
                    result['message'] = 'No content found'
                    self.log_activity(url_id, 'error', 'No content found')
                    return result
                
                # Parse events from content
                events = self.parse_events_from_text(text_content, url)
                result['events_found'] = len(events)
            
            if not events:
                result['status'] = 'success'
                result['message'] = 'No events found'
                self.log_activity(url_id, 'success', 'No events found', 0, 0)
                return result
            
            # Process and store events
            events_added = self.process_events(events, url_id, url)
            result['events_added'] = events_added
            
            # Update last scraped time
            self.update_last_scraped(url_id)
            
            result['status'] = 'success'
            result['message'] = f'Found {len(events)} events, added {events_added} new ones'
            self.log_activity(
                url_id, 
                'success', 
                result['message'], 
                len(events), 
                events_added
            )
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = str(e)
            self.log_activity(url_id, 'error', str(e), error_details=str(e))
        
        return result
    
    def fetch_page(self, url: str) -> Optional[requests.Response]:
        """Fetch a webpage with error handling."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {str(e)}")
            return None
    
    def extract_text_content(self, html: str, base_url: str) -> str:
        """Extract text content from HTML."""
        try:
            # Remove script and style elements
            html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Look for event-related content
            event_indicators = [
                r'event[s]?', r'meeting[s]?', r'conference[s]?', r'workshop[s]?',
                r'concert[s]?', r'show[s]?', r'exhibition[s]?', r'gallery',
                r'date[s]?', r'time[s]?', r'location[s]?', r'venue[s]?'
            ]
            
            # If text is too short or doesn't contain event indicators, return empty
            if len(text) < 100 or not any(re.search(indicator, text, re.IGNORECASE) for indicator in event_indicators):
                return ""
            
            return text
            
        except Exception as e:
            print(f"Error extracting text content: {str(e)}")
            return ""
    
    def parse_events_from_text(self, text: str, source_url: str) -> List[Dict]:
        """Parse events from text content using the AI parser."""
        events = []
        
        try:
            # Split text into potential event blocks
            event_blocks = self.split_into_event_blocks(text)
            
            for block in event_blocks:
                if len(block.strip()) < 50:  # Skip very short blocks
                    continue
                
                # Parse the block
                parsed_event = self.parser.parse_natural_language(block)
                
                # Validate the parsed event
                if self.is_valid_event(parsed_event):
                    # Add source information
                    parsed_event['source_url'] = source_url
                    parsed_event['raw_data'] = block
                    events.append(parsed_event)
        
        except Exception as e:
            print(f"Error parsing events from text: {str(e)}")
        
        return events
    
    def split_into_event_blocks(self, text: str) -> List[str]:
        """Split text into potential event blocks."""
        # Common separators for event blocks
        separators = [
            r'\n\s*\n',  # Double newlines
            r'\.\s+(?=[A-Z])',  # Period followed by capital letter
            r';\s+',  # Semicolons
            r'Event:', r'Meeting:', r'Conference:', r'Workshop:',  # Event type indicators
        ]
        
        blocks = [text]  # Start with the full text
        
        for separator in separators:
            new_blocks = []
            for block in blocks:
                parts = re.split(separator, block, flags=re.IGNORECASE)
                new_blocks.extend([part.strip() for part in parts if part.strip()])
            blocks = new_blocks
        
        # Filter blocks that look like events
        event_blocks = []
        for block in blocks:
            if (len(block) > 50 and 
                any(keyword in block.lower() for keyword in ['event', 'meeting', 'date', 'time', 'location', 'venue'])):
                event_blocks.append(block)
        
        return event_blocks
    
    def is_valid_event(self, event: Dict) -> bool:
        """Check if a parsed event is valid."""
        # Must have a title
        if not event.get('title') or len(event['title'].strip()) < 3:
            return False
        
        # Must have either date or time
        if not event.get('date') and not event.get('time'):
            return False
        
        # Title shouldn't be too long (likely not an event)
        if len(event['title']) > 200:
            return False
        
        return True
    
    def process_events(self, events: List[Dict], url_id: int, source_url: str) -> int:
        """Process and store events using advanced duplicate detection."""
        events_added = 0
        events_skipped = 0
        events_reviewed = 0
        
        try:
            conn = self.get_db_connection()
            
            for event in events:
                # Use advanced event tracking system
                result = event_tracker.process_new_event(event, source_url)
                
                if result['action'] == 'skip':
                    events_skipped += 1
                    self.log_activity(
                        url_id, 
                        'info', 
                        f"Skipped duplicate: {result['reason']}",
                        events_found=1,
                        events_added=0
                    )
                    continue
                
                elif result['action'] == 'review':
                    events_reviewed += 1
                    # Store with review flag
                    event_id = self._store_event_for_review(event, url_id, conn, result)
                    if event_id:
                        # Store fingerprint for future duplicate detection
                        event_tracker.store_event_fingerprint(event_id, result['fingerprint'], 'scraped_events')
                        events_added += 1
                
                elif result['action'] == 'add':
                    # Store new event for review
                    event_id = self._store_event_for_review(event, url_id, conn, result)
                    if event_id:
                        # Store fingerprint for future duplicate detection
                        event_tracker.store_event_fingerprint(event_id, result['fingerprint'], 'scraped_events')
                        events_added += 1
            
            conn.commit()
            conn.close()
            
            # Log summary
            self.log_activity(
                url_id,
                'success',
                f"Processed {len(events)} events: {events_added} new, {events_skipped} duplicates, {events_reviewed} for review",
                events_found=len(events),
                events_added=events_added
            )
            
        except Exception as e:
            print(f"Error processing events: {str(e)}")
            self.log_activity(url_id, 'error', f"Error processing events: {str(e)}")
        
        return events_added
    
    def _store_event_for_review(self, event: Dict, url_id: int, conn: sqlite3.Connection, result: Dict) -> Optional[int]:
        """Store event in scraped_events table for review."""
        try:
            cursor = conn.execute('''
                INSERT INTO scraped_events 
                (url_id, title, start_datetime, description, location, price_info, url, raw_data, event_hash, confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                url_id,
                event.get('title', ''),
                self.format_datetime(event.get('date'), event.get('time')),
                event.get('description', ''),
                event.get('location', ''),
                event.get('price', ''),
                event.get('url', ''),
                event.get('raw_data', ''),
                result.get('fingerprint', {}).get('hash_key', ''),
                result.get('confidence', 0.0)
            ))
            
            return cursor.lastrowid
            
        except Exception as e:
            print(f"Error storing event for review: {str(e)}")
            return None
    
    def create_event_hash(self, event: Dict) -> str:
        """Create a unique hash for an event to detect duplicates."""
        # Use title, date, and location for hash
        hash_string = f"{event.get('title', '')}{event.get('date', '')}{event.get('location', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def event_exists(self, event_hash: str, conn: sqlite3.Connection) -> bool:
        """Check if an event with the same hash already exists."""
        # Check in main events table
        existing = conn.execute('''
            SELECT 1 FROM events WHERE title || start_datetime || location = ?
        ''', (event_hash,)).fetchone()
        
        if existing:
            return True
        
        # Check in scraped_events table
        existing = conn.execute('''
            SELECT 1 FROM scraped_events WHERE title || start_datetime || location = ?
        ''', (event_hash,)).fetchone()
        
        return existing is not None
    
    def format_datetime(self, date: str, time: str) -> str:
        """Format date and time into ISO format."""
        try:
            if not date:
                return ""
            
            # If we have both date and time, combine them
            if time:
                return f"{date}T{time}:00"
            else:
                return f"{date}T00:00:00"
        except:
            return ""
    
    def update_last_scraped(self, url_id: int):
        """Update the last scraped timestamp for a URL."""
        try:
            conn = self.get_db_connection()
            conn.execute('''
                UPDATE monitored_urls 
                SET last_scraped = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (url_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating last scraped time: {str(e)}")
    
    def log_activity(self, url_id: int, status: str, message: str, 
                    events_found: int = 0, events_added: int = 0, 
                    error_details: str = None):
        """Log scraper activity."""
        try:
            conn = self.get_db_connection()
            conn.execute('''
                INSERT INTO scraper_logs 
                (url_id, status, message, events_found, events_added, error_details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url_id, status, message, events_found, events_added, error_details))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging activity: {str(e)}")

# Example usage and testing
if __name__ == "__main__":
    scraper = ScraperService()
    results = scraper.run_scraping_cycle()
    print(json.dumps(results, indent=2))
