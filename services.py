"""
Simplified business logic services for the calendar application
"""

import re
import json
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from models import Database, EventModel, CategoryModel, RSSFeedModel

class EventParser:
    """Simplified event parser using regex patterns"""
    
    def __init__(self):
        # Common date patterns
        self.date_patterns = [
            r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        
        # Time patterns
        self.time_patterns = [
            r'\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b',
            r'\b\d{1,2}\s*(?:AM|PM|am|pm)\b',
            r'\b(?:at|from|starting)\s+\d{1,2}(?::\d{2})?\s*(?:AM|PM|am|pm)\b'
        ]
        
        # Location patterns
        self.location_patterns = [
            r'\b(at|in|@)\s+[A-Z][A-Za-z\s&\',\-\.]+(?:Center|Theater|Theatre|Museum|Library|Park|Hall|Arena|Stadium|Club|Bar|Restaurant|Cafe|Gallery|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue)\b',
            r'\b\d+\s+[A-Za-z\s,.-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct|NW|NE|SW|SE)\b'
        ]
        
        # Price patterns
        self.price_patterns = [
            r'\$\d+(?:\.\d{2})?',
            r'\b(?:free|Free|FREE)\b',
            r'\b\d+\s*dollars?\b'
        ]
    
    def parse_natural_language(self, text: str) -> Dict:
        """Parse natural language text to extract event information"""
        result = {
            'title': '',
            'date': '',
            'time': '',
            'location': '',
            'description': text,
            'price_info': 'Free'
        }
        
        # Extract title (first line or sentence)
        lines = text.strip().split('\n')
        if lines:
            first_line = lines[0].strip()
            if len(first_line) > 5 and len(first_line) < 100:
                result['title'] = first_line
        
        # Extract date
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['date'] = match.group()
                break
        
        # Extract time
        for pattern in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['time'] = match.group()
                break
        
        # Extract location
        for pattern in self.location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['location'] = match.group()
                break
        
        # Extract price
        for pattern in self.price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['price_info'] = match.group()
                break
        
        return result
    
    def extract_multiple_events(self, text: str) -> List[Dict]:
        """Extract multiple events from bulk text"""
        events = []
        
        # Split by common separators
        event_blocks = re.split(r'\n\s*\n|\n(?=[A-Z][a-z])', text)
        
        for block in event_blocks:
            block = block.strip()
            if len(block) > 50:  # Only process substantial blocks
                parsed_event = self.parse_natural_language(block)
                if parsed_event.get('title'):
                    events.append(parsed_event)
        
        return events

class RSSService:
    """Simplified RSS feed service"""
    
    def __init__(self, event_model: EventModel):
        self.event_model = event_model
    
    def parse_rss_feed(self, feed_url: str) -> List[Dict]:
        """Parse RSS feed and extract events"""
        try:
            feed = feedparser.parse(feed_url)
            events = []
            
            for entry in feed.entries:
                event_data = {
                    'title': entry.get('title', ''),
                    'description': entry.get('description', ''),
                    'url': entry.get('link', ''),
                    'source': 'rss'
                }
                
                # Try to extract date from published or updated
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    event_data['start_datetime'] = datetime(*entry.published_parsed[:6]).isoformat()
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    event_data['start_datetime'] = datetime(*entry.updated_parsed[:6]).isoformat()
                else:
                    event_data['start_datetime'] = datetime.now().isoformat()
                
                events.append(event_data)
            
            return events
            
        except Exception as e:
            print(f"Error parsing RSS feed {feed_url}: {e}")
            return []
    
    def _detect_event_type(self, event_data: Dict) -> str:
        """Automatically detect event type based on content"""
        title = event_data.get('title', '').lower()
        description = event_data.get('description', '').lower()
        location = event_data.get('location_name', '').lower()
        url = event_data.get('url', '').lower()
        
        # Combine all text for analysis
        all_text = f"{title} {description} {location} {url}"
        
        # Online indicators
        online_keywords = [
            'zoom', 'virtual', 'online', 'webinar', 'livestream', 'remote',
            'digital', 'via zoom', 'video conference', 'join us online',
            'live stream', 'watch online', 'virtual event', 'online only'
        ]
        
        # In-person indicators  
        in_person_keywords = [
            'museum', 'library', 'theater', 'auditorium', 'hall', 'building',
            'room', 'floor', 'address', 'parking', 'venue', 'location',
            'in person', 'attend in person', 'physical location'
        ]
        
        # Hybrid indicators
        hybrid_keywords = [
            'hybrid', 'both online and in person', 'virtual and in person',
            'attend virtually or in person', 'zoom and in person'
        ]
        
        # Check for hybrid first (most specific)
        if any(keyword in all_text for keyword in hybrid_keywords):
            return 'hybrid'
        
        # Check online indicators
        online_score = sum(1 for keyword in online_keywords if keyword in all_text)
        
        # Check in-person indicators
        in_person_score = sum(1 for keyword in in_person_keywords if keyword in all_text)
        
        # Additional logic
        has_physical_location = location and location not in ['virtual', 'online', '']
        has_url_meeting = 'zoom' in url or 'meet' in url or 'webinar' in url
        
        if has_url_meeting or online_score >= 2:
            return 'online'
        elif has_physical_location or in_person_score >= 2:
            return 'in-person' 
        elif online_score > 0:
            return 'online'
        elif in_person_score > 0:
            return 'in-person'
        else:
            return 'unknown'
    
    def refresh_all_feeds(self, rss_model: RSSFeedModel) -> Dict:
        """Refresh all enabled RSS feeds"""
        feeds = rss_model.get_all_feeds()
        enabled_feeds = [feed for feed in feeds if feed['is_active']]
        
        total_events = 0
        successful_feeds = 0
        failed_feeds = 0
        
        for feed in enabled_feeds:
            try:
                events = self.parse_rss_feed(feed['url'])
                
                for event_data in events:
                    # Check if event already exists
                    existing_events = self.event_model.search_events(event_data['title'])
                    if not existing_events:
                        # Ensure RSS events require approval
                        event_data['source'] = 'rss'
                        event_data['approval_status'] = 'pending'
                        
                        # Auto-detect event type
                        event_data['event_type'] = self._detect_event_type(event_data)
                        
                        self.event_model.create_event(event_data)
                        total_events += 1
                
                # Update last checked time
                rss_model.update_feed_status(feed['id'], True)
                successful_feeds += 1
                
            except Exception as e:
                print(f"Error refreshing feed {feed['name']}: {e}")
                failed_feeds += 1
        
        return {
            'total_events': total_events,
            'successful_feeds': successful_feeds,
            'failed_feeds': failed_feeds,
            'total_feeds': len(enabled_feeds)
        }

class EventService:
    """Main event service combining all operations"""
    
    def __init__(self, db_path: str = "calendar.db"):
        self.db = Database(db_path)
        self.event_model = EventModel(self.db)
        self.category_model = CategoryModel(self.db)
        self.rss_model = RSSFeedModel(self.db)
        self.parser = EventParser()
        self.rss_service = RSSService(self.event_model)
    
    def get_events(self, date: Optional[str] = None, month: Optional[str] = None, year: Optional[str] = None, approved_only: bool = True) -> List[Dict]:
        """Get events with optional filtering"""
        if date:
            return self.event_model.get_events_by_date(date, approved_only=approved_only)
        elif month and year:
            return self.event_model.get_events_by_month(month, year, approved_only=approved_only)
        else:
            return self.event_model.get_all_events(approved_only=approved_only)
    
    def search_events(self, query: str) -> List[Dict]:
        """Search events"""
        return self.event_model.search_events(query)
    
    def create_event(self, event_data: Dict) -> int:
        """Create a new event"""
        return self.event_model.create_event(event_data)
    
    def update_event(self, event_id: int, event_data: Dict) -> bool:
        """Update an event"""
        return self.event_model.update_event(event_id, event_data)
    
    def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        return self.event_model.delete_event(event_id)
    
    def bulk_delete_events(self, event_ids: List[int]) -> int:
        """Delete multiple events"""
        return self.event_model.bulk_delete_events(event_ids)
    
    def parse_event_text(self, text: str) -> Dict:
        """Parse natural language event text"""
        return self.parser.parse_natural_language(text)
    
    def extract_events_from_text(self, text: str) -> List[Dict]:
        """Extract multiple events from text"""
        return self.parser.extract_multiple_events(text)
    
    def get_categories(self) -> List[Dict]:
        """Get all categories"""
        return self.category_model.get_all_categories()
    
    def get_rss_feeds(self) -> List[Dict]:
        """Get all RSS feeds"""
        return self.rss_model.get_all_feeds()
    
    def add_rss_feed(self, name: str, url: str, description: str = "") -> int:
        """Add a new RSS feed"""
        return self.rss_model.create_feed(name, url, description)
    
    def delete_rss_feed(self, feed_id: int) -> bool:
        """Delete an RSS feed"""
        return self.rss_model.delete_feed(feed_id)
    
    def refresh_rss_feeds(self) -> Dict:
        """Refresh all RSS feeds"""
        return self.rss_service.refresh_all_feeds(self.rss_model)
    
    def get_stats(self) -> Dict:
        """Get basic statistics"""
        events = self.event_model.get_all_events()
        categories = self.category_model.get_all_categories()
        feeds = self.rss_model.get_all_feeds()
        
        # Count events by category
        category_counts = {}
        for event in events:
            cat_name = event.get('category_name') or 'Uncategorized'
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        return {
            'total_events': len(events),
            'total_categories': len(categories),
            'total_feeds': len(feeds),
            'events_by_category': category_counts
        }
    
    # Event Approval Methods
    def get_pending_events(self) -> List[Dict]:
        """Get all events pending approval"""
        return self.event_model.get_pending_events()
    
    def approve_event(self, event_id: int, admin_user_id: int) -> bool:
        """Approve a specific event"""
        return self.event_model.approve_event(event_id, admin_user_id)
    
    def reject_event(self, event_id: int, reason: str, admin_user_id: int) -> bool:
        """Reject a specific event"""
        return self.event_model.reject_event(event_id, reason, admin_user_id)
    
    def bulk_approve_events(self, event_ids: List[int], admin_user_id: int) -> int:
        """Bulk approve multiple events"""
        approved_count = 0
        for event_id in event_ids:
            if self.event_model.approve_event(event_id, admin_user_id):
                approved_count += 1
        return approved_count
    
    def bulk_reject_events(self, event_ids: List[int], reason: str, admin_user_id: int) -> int:
        """Bulk reject multiple events"""
        rejected_count = 0
        for event_id in event_ids:
            if self.event_model.reject_event(event_id, reason, admin_user_id):
                rejected_count += 1
        return rejected_count
