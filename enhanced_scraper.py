"""
Enhanced Web Scraper with Dynamic Content Support
Implements foolproof scraping with multiple strategies and content validation
"""

import json
import re
import time
import random
import html
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import dateutil.parser as date_parser
from typing import List, Dict, Optional, Tuple

class SmartDateParser:
    """Intelligent date parsing with multiple format support"""
    
    def __init__(self):
        self.patterns = [
            # Common date patterns
            r'\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})\b',  # MM/DD/YYYY
            r'\b(\d{2,4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})\b',  # YYYY/MM/DD
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2}),?\s+(\d{2,4})\b',
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})\b',
            # ISO format
            r'\b(\d{4})-(\d{2})-(\d{2})\b',
            # Relative dates
            r'\b(today|tomorrow|tonight)\b',
            r'\b(this|next)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(this|next)\s+(week|weekend|month)\b'
        ]
        
        self.time_patterns = [
            r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b',
            r'\b(\d{1,2}):(\d{2}):(\d{2})\b',
            r'\b(\d{1,2}):(\d{2})\b',
            r'\b(\d{1,2})\s*(AM|PM|am|pm)\b'
        ]
    
    def parse_date_string(self, text: str) -> Optional[datetime]:
        """Extract and parse dates from text with multiple strategies"""
        if not text:
            return None
            
        # Clean the text
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Strategy 1: Handle Brookings-specific malformed dates
        if 'October01' in text or 'September17' in text:
            # Fix malformed dates like "October01202510:00 am EDT"
            brookings_pattern = r'(January|February|March|April|May|June|July|August|September|October|November|December)(\d{2})(\d{4})(\d{1,2}):(\d{2})\s*(am|pm)\s*EDT'
            match = re.search(brookings_pattern, text, re.IGNORECASE)
            if match:
                month, day, year, hour, minute, ampm = match.groups()
                # Format as proper date string
                formatted = f'{month} {int(day)}, {year} {hour}:{minute} {ampm}'
                try:
                    return date_parser.parse(formatted)
                except:
                    pass
        
        # Strategy 2: Look for full date patterns first
        full_date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})'
        match = re.search(full_date_pattern, text, re.IGNORECASE)
        if match:
            day_name, month, day, year = match.groups()
            date_str = f'{month} {day}, {year}'
            
            # Look for time in the same text
            time_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)'
            time_match = re.search(time_pattern, text, re.IGNORECASE)
            if time_match:
                hour, minute, ampm = time_match.groups()
                date_str += f' {hour}:{minute} {ampm}'
            else:
                # Look for time range pattern "10:00 am - 11:00 am"
                time_range_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*\d{1,2}:\d{2}\s*(am|pm)'
                time_range_match = re.search(time_range_pattern, text, re.IGNORECASE)
                if time_range_match:
                    hour, minute, ampm = time_range_match.groups()[:3]
                    date_str += f' {hour}:{minute} {ampm}'
            
            try:
                return date_parser.parse(date_str)
            except:
                pass
        
        # Strategy 3: Use dateutil (handles most formats)
        try:
            return date_parser.parse(text, fuzzy=True)
        except:
            pass
        
        # Strategy 2: Handle relative dates
        relative_date = self._parse_relative_date(text.lower())
        if relative_date:
            return relative_date
        
        # Strategy 3: Regex patterns
        for pattern in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return self._normalize_date_match(match, text)
                except:
                    continue
        
        return None
    
    def _parse_relative_date(self, text: str) -> Optional[datetime]:
        """Parse relative date expressions"""
        now = datetime.now()
        
        if 'today' in text:
            return now
        elif 'tomorrow' in text:
            return now + timedelta(days=1)
        elif 'tonight' in text:
            return now.replace(hour=19, minute=0, second=0, microsecond=0)
        elif 'next week' in text:
            return now + timedelta(weeks=1)
        elif 'this week' in text:
            return now
        
        # Handle "next Monday", "this Friday", etc.
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in weekdays.items():
            if day_name in text:
                days_ahead = day_num - now.weekday()
                if 'next' in text:
                    days_ahead += 7
                elif days_ahead <= 0:  # This week but day has passed
                    days_ahead += 7
                return now + timedelta(days=days_ahead)
        
        return None
    
    def _normalize_date_match(self, match, original_text: str) -> datetime:
        """Convert regex match to datetime object"""
        groups = match.groups()
        
        # Try different date format interpretations
        try:
            # ISO format YYYY-MM-DD
            if len(groups) == 3 and len(groups[0]) == 4:
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                return datetime(year, month, day)
            
            # MM/DD/YYYY or DD/MM/YYYY
            elif len(groups) == 3 and groups[2].isdigit():
                # Guess format based on values
                a, b, year = int(groups[0]), int(groups[1]), int(groups[2])
                if year < 100:
                    year += 2000
                
                # If first number > 12, it's likely DD/MM/YYYY
                if a > 12:
                    return datetime(year, b, a)
                # If second number > 12, it's likely MM/DD/YYYY
                elif b > 12:
                    return datetime(year, a, b)
                else:
                    # Default to MM/DD/YYYY for US sites
                    return datetime(year, a, b)
        except ValueError:
            pass
        
        raise ValueError("Could not parse date")

class EventValidator:
    """Validates and scores extracted event data"""
    
    def __init__(self):
        self.required_fields = ['title']
        self.preferred_fields = ['start_date', 'location', 'description', 'url']
        self.spam_indicators = [
            'viagra', 'casino', 'loan', 'credit', 'bitcoin', 'crypto',
            'investment', 'mlm', 'work from home', 'make money',
            'free trial', 'limited time', 'act now', 'click here'
        ]
        self.min_title_length = 5
        self.max_title_length = 200
    
    def score_event(self, event_data: Dict) -> int:
        """Calculate confidence score (0-100) for extracted event"""
        score = 0
        
        # Title validation (30 points)
        title = event_data.get('title', '').strip()
        if title:
            if self.min_title_length <= len(title) <= self.max_title_length:
                score += 30
            elif len(title) > 0:
                score += 15  # Partial credit
        
        # Date validation (25 points)
        if self._is_valid_future_date(event_data.get('start_date')):
            score += 25
        elif event_data.get('start_date'):
            score += 10  # Has date but may be past
        
        # Location (15 points)
        if event_data.get('location') and len(event_data['location'].strip()) > 0:
            score += 15
        
        # Description (15 points)
        description = event_data.get('description', '').strip()
        if description:
            if len(description) > 50:
                score += 15
            elif len(description) > 10:
                score += 8
        
        # URL (10 points)
        if event_data.get('url') and self._is_valid_url(event_data['url']):
            score += 10
        
        # Additional data (5 points)
        if event_data.get('image'):
            score += 2
        if event_data.get('price') or event_data.get('price_info'):
            score += 2
        if event_data.get('category'):
            score += 1
        
        # Spam detection (deduct points)
        content_lower = f"{title} {description}".lower()
        spam_count = sum(1 for indicator in self.spam_indicators if indicator in content_lower)
        score -= spam_count * 20
        
        # Bonus for structured data
        if event_data.get('_source') == 'structured':
            score += 10
        
        return max(0, min(100, score))
    
    def _is_valid_future_date(self, date_str: str) -> bool:
        """Check if date is valid and in the future (or today)"""
        if not date_str:
            return False
        
        try:
            parser = SmartDateParser()
            event_date = parser.parse_date_string(date_str)
            if event_date:
                # Allow events from today onwards
                return event_date.date() >= datetime.now().date()
        except:
            pass
        
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

class EnhancedWebScraper:
    """Enhanced web scraper with multiple extraction strategies"""
    
    def __init__(self):
        self.date_parser = SmartDateParser()
        self.validator = EventValidator()
        self.session = requests.Session()
        
        # User agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Common event selectors
        self.event_selectors = [
            '.event', '.event-item', '.event-listing', '.event-card',
            '[class*="event"]', '[class*="Event"]',
            '.post', '.article', '.listing', '.card',
            '[data-event]', '[data-type="event"]',
            '.workshop', '.seminar', '.conference', '.meetup'
        ]
        
        # Schema.org selectors
        self.schema_selectors = {
            'Event': '[itemtype*="schema.org/Event"]',
            'SportsEvent': '[itemtype*="schema.org/SportsEvent"]',
            'MusicEvent': '[itemtype*="schema.org/MusicEvent"]',
            'TheaterEvent': '[itemtype*="schema.org/TheaterEvent"]',
            'BusinessEvent': '[itemtype*="schema.org/BusinessEvent"]'
        }
    
    def _clean_text(self, text):
        """Clean and normalize text content"""
        if not text:
            return text
        
        # Step 1: Decode HTML entities
        text = html.unescape(text)
        
        # Step 2: Remove/clean HTML tags if present
        if '<' in text or '&lt;' in text:
            soup = BeautifulSoup(text, 'html.parser')
            text = soup.get_text()
        
        # Step 3: Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Step 4: Fix specific encoding issues
        replacements = {
            '&#8217;': "'",
            '&#8216;': "'", 
            '&#8220;': '"',
            '&#8221;': '"',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&nbsp;': ' ',
            '&quot;': '"'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def _is_valid_title(self, title):
        """Validate if text is a proper event title"""
        if not title or len(title.strip()) < 5:
            return False
        
        title_lower = title.lower().strip()
        
        # Exclude generic/metadata terms
        bad_titles = [
            'event date', 'event type', 'event series', 'events',
            'online only', 'main navigation', 'view details',
            'register now', 'more info', 'event category'
        ]
        
        if title_lower in bad_titles:
            return False
        
        # Check for HTML artifacts
        if '<' in title or '&lt;' in title or '&gt;' in title:
            return False
        
        # Check for obvious location-only titles (without event context)
        location_only_patterns = [
            r'^\d+\w*\s+floor\s*,',  # "1st Floor, ..."
            r'^ground floor\s*,',     # "Ground Floor, ..."
            r'^\w+\s+hall\s*$',      # "Theatre Hall"
            r'^\w+\s+building\s*$'   # "Main Building"
        ]
        
        for pattern in location_only_patterns:
            if re.match(pattern, title_lower):
                return False
        
        return True
    
    def _is_past_event(self, soup):
        """Check if the page indicates this is a past event"""
        text = soup.get_text().lower()
        
        # Look for explicit past event indicators
        past_indicators = [
            'past event',
            'event has ended',
            'this event has concluded',
            'event archive',
            'archived event'
        ]
        
        for indicator in past_indicators:
            if indicator in text:
                return True
        
        # Only check for very old dates (more than 30 days past)
        from datetime import datetime, timedelta
        now = datetime.now()
        cutoff = now - timedelta(days=30)  # Only skip very old events
        
        # Look for date patterns that might indicate very old events
        date_elements = soup.find_all(class_=lambda x: x and 'date' in x.lower() if x else False)
        old_dates_found = 0
        
        for elem in date_elements:
            elem_text = elem.get_text(strip=True)
            try:
                # Try to parse the date
                parsed_date = self.date_parser.parse_date_string(elem_text)
                if parsed_date and parsed_date < cutoff:
                    old_dates_found += 1
            except:
                continue
        
        # Only consider it past if multiple old dates found (not just one metadata date)
        if old_dates_found >= 2:
            return True
        
        return False
    
    def scrape_events(self, url: str, custom_selectors: Dict = None) -> List[Dict]:
        """Main scraping method with multiple strategies"""
        try:
            html_content = self._fetch_page(url)
            if not html_content:
                return []
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check if this is a past event first
            if self._is_past_event(soup):
                print(f"Skipping past event from: {url}")
                return []
            
            # Try multiple extraction strategies
            strategies = [
                ('structured', self._extract_structured_data),
                ('microdata', self._extract_microdata),
                ('css_selectors', self._extract_css_selectors),
                ('meta_tags', self._extract_meta_tags)
            ]
            
            all_events = []
            for strategy_name, strategy_func in strategies:
                try:
                    events = strategy_func(soup, url, custom_selectors)
                    for event in events:
                        event['_source'] = strategy_name
                        event['_url'] = url
                    all_events.extend(events)
                except Exception as e:
                    print(f"Strategy {strategy_name} failed: {e}")
                    continue
            
            # Deduplicate and validate
            unique_events = self._deduplicate_events(all_events)
            validated_events = []
            
            for event in unique_events:
                score = self.validator.score_event(event)
                if score >= 50:  # Minimum confidence threshold
                    event['confidence_score'] = score
                    validated_events.append(event)
            
            # Sort by confidence score
            validated_events.sort(key=lambda x: x['confidence_score'], reverse=True)
            
            return validated_events[:20]  # Limit results
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return []
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch web page with retry logic and anti-bot measures"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        for attempt in range(3):
            try:
                # Add random delay
                if attempt > 0:
                    time.sleep(random.uniform(1, 3))
                
                response = self.session.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                
                return response.text
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise
        
        return None
    
    def _extract_structured_data(self, soup: BeautifulSoup, url: str, custom_selectors: Dict = None) -> List[Dict]:
        """Extract events from JSON-LD structured data"""
        events = []
        
        # Find all JSON-LD scripts
        scripts = soup.find_all('script', type='application/ld+json')
        
        for script in scripts:
            try:
                if not script.string:
                    continue
                
                data = json.loads(script.string)
                
                # Handle single object or list
                if isinstance(data, dict):
                    data = [data]
                elif not isinstance(data, list):
                    continue
                
                for item in data:
                    if self._is_event_data(item):
                        event = self._normalize_structured_event(item, url)
                        if event:
                            events.append(event)
                            
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"Error processing JSON-LD: {e}")
                continue
        
        return events
    
    def _extract_microdata(self, soup: BeautifulSoup, url: str, custom_selectors: Dict = None) -> List[Dict]:
        """Extract events from Schema.org microdata"""
        events = []
        
        for event_type, selector in self.schema_selectors.items():
            containers = soup.select(selector)
            
            for container in containers:
                event = self._extract_microdata_event(container, url)
                if event:
                    events.append(event)
        
        return events
    
    def _extract_css_selectors(self, soup: BeautifulSoup, url: str, custom_selectors: Dict = None) -> List[Dict]:
        """Extract events using CSS selectors"""
        events = []
        
        # Use custom selectors if provided, otherwise use defaults
        selectors = custom_selectors.get('event_container', self.event_selectors) if custom_selectors else self.event_selectors
        
        if isinstance(selectors, str):
            selectors = [selectors]
        
        for selector in selectors:
            containers = soup.select(selector)
            
            for container in containers[:15]:  # Limit to prevent spam
                event = self._extract_from_container(container, url, custom_selectors)
                if event and self._looks_like_event(event):
                    events.append(event)
        
        return events
    
    def _extract_meta_tags(self, soup: BeautifulSoup, url: str, custom_selectors: Dict = None) -> List[Dict]:
        """Extract event info from Open Graph and meta tags"""
        events = []
        
        # Look for Open Graph event data
        og_type = soup.find('meta', property='og:type')
        if og_type and 'event' in og_type.get('content', '').lower():
            event = {}
            
            # Extract OG data
            og_mappings = {
                'og:title': 'title',
                'og:description': 'description',
                'og:url': 'url',
                'og:image': 'image',
                'event:start_time': 'start_date',
                'event:end_time': 'end_date',
                'event:location': 'location'
            }
            
            for og_prop, event_field in og_mappings.items():
                meta_tag = soup.find('meta', property=og_prop)
                if meta_tag and meta_tag.get('content'):
                    event[event_field] = meta_tag['content']
            
            if event.get('title'):
                events.append(event)
        
        return events
    
    def _extract_from_container(self, container: BeautifulSoup, url: str, custom_selectors: Dict = None) -> Optional[Dict]:
        """Extract event data from a container element"""
        event = {}
        
        # Define selectors (custom or default)
        selectors = custom_selectors or {}
        
        # Title extraction
        title_selectors = selectors.get('title', ['h1', 'h2', 'h3', 'h4', '.title', '.event-title', '.name', 'a'])
        title = self._extract_text_by_selectors(container, title_selectors)
        if title:
            # Clean and validate title
            clean_title = self._clean_text(title.strip())
            if self._is_valid_title(clean_title):
                event['title'] = clean_title
            else:
                # Try alternative title extraction
                text_content = container.get_text(strip=True)
                lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                for line in lines[:3]:  # Check first 3 lines
                    clean_line = self._clean_text(line)
                    if self._is_valid_title(clean_line):
                        event['title'] = clean_line
                        break
        
        # Date extraction
        date_selectors = selectors.get('date', ['.date', '.event-date', 'time', '[class*="date"]', '[datetime]'])
        date_text = self._extract_text_by_selectors(container, date_selectors)
        if date_text:
            event['start_date'] = date_text.strip()
        
        # Location extraction
        location_selectors = selectors.get('location', ['.location', '.venue', '.address', '[class*="location"]', '[class*="venue"]'])
        location = self._extract_text_by_selectors(container, location_selectors)
        if location:
            event['location'] = location.strip()
        
        # Description extraction
        desc_selectors = selectors.get('description', ['.description', '.content', '.summary', 'p'])
        description = self._extract_text_by_selectors(container, desc_selectors)
        if description:
            clean_description = self._clean_text(description.strip())
            event['description'] = clean_description[:500]  # Limit length
        
        # URL extraction
        url_elem = container.find('a', href=True)
        if url_elem:
            event['url'] = urljoin(url, url_elem['href'])
        
        # Image extraction
        img_elem = container.find('img', src=True)
        if img_elem:
            event['image'] = urljoin(url, img_elem['src'])
        
        # Price extraction
        price_selectors = selectors.get('price', ['.price', '.cost', '[class*="price"]', '[class*="cost"]'])
        price = self._extract_text_by_selectors(container, price_selectors)
        if price:
            event['price_info'] = price.strip()
        
        return event if event.get('title') else None
    
    def _extract_text_by_selectors(self, container: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract text using multiple CSS selectors"""
        for selector in selectors:
            elem = container.select_one(selector)
            if elem:
                # Try different text extraction methods
                text = elem.get('datetime') or elem.get_text(strip=True)
                if text and len(text.strip()) > 0:
                    return text.strip()
        return None
    
    def _is_event_data(self, data: Dict) -> bool:
        """Check if JSON-LD data represents an event"""
        event_types = ['Event', 'SportsEvent', 'MusicEvent', 'TheaterEvent', 'BusinessEvent', 'EducationEvent']
        data_type = data.get('@type', '')
        return any(event_type in data_type for event_type in event_types)
    
    def _normalize_structured_event(self, data: Dict, url: str) -> Optional[Dict]:
        """Convert structured data to normalized event format"""
        event = {}
        
        # Map structured data fields to our format
        mappings = {
            'name': 'title',
            'description': 'description',
            'startDate': 'start_date',
            'endDate': 'end_date',
            'url': 'url',
            'image': 'image'
        }
        
        for struct_field, event_field in mappings.items():
            value = data.get(struct_field)
            if value:
                if isinstance(value, dict) and '@value' in value:
                    value = value['@value']
                elif isinstance(value, list) and len(value) > 0:
                    value = value[0]
                
                if isinstance(value, str) and value.strip():
                    event[event_field] = value.strip()
        
        # Handle location (can be complex object)
        location = data.get('location')
        if location:
            if isinstance(location, dict):
                location_name = location.get('name') or location.get('address', {}).get('addressLocality')
                if location_name:
                    event['location'] = location_name
            elif isinstance(location, str):
                event['location'] = location
        
        # Handle offers/price
        offers = data.get('offers')
        if offers:
            if isinstance(offers, list) and len(offers) > 0:
                offers = offers[0]
            if isinstance(offers, dict):
                price = offers.get('price') or offers.get('priceSpecification', {}).get('price')
                if price:
                    event['price_info'] = str(price)
        
        return event if event.get('title') else None
    
    def _extract_microdata_event(self, container: BeautifulSoup, url: str) -> Optional[Dict]:
        """Extract event from microdata container"""
        event = {}
        
        # Microdata property mappings
        mappings = {
            'name': 'title',
            'description': 'description',
            'startDate': 'start_date',
            'endDate': 'end_date',
            'url': 'url',
            'image': 'image',
            'location': 'location'
        }
        
        for prop, field in mappings.items():
            elem = container.find(attrs={'itemprop': prop})
            if elem:
                # Get content from different attributes/text
                value = elem.get('content') or elem.get('datetime') or elem.get_text(strip=True)
                if value:
                    event[field] = value.strip()
        
        return event if event.get('title') else None
    
    def _looks_like_event(self, event: Dict) -> bool:
        """Basic heuristic to determine if extracted data looks like an event"""
        title = event.get('title', '').lower()
        
        # Check for event-related keywords
        event_keywords = [
            'event', 'workshop', 'seminar', 'conference', 'meetup', 'webinar',
            'concert', 'show', 'performance', 'festival', 'competition',
            'training', 'class', 'session', 'presentation', 'talk'
        ]
        
        # Title should have some substance
        if len(title) < 5 or len(title) > 200:
            return False
        
        # Bonus if it has event keywords or date
        has_keywords = any(keyword in title for keyword in event_keywords)
        has_date = bool(event.get('start_date'))
        
        return has_keywords or has_date or len(title.split()) >= 3
    
    def _deduplicate_events(self, events: List[Dict]) -> List[Dict]:
        """Remove duplicate events based on title and date"""
        seen = set()
        unique_events = []
        
        for event in events:
            # Create a simple key for deduplication
            key = (
                event.get('title', '').lower().strip()[:50],
                event.get('start_date', '')[:10]  # Just the date part
            )
            
            if key not in seen and key[0]:  # Must have a title
                seen.add(key)
                unique_events.append(event)
        
        return unique_events

# Usage example:
if __name__ == "__main__":
    scraper = EnhancedWebScraper()
    
    # Test with a sample URL
    test_url = "https://www.eventbrite.com/d/dc--washington/events/"
    events = scraper.scrape_events(test_url)
    
    print(f"Found {len(events)} events:")
    for event in events[:5]:  # Show first 5
        print(f"- {event.get('title')} (Score: {event.get('confidence_score')})")
        print(f"  Date: {event.get('start_date')}")
        print(f"  Location: {event.get('location')}")
        print()
