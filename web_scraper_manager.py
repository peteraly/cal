"""
Web Scraper Manager for Calendar Events
Handles web scraping of event websites with scheduling and history tracking
"""

import sqlite3
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import schedule
import threading
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapedEvent:
    """Data class for scraped event information"""
    title: str
    description: str = ""
    start_datetime: str = ""
    end_datetime: str = ""
    location_name: str = ""
    address: str = ""
    price_info: str = ""
    url: str = ""
    tags: str = ""
    category_id: int = 1

class WebScraperManager:
    """Manages web scraping operations for event websites"""
    
    def __init__(self, db_path: str = "calendar.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.init_database()
    
    def init_database(self):
        """Initialize database tables for web scrapers"""
        try:
            with open('web_scrapers_schema.sql', 'r') as f:
                schema = f.read()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.executescript(schema)
            conn.commit()
            conn.close()
            logger.info("Web scraper database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing web scraper database: {e}")
    
    def add_scraper(self, name: str, url: str, description: str = "", 
                   category: str = "events", selector_config: Dict = None,
                   update_interval: int = 60, enabled: bool = True) -> Tuple[bool, str]:
        """Add a new web scraper"""
        try:
            # Validate URL
            if not self._validate_url(url):
                return False, "Invalid URL format"
            
            # Test scraping configuration
            if selector_config:
                test_result = self._test_scraper_config(url, selector_config)
                if not test_result['success']:
                    return False, f"Scraper configuration test failed: {test_result['message']}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if scraper already exists
            cursor.execute('SELECT id FROM web_scrapers WHERE url = ?', (url,))
            if cursor.fetchone():
                conn.close()
                return False, "Web scraper already exists for this URL"
            
            # Calculate next run time
            next_run = datetime.now() + timedelta(minutes=update_interval)
            
            # Insert new scraper
            cursor.execute('''
                INSERT INTO web_scrapers (name, url, description, category, selector_config, 
                                        update_interval, is_active, next_run)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, url, description, category, json.dumps(selector_config or {}), 
                  update_interval, enabled, next_run))
            
            scraper_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Perform initial scrape
            if enabled:
                self.scrape_website(scraper_id)
            
            return True, f"Web scraper added successfully. Initial scrape completed."
            
        except Exception as e:
            logger.error(f"Error adding web scraper: {e}")
            return False, f"Error adding web scraper: {str(e)}"
    
    def _validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _test_scraper_config(self, url: str, selector_config: Dict) -> Dict:
        """Test scraper configuration by attempting to scrape the page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Test each selector in the configuration
            results = {}
            for key, selector in selector_config.items():
                if key == 'event_container':
                    elements = soup.select(selector)
                    results[key] = len(elements)
                else:
                    # Test if selector exists
                    elements = soup.select(selector)
                    results[key] = len(elements) > 0
            
            return {
                'success': True,
                'message': f"Configuration test successful. Found {results.get('event_container', 0)} event containers.",
                'results': results
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Configuration test failed: {str(e)}"
            }
    
    def scrape_website(self, scraper_id: int) -> Dict:
        """Scrape a specific website for events"""
        start_time = time.time()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get scraper configuration
            cursor.execute('''
                SELECT name, url, selector_config, category FROM web_scrapers 
                WHERE id = ? AND is_active = 1
            ''', (scraper_id,))
            
            scraper_data = cursor.fetchone()
            if not scraper_data:
                return {'success': False, 'message': 'Scraper not found or inactive'}
            
            name, url, selector_config_json, category = scraper_data
            selector_config = json.loads(selector_config_json or '{}')
            
            # Fetch the webpage
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract events using the selector configuration
            events = self._extract_events(soup, selector_config, url)
            
            # Process and store events
            events_added = 0
            events_updated = 0
            
            for event_data in events:
                result = self._process_scraped_event(scraper_id, event_data, category)
                if result['action'] == 'added':
                    events_added += 1
                elif result['action'] == 'updated':
                    events_updated += 1
            
            # Update scraper statistics
            cursor.execute('''
                UPDATE web_scrapers 
                SET last_run = CURRENT_TIMESTAMP, 
                    next_run = datetime(CURRENT_TIMESTAMP, '+' || update_interval || ' minutes'),
                    consecutive_failures = 0,
                    total_events = total_events + ?
                WHERE id = ?
            ''', (events_added, scraper_id))
            
            # Log the scraping operation
            response_time = int((time.time() - start_time) * 1000)
            cursor.execute('''
                INSERT INTO web_scraper_logs 
                (scraper_id, status, events_found, events_added, events_updated, response_time_ms)
                VALUES (?, 'success', ?, ?, ?, ?)
            ''', (scraper_id, len(events), events_added, events_updated, response_time))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': f"Scraping completed. Found {len(events)} events, added {events_added}, updated {events_updated}",
                'events_found': len(events),
                'events_added': events_added,
                'events_updated': events_updated
            }
            
        except Exception as e:
            logger.error(f"Error scraping website {scraper_id}: {e}")
            
            # Update failure count
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE web_scrapers 
                    SET consecutive_failures = consecutive_failures + 1,
                        last_run = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (scraper_id,))
                
                # Log the error
                cursor.execute('''
                    INSERT INTO web_scraper_logs 
                    (scraper_id, status, error_message, response_time_ms)
                    VALUES (?, 'error', ?, ?)
                ''', (scraper_id, str(e), int((time.time() - start_time) * 1000)))
                
                conn.commit()
                conn.close()
            except:
                pass
            
            return {'success': False, 'message': f"Scraping failed: {str(e)}"}
    
    def _extract_events(self, soup: BeautifulSoup, selector_config: Dict, base_url: str) -> List[ScrapedEvent]:
        """Extract events from parsed HTML using selector configuration"""
        events = []
        
        # Default selectors if not provided
        default_config = {
            'event_container': '.event, .event-item, [class*="event"]',
            'title': 'h1, h2, h3, .title, .event-title',
            'description': '.description, .event-description, p',
            'date': '.date, .event-date, time',
            'time': '.time, .event-time',
            'location': '.location, .venue, .event-location',
            'price': '.price, .cost, .ticket-price'
        }
        
        # Clean and validate selectors
        config = {}
        for key, value in {**default_config, **selector_config}.items():
            if value and isinstance(value, str) and value.strip():
                # Basic validation - check if it looks like a CSS selector
                if not value.startswith(('^', '!', '@', '#', '.', '[', ':', '>', '+', '~', ' ', '\t', '\n')):
                    # If it doesn't start with a valid CSS selector character, skip it
                    config[key] = default_config.get(key, '')
                else:
                    config[key] = value.strip()
            else:
                config[key] = default_config.get(key, '')
        
        # Find event containers
        try:
            event_containers = soup.select(config['event_container'])
        except Exception as e:
            logger.warning(f"Invalid CSS selector '{config['event_container']}': {e}")
            # Fallback to a very generic selector
            event_containers = soup.find_all(['div', 'article', 'li', 'section'], limit=20)
        
        for container in event_containers:
            try:
                event = ScrapedEvent(title="")
                
                # Extract title
                try:
                    title_elem = container.select_one(config['title'])
                    if title_elem:
                        event.title = title_elem.get_text(strip=True)
                except Exception as e:
                    logger.warning(f"Error extracting title: {e}")
                
                # Extract description
                try:
                    desc_elem = container.select_one(config['description'])
                    if desc_elem:
                        event.description = desc_elem.get_text(strip=True)
                except Exception as e:
                    logger.warning(f"Error extracting description: {e}")
                
                # Extract date and time
                try:
                    date_elem = container.select_one(config['date'])
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        event.start_datetime = self._parse_datetime(date_text)
                except Exception as e:
                    logger.warning(f"Error extracting date: {e}")
                
                try:
                    time_elem = container.select_one(config['time'])
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        if event.start_datetime:
                            event.start_datetime += f" {time_text}"
                        else:
                            event.start_datetime = time_text
                except Exception as e:
                    logger.warning(f"Error extracting time: {e}")
                
                # Extract location
                try:
                    location_elem = container.select_one(config['location'])
                    if location_elem:
                        event.location_name = location_elem.get_text(strip=True)
                except Exception as e:
                    logger.warning(f"Error extracting location: {e}")
                
                # Extract price
                try:
                    price_elem = container.select_one(config['price'])
                    if price_elem:
                        event.price_info = price_elem.get_text(strip=True)
                except Exception as e:
                    logger.warning(f"Error extracting price: {e}")
                
                # Extract URL (look for links)
                link_elem = container.select_one('a[href]')
                if link_elem:
                    href = link_elem.get('href')
                    event.url = urljoin(base_url, href)
                
                # Only add events with titles
                if event.title:
                    events.append(event)
                    
            except Exception as e:
                logger.warning(f"Error extracting event from container: {e}")
                continue
        
        return events
    
    def _parse_datetime(self, date_text: str) -> str:
        """Parse date text into standardized format"""
        # This is a simplified parser - you might want to use dateutil for more robust parsing
        try:
            # Remove common prefixes
            date_text = re.sub(r'^(on|at|from)\s+', '', date_text, flags=re.IGNORECASE)
            
            # Try to extract date patterns
            date_patterns = [
                r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
                r'(\d{4}-\d{2}-\d{2})',      # YYYY-MM-DD
                r'(\w+ \d{1,2}, \d{4})',     # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_text)
                if match:
                    return match.group(1)
            
            return date_text
            
        except:
            return date_text
    
    def _process_scraped_event(self, scraper_id: int, event: ScrapedEvent, category: str) -> Dict:
        """Process a scraped event and add/update it in the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create a unique identifier for the event
            event_id = f"{scraper_id}_{hash(event.title + event.start_datetime)}"
            
            # Check if event already exists
            cursor.execute('''
                SELECT id FROM events 
                WHERE title = ? AND start_datetime = ?
            ''', (event.title, event.start_datetime))
            
            existing_event = cursor.fetchone()
            
            if existing_event:
                # Update existing event
                event_db_id = existing_event[0]
                cursor.execute('''
                    UPDATE events 
                    SET description = ?, location_name = ?, address = ?, 
                        price_info = ?, url = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (event.description, event.location_name, event.address, 
                      event.price_info, event.url, event_db_id))
                
                # Update web scraper events tracking
                cursor.execute('''
                    UPDATE web_scraper_events 
                    SET last_seen = CURRENT_TIMESTAMP, is_active = 1
                    WHERE scraper_id = ? AND event_id = ?
                ''', (scraper_id, event_db_id))
                
                conn.commit()
                conn.close()
                return {'action': 'updated', 'event_id': event_db_id}
            
            else:
                # Add new event
                cursor.execute('''
                    INSERT INTO events (title, description, start_datetime, end_datetime,
                                      location_name, address, price_info, url, tags, category_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (event.title, event.description, event.start_datetime, event.end_datetime,
                      event.location_name, event.address, event.price_info, event.url, 
                      event.tags, 1))  # Default category
                
                event_db_id = cursor.lastrowid
                
                # Track in web scraper events
                cursor.execute('''
                    INSERT INTO web_scraper_events (scraper_id, event_id, source_url, scraped_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (scraper_id, event_db_id, event.url))
                
                conn.commit()
                conn.close()
                return {'action': 'added', 'event_id': event_db_id}
                
        except Exception as e:
            logger.error(f"Error processing scraped event: {e}")
            return {'action': 'error', 'error': str(e)}
    
    def get_all_scrapers(self) -> List[Dict]:
        """Get all web scrapers with their status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT ws.id, ws.name, ws.url, ws.description, ws.category, 
                       ws.update_interval, ws.is_active, ws.last_run, ws.next_run,
                       ws.consecutive_failures, ws.total_events,
                       COUNT(wse.event_id) as current_events
                FROM web_scrapers ws
                LEFT JOIN web_scraper_events wse ON ws.id = wse.scraper_id AND wse.is_active = 1
                GROUP BY ws.id
                ORDER BY ws.created_at DESC
            ''')
            
            scrapers = []
            for row in cursor.fetchall():
                scrapers.append({
                    'id': row[0],
                    'name': row[1],
                    'url': row[2],
                    'description': row[3],
                    'category': row[4],
                    'update_interval': row[5],
                    'is_active': bool(row[6]),
                    'last_run': row[7],
                    'next_run': row[8],
                    'consecutive_failures': row[9],
                    'total_events': row[10],
                    'current_events': row[11]
                })
            
            conn.close()
            return scrapers
            
        except Exception as e:
            logger.error(f"Error getting web scrapers: {e}")
            return []
    
    def get_scraper_logs(self, scraper_id: int = None, limit: int = 50) -> List[Dict]:
        """Get web scraper logs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if scraper_id:
                cursor.execute('''
                    SELECT wsl.id, ws.name, wsl.run_time, wsl.status, wsl.events_found,
                           wsl.events_added, wsl.events_updated, wsl.response_time_ms, wsl.error_message
                    FROM web_scraper_logs wsl
                    JOIN web_scrapers ws ON wsl.scraper_id = ws.id
                    WHERE wsl.scraper_id = ?
                    ORDER BY wsl.run_time DESC
                    LIMIT ?
                ''', (scraper_id, limit))
            else:
                cursor.execute('''
                    SELECT wsl.id, ws.name, wsl.run_time, wsl.status, wsl.events_found,
                           wsl.events_added, wsl.events_updated, wsl.response_time_ms, wsl.error_message
                    FROM web_scraper_logs wsl
                    JOIN web_scrapers ws ON wsl.scraper_id = ws.id
                    ORDER BY wsl.run_time DESC
                    LIMIT ?
                ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'id': row[0],
                    'scraper_name': row[1],
                    'run_time': row[2],
                    'status': row[3],
                    'events_found': row[4],
                    'events_added': row[5],
                    'events_updated': row[6],
                    'response_time_ms': row[7],
                    'error_message': row[8]
                })
            
            conn.close()
            return logs
            
        except Exception as e:
            logger.error(f"Error getting scraper logs: {e}")
            return []
    
    def update_scraper(self, scraper_id: int, data: Dict) -> bool:
        """Update web scraper configuration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build update query dynamically
            update_fields = []
            values = []
            
            for field in ['name', 'description', 'category', 'update_interval', 'is_active']:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    values.append(data[field])
            
            if 'selector_config' in data:
                update_fields.append("selector_config = ?")
                values.append(json.dumps(data['selector_config']))
            
            if update_fields:
                update_fields.append("updated_at = CURRENT_TIMESTAMP")
                values.append(scraper_id)
                
                query = f"UPDATE web_scrapers SET {', '.join(update_fields)} WHERE id = ?"
                cursor.execute(query, values)
                
                conn.commit()
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating web scraper: {e}")
            return False
    
    def delete_scraper(self, scraper_id: int) -> bool:
        """Delete a web scraper"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete related records
            cursor.execute('DELETE FROM web_scraper_logs WHERE scraper_id = ?', (scraper_id,))
            cursor.execute('DELETE FROM web_scraper_events WHERE scraper_id = ?', (scraper_id,))
            cursor.execute('DELETE FROM web_scrapers WHERE id = ?', (scraper_id,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting web scraper: {e}")
            return False
    
    def test_scraper_url(self, url: str, selector_config: Dict = None) -> Dict:
        """Test a scraper URL and configuration"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if this is a JavaScript-heavy page
            scripts = soup.find_all('script')
            has_react = any('react' in str(script).lower() for script in scripts)
            has_vue = any('vue' in str(script).lower() for script in scripts)
            has_angular = any('angular' in str(script).lower() for script in scripts)
            has_spa = any('spa' in str(script).lower() or 'single-page' in str(script).lower() for script in scripts)
            
            is_js_heavy = has_react or has_vue or has_angular or has_spa or '#' in url
            
            if is_js_heavy:
                # Clean the URL to remove fragments and get base domain
                base_url = url.split('#')[0].split('?')[0].rstrip('/')
                if '/calendar-2' in base_url:
                    # Special case for Washingtonian calendar
                    rss_suggestions = [
                        f"{base_url.replace('/calendar-2', '')}/feed/",
                        f"{base_url.replace('/calendar-2', '')}/events/feed/"
                    ]
                else:
                    rss_suggestions = [
                        f"{base_url}/feed/",
                        f"{base_url}/events/feed/",
                        f"{base_url}/rss/"
                    ]
                
                return {
                    'success': False,
                    'message': f"This appears to be a JavaScript-heavy website (SPA). Basic web scraping won't work. Consider using RSS feeds instead.",
                    'events_found': 0,
                    'is_javascript_heavy': True,
                    'rss_suggestions': rss_suggestions,
                    'rss_suggestion': rss_suggestions[0]  # Primary suggestion
                }
            
            if selector_config:
                # Test with provided configuration
                events = self._extract_events(soup, selector_config, url)
                return {
                    'success': True,
                    'message': f"Scraper test successful. Found {len(events)} potential events.",
                    'events_found': len(events),
                    'sample_events': [{'title': e.title, 'description': e.description[:100]} for e in events[:3]]
                }
            else:
                # Test with default configuration
                default_config = {
                    'event_container': '.event, .event-item, [class*="event"]',
                    'title': 'h1, h2, h3, .title, .event-title'
                }
                events = self._extract_events(soup, default_config, url)
                return {
                    'success': True,
                    'message': f"Basic scraper test successful. Found {len(events)} potential events with default selectors.",
                    'events_found': len(events),
                    'sample_events': [{'title': e.title} for e in events[:3]]
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f"Scraper test failed: {str(e)}"
            }

# Scheduler functions
def run_scheduled_scrapers():
    """Run all scrapers that are due for execution"""
    try:
        scraper_manager = WebScraperManager()
        conn = sqlite3.connect(scraper_manager.db_path)
        cursor = conn.cursor()
        
        # Get scrapers that are due for execution
        cursor.execute('''
            SELECT id FROM web_scrapers 
            WHERE is_active = 1 AND next_run <= CURRENT_TIMESTAMP
        ''')
        
        due_scrapers = cursor.fetchall()
        conn.close()
        
        for (scraper_id,) in due_scrapers:
            logger.info(f"Running scheduled scraper {scraper_id}")
            result = scraper_manager.scrape_website(scraper_id)
            logger.info(f"Scraper {scraper_id} result: {result['message']}")
            
    except Exception as e:
        logger.error(f"Error running scheduled scrapers: {e}")

def start_web_scraper_scheduler():
    """Start the web scraper scheduler"""
    try:
        # Schedule scrapers to run every 5 minutes
        schedule.every(5).minutes.do(run_scheduled_scrapers)
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("Web scraper scheduler started successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error starting web scraper scheduler: {e}")
        return False

def get_scraper_scheduler_status():
    """Get the status of the web scraper scheduler"""
    try:
        return {
            'running': True,
            'next_run': 'Every 5 minutes',
            'active_scrapers': len([s for s in WebScraperManager().get_all_scrapers() if s['is_active']])
        }
    except:
        return {
            'running': False,
            'next_run': 'Not running',
            'active_scrapers': 0
        }
