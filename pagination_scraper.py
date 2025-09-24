"""
Enhanced scraper for handling pagination and comprehensive event capture
Specifically designed for Smithsonian Natural History Museum events
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import sqlite3

class PaginationAwareScraper:
    """Scraper that can handle paginated content and JavaScript-loaded events"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
    
    def setup_session(self):
        """Setup session with realistic headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def scrape_natural_history_comprehensive(self):
        """
        Scrape ALL Natural History Museum events using multiple strategies
        Target: 26 events (Sep:5, Oct:17, Nov:1, Dec:3)
        """
        base_url = 'https://naturalhistory.si.edu/events'
        all_events = []
        
        print(f'🔍 Comprehensive Natural History Museum scraping...')
        
        # Strategy 1: Check for AJAX/API endpoints
        api_events = self._check_for_api_endpoints(base_url)
        if api_events:
            print(f'   ✅ API Strategy: {len(api_events)} events found')
            all_events.extend(api_events)
        
        # Strategy 2: Parse the main page for all event data
        page_events = self._parse_main_page_comprehensive(base_url)
        if page_events:
            print(f'   ✅ Main Page Strategy: {len(page_events)} events found')
            all_events.extend(page_events)
        
        # Strategy 3: Check for calendar data in JavaScript
        js_events = self._extract_javascript_events(base_url)
        if js_events:
            print(f'   ✅ JavaScript Strategy: {len(js_events)} events found')
            all_events.extend(js_events)
        
        # Remove duplicates
        unique_events = self._deduplicate_events(all_events)
        
        print(f'   📊 Total unique events: {len(unique_events)}')
        return unique_events
    
    def _check_for_api_endpoints(self, base_url):
        """Check for API endpoints that might contain event data"""
        api_endpoints = [
            '/api/events',
            '/events/api',
            '/events.json',
            '/calendar/data',
            '/events/data'
        ]
        
        domain = base_url.split('/events')[0]
        
        for endpoint in api_endpoints:
            try:
                api_url = domain + endpoint
                response = self.session.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 10:
                            return self._parse_api_events(data)
                    except:
                        pass
            except:
                continue
        
        return []
    
    def _parse_main_page_comprehensive(self, url):
        """Parse the main page more thoroughly to extract all event information"""
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            events = []
            
            # Look for event containers with various selectors
            event_selectors = [
                '[class*="event"]',
                '[data-event]',
                '.program',
                '.activity',
                'article',
                '[id*="event"]'
            ]
            
            for selector in event_selectors:
                elements = soup.select(selector)
                
                for element in elements:
                    event_data = self._extract_event_from_element(element)
                    if event_data and self._is_valid_event(event_data):
                        events.append(event_data)
            
            # Also look for structured data (JSON-LD)
            json_ld_events = self._extract_json_ld_events(soup)
            events.extend(json_ld_events)
            
            return events
            
        except Exception as e:
            print(f'   ❌ Main page parsing error: {e}')
            return []
    
    def _extract_javascript_events(self, url):
        """Extract event data from JavaScript variables or AJAX calls"""
        try:
            response = self.session.get(url, timeout=15)
            content = response.text
            
            # Look for common JavaScript patterns that contain event data
            js_patterns = [
                r'var events = (\\[.*?\\]);',
                r'window\\.events = (\\[.*?\\]);',
                r'"events":\\s*(\\[.*?\\])',
                r'eventData = (\\[.*?\\]);'
            ]
            
            import re
            
            for pattern in js_patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                for match in matches:
                    try:
                        events_data = json.loads(match)
                        if isinstance(events_data, list) and len(events_data) > 5:
                            return self._parse_js_events(events_data)
                    except:
                        continue
            
            return []
            
        except Exception as e:
            print(f'   ❌ JavaScript extraction error: {e}')
            return []
    
    def _extract_event_from_element(self, element):
        """Extract event information from a DOM element"""
        try:
            # Extract title - be much more specific about what constitutes an event title
            title = ''
            
            # Strategy 1: Look for actual event names (not locations or dates)
            text_content = element.get_text(strip=True)
            
            # Split into lines and find the actual event title
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            
            for line in lines:
                # Skip obviously non-title content
                if self._is_likely_event_title(line):
                    title = line
                    break
            
            # Strategy 2: If no good title found, try HTML selectors
            if not title:
                title_selectors = ['h1', 'h2', 'h3', '.event-title', '[data-title]']
                for selector in title_selectors:
                    title_elem = element.select_one(selector)
                    if title_elem:
                        candidate_title = title_elem.get_text(strip=True)
                        if self._is_likely_event_title(candidate_title):
                            title = candidate_title
                            break
            
            # Strategy 3: Fallback - use first meaningful text but validate it
            if not title and text_content:
                first_line = lines[0] if lines else text_content[:100]
                if self._is_likely_event_title(first_line):
                    title = first_line
                else:
                    # Last resort - use text but mark as low confidence
                    title = first_line[:80] + "..." if len(first_line) > 80 else first_line
            
            # Extract date
            date_selectors = ['.date', '[class*="date"]', 'time', '[datetime]']
            date = ''
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
            
            # Extract location
            location_selectors = ['.location', '[class*="location"]', '.venue']
            location = ''
            for selector in location_selectors:
                loc_elem = element.select_one(selector)
                if loc_elem:
                    location = loc_elem.get_text(strip=True)
                    break
            
            if not location:
                location = 'Natural History Museum'
            
            # Extract description
            desc_selectors = ['.description', 'p', '.summary']
            description = ''
            for selector in desc_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem and len(desc_elem.get_text(strip=True)) > 20:
                    description = desc_elem.get_text(strip=True)
                    break
            
            return {
                'title': title,
                'start_date': date,
                'location': location,
                'description': description,
                'confidence_score': 85
            }
            
        except Exception as e:
            return None
    
    def _is_valid_event(self, event_data):
        """Validate if the extracted data represents a real event"""
        if not event_data.get('title') or len(event_data['title']) < 5:
            return False
        
        # Check for common false positives
        false_positives = ['navigation', 'menu', 'header', 'footer', 'cookie', 'privacy']
        title_lower = event_data['title'].lower()
        
        for fp in false_positives:
            if fp in title_lower:
                return False
        
        return True
    
    def _extract_json_ld_events(self, soup):
        """Extract events from JSON-LD structured data"""
        events = []
        
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)
                
                if isinstance(data, dict) and data.get('@type') == 'Event':
                    events.append(self._parse_json_ld_event(data))
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') == 'Event':
                            events.append(self._parse_json_ld_event(item))
                            
            except:
                continue
        
        return events
    
    def _parse_json_ld_event(self, data):
        """Parse a single JSON-LD event"""
        return {
            'title': data.get('name', ''),
            'start_date': data.get('startDate', ''),
            'location': data.get('location', {}).get('name', 'Natural History Museum'),
            'description': data.get('description', ''),
            'confidence_score': 95
        }
    
    def _parse_api_events(self, events_data):
        """Parse events from API response"""
        events = []
        
        for event in events_data:
            if isinstance(event, dict):
                events.append({
                    'title': event.get('title', event.get('name', '')),
                    'start_date': event.get('start_date', event.get('date', '')),
                    'location': event.get('location', 'Natural History Museum'),
                    'description': event.get('description', ''),
                    'confidence_score': 90
                })
        
        return events
    
    def _parse_js_events(self, events_data):
        """Parse events from JavaScript data"""
        return self._parse_api_events(events_data)
    
    def _deduplicate_events(self, events):
        """Remove duplicate events based on title and date"""
        seen = set()
        unique_events = []
        
        for event in events:
            key = (event.get('title', '').lower(), event.get('start_date', ''))
            if key not in seen and event.get('title'):
                seen.add(key)
                unique_events.append(event)
        
        return unique_events
    
    def _is_likely_event_title(self, text):
        """Determine if text is likely to be an actual event title"""
        if not text or len(text) < 5:
            return False
        
        text_lower = text.lower()
        
        # Exclude obvious non-titles
        exclusions = [
            # Location patterns
            'floor', 'hall', 'theater', 'gallery', 'center', 'building', 'room',
            # Date patterns  
            '2025', '2024', '2026', 'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'am', 'pm', 'edt', 'est', 'pdt', 'pst',
            # Metadata patterns
            'event date', 'event type', 'event series', 'event category',
            # Navigation patterns
            'view details', 'more info', 'register', 'tickets'
        ]
        
        # If text contains any exclusion patterns, it's probably not a title
        for exclusion in exclusions:
            if exclusion in text_lower:
                return False
        
        # Positive indicators of event titles
        positive_indicators = [
            # Event type words
            'tour', 'talk', 'lecture', 'workshop', 'class', 'program', 'exhibition',
            'performance', 'concert', 'show', 'festival', 'conference', 'seminar',
            'demonstration', 'presentation', 'screening', 'discussion',
            # Natural History specific
            'play date', 'story time', 'fossil', 'ocean', 'science', 'discovery',
            'animals', 'nature', 'dinosaur', 'mammal', 'marine', 'coral',
            # Action words
            'exploring', 'discovering', 'learning', 'experience', 'adventure',
            # Event names often have colons
            ':'
        ]
        
        # Check for positive indicators
        has_positive = any(indicator in text_lower for indicator in positive_indicators)
        
        # Title-like characteristics
        has_title_case = any(word[0].isupper() for word in text.split() if word)
        reasonable_length = 10 <= len(text) <= 100
        not_all_caps = text != text.upper()
        
        # Combine criteria
        return has_positive and has_title_case and reasonable_length and not_all_caps

def update_natural_history_scraper():
    """Update the Natural History scraper with comprehensive capture"""
    print('🚀 UPDATING NATURAL HISTORY FOR COMPREHENSIVE CAPTURE')
    print('=' * 60)
    
    scraper = PaginationAwareScraper()
    events = scraper.scrape_natural_history_comprehensive()
    
    print(f'\\n📊 COMPREHENSIVE SCRAPING RESULTS:')
    print(f'   Total events found: {len(events)}')
    
    if events:
        # Count by month
        months = {'Sep': 0, 'Oct': 0, 'Nov': 0, 'Dec': 0}
        
        for event in events:
            date = event.get('start_date', '')
            if any(x in date.lower() for x in ['september', '2025-09', 'sep']):
                months['Sep'] += 1
            elif any(x in date.lower() for x in ['october', '2025-10', 'oct']):
                months['Oct'] += 1
            elif any(x in date.lower() for x in ['november', '2025-11', 'nov']):
                months['Nov'] += 1
            elif any(x in date.lower() for x in ['december', '2025-12', 'dec']):
                months['Dec'] += 1
        
        print(f'\\n📅 MONTHLY BREAKDOWN:')
        for month, count in months.items():
            if count > 0:
                print(f'   {month}: {count} events')
        
        total_months = sum(months.values())
        print(f'   Total with dates: {total_months}')
        
        expected = {'Sep': 5, 'Oct': 17, 'Nov': 1, 'Dec': 3}
        print(f'\\n🎯 COMPARISON TO EXPECTED:')
        for month, expected_count in expected.items():
            found_count = months[month]
            status = '✅' if found_count >= expected_count else '❌'
            print(f'   {month}: Expected {expected_count}, Found {found_count} {status}')
        
        # Show sample events
        print(f'\\n📋 SAMPLE EVENTS:')
        for i, event in enumerate(events[:5]):
            title = event.get('title', 'Unknown')[:50]
            date = event.get('start_date', 'No date')
            conf = event.get('confidence_score', 0)
            print(f'   {i+1}. {title}... | {date} | {conf}%')
    
    return events

if __name__ == '__main__':
    events = update_natural_history_scraper()
