#!/usr/bin/env python3
"""
Advanced Web Scraper for Various Website Types
Handles static HTML, JavaScript-heavy sites, and various event formats
"""

import requests
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import re
from datetime import datetime, timedelta
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ScrapedEvent:
    title: str
    description: str = ""
    start_datetime: str = ""
    location_name: str = ""
    price: str = ""
    url: str = ""
    source: str = ""

class AdvancedWebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Common event patterns for different website types
        self.event_patterns = {
            'eventbrite': {
                'containers': ['.event-card', '.event-tile', '[data-testid*="event"]'],
                'title': ['h3', '.event-title', '[data-testid*="title"]'],
                'date': ['.event-date', '.date-time', '[data-testid*="date"]'],
                'location': ['.event-location', '.venue', '[data-testid*="location"]'],
                'price': ['.price', '.ticket-price', '[data-testid*="price"]']
            },
            'meetup': {
                'containers': ['.eventCard', '.event-item', '[data-event-id]'],
                'title': ['h3', '.event-title', 'a[href*="/events/"]'],
                'date': ['.event-date', '.dateTime', '.event-time'],
                'location': ['.event-location', '.venue', '.location'],
                'price': ['.price', '.cost']
            },
            'facebook': {
                'containers': ['[data-testid*="event"]', '.event-item', '[role="article"]'],
                'title': ['h3', '.event-title', '[data-testid*="title"]'],
                'date': ['.event-date', '.date-time', '[data-testid*="date"]'],
                'location': ['.event-location', '.venue', '[data-testid*="location"]'],
                'price': ['.price', '.ticket-price']
            },
            'generic': {
                'containers': [
                    '.event', '.event-item', '.event-card', '.event-tile',
                    'article', '.listing', '.post', '.entry',
                    '[class*="event"]', '[data-event]', '[id*="event"]',
                    '.calendar-event', '.upcoming-event', '.event-list-item'
                ],
                'title': [
                    'h1', 'h2', 'h3', 'h4', '.title', '.event-title', '.event-name',
                    '.event-heading', '.event-header', '[class*="title"]'
                ],
                'date': [
                    '.date', '.event-date', '.event-time', 'time', '.datetime',
                    '[class*="date"]', '[class*="time"]', '.when', '.event-when'
                ],
                'location': [
                    '.location', '.venue', '.event-location', '.address',
                    '[class*="location"]', '[class*="venue"]', '.where', '.event-where'
                ],
                'price': [
                    '.price', '.cost', '.ticket-price', '.event-price',
                    '[class*="price"]', '[class*="cost"]', '.ticket', '.fee'
                ]
            }
        }
        
        # Date parsing patterns
        self.date_patterns = [
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # "September 19, 2025"
            r'(\d{1,2})/(\d{1,2})/(\d{4})',    # "09/19/2025"
            r'(\d{1,2})-(\d{1,2})-(\d{4})',    # "09-19-2025"
            r'(\w+)\s+(\d{1,2})',              # "September 19"
            r'(\d{1,2}):(\d{2})\s*(AM|PM)',    # "7:00 PM"
        ]
        
        # Time patterns
        self.time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(AM|PM)',    # "7:00 PM"
            r'(\d{1,2})\s*(AM|PM)',            # "7 PM"
            r'(\d{1,2}):(\d{2})',              # "19:00"
        ]

    def detect_website_type(self, url: str, soup: BeautifulSoup) -> str:
        """Detect the type of website based on URL and content"""
        domain = urlparse(url).netloc.lower()
        
        if 'eventbrite' in domain:
            return 'eventbrite'
        elif 'meetup' in domain:
            return 'meetup'
        elif 'facebook' in domain:
            return 'facebook'
        elif 'eventful' in domain:
            return 'eventful'
        else:
            return 'generic'

    def get_page_content(self, url: str, timeout: int = 30) -> Tuple[bool, str, BeautifulSoup]:
        """Get page content with multiple strategies"""
        strategies = [
            self._fetch_with_requests,
            self._fetch_with_retries,
            self._fetch_with_different_headers
        ]
        
        for strategy in strategies:
            try:
                success, content, soup = strategy(url, timeout)
                if success:
                    return True, content, soup
            except Exception as e:
                logger.warning(f"Strategy failed: {e}")
                continue
        
        return False, "", BeautifulSoup("", 'html.parser')

    def _fetch_with_requests(self, url: str, timeout: int) -> Tuple[bool, str, BeautifulSoup]:
        """Standard requests fetch"""
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return True, response.text, soup

    def _fetch_with_retries(self, url: str, timeout: int) -> Tuple[bool, str, BeautifulSoup]:
        """Fetch with retries and backoff"""
        for attempt in range(3):
            try:
                time.sleep(attempt * 2)  # Exponential backoff
                response = self.session.get(url, timeout=timeout)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                return True, response.text, soup
            except Exception as e:
                logger.warning(f"Retry {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise
        return False, "", BeautifulSoup("", 'html.parser')

    def _fetch_with_different_headers(self, url: str, timeout: int) -> Tuple[bool, str, BeautifulSoup]:
        """Fetch with different user agent"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        return True, response.text, soup

    def extract_events(self, url: str, custom_selectors: Dict = None) -> List[ScrapedEvent]:
        """Extract events from a website using multiple strategies"""
        logger.info(f"Starting event extraction from: {url}")
        
        # Get page content
        success, content, soup = self.get_page_content(url)
        if not success:
            logger.error(f"Failed to fetch content from {url}")
            return []
        
        # Detect website type
        website_type = self.detect_website_type(url, soup)
        logger.info(f"Detected website type: {website_type}")
        
        # Get selectors for this website type
        selectors = self.event_patterns.get(website_type, self.event_patterns['generic'])
        if custom_selectors:
            selectors = {**selectors, **custom_selectors}
        
        # Extract events using multiple strategies
        events = []
        
        # Strategy 1: Use detected selectors
        events.extend(self._extract_with_selectors(soup, selectors, url))
        
        # Strategy 2: If no events found, try generic patterns
        if not events:
            logger.info("No events found with specific selectors, trying generic patterns")
            events.extend(self._extract_with_generic_patterns(soup, url))
        
        # Strategy 3: If still no events, try content analysis
        if not events:
            logger.info("No events found with generic patterns, trying content analysis")
            events.extend(self._extract_with_content_analysis(soup, url))
        
        logger.info(f"Extracted {len(events)} events from {url}")
        return events

    def _extract_with_selectors(self, soup: BeautifulSoup, selectors: Dict, base_url: str) -> List[ScrapedEvent]:
        """Extract events using specific CSS selectors"""
        events = []
        
        # Find event containers
        containers = []
        for selector in selectors['containers']:
            try:
                found = soup.select(selector)
                if found:
                    containers.extend(found)
                    logger.info(f"Found {len(found)} containers with selector: {selector}")
            except Exception as e:
                logger.warning(f"Error with selector '{selector}': {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_containers = []
        for container in containers:
            container_id = id(container)
            if container_id not in seen:
                seen.add(container_id)
                unique_containers.append(container)
        
        logger.info(f"Processing {len(unique_containers)} unique containers")
        
        for i, container in enumerate(unique_containers):
            try:
                event = self._extract_event_from_container(container, selectors, base_url, i)
                if event and event.title and event.title.strip():
                    events.append(event)
            except Exception as e:
                logger.warning(f"Error extracting event from container {i}: {e}")
        
        return events

    def _extract_event_from_container(self, container, selectors: Dict, base_url: str, index: int) -> Optional[ScrapedEvent]:
        """Extract a single event from a container"""
        event = ScrapedEvent(title="", source=base_url)
        
        # Extract title
        event.title = self._extract_text_with_selectors(container, selectors['title'], f"Event {index + 1}")
        
        # Extract description
        event.description = self._extract_text_with_selectors(container, selectors.get('description', []), "")
        
        # Extract date and time
        date_text = self._extract_text_with_selectors(container, selectors['date'], "")
        time_text = self._extract_text_with_selectors(container, selectors.get('time', []), "")
        event.start_datetime = self._parse_datetime(date_text, time_text)
        
        # Extract location
        event.location_name = self._extract_text_with_selectors(container, selectors['location'], "")
        
        # Extract price
        event.price = self._extract_text_with_selectors(container, selectors['price'], "")
        
        # Extract URL
        event.url = self._extract_url_from_container(container, base_url)
        
        return event

    def _extract_text_with_selectors(self, container, selectors: List[str], default: str = "") -> str:
        """Extract text using multiple selectors"""
        for selector in selectors:
            try:
                element = container.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text:
                        return text
            except Exception as e:
                logger.debug(f"Error with selector '{selector}': {e}")
        return default

    def _extract_url_from_container(self, container, base_url: str) -> str:
        """Extract URL from container"""
        try:
            # Look for links
            link = container.select_one('a[href]')
            if link:
                href = link.get('href')
                if href:
                    return urljoin(base_url, href)
            
            # Look for data attributes
            for attr in ['data-url', 'data-href', 'data-link']:
                url = container.get(attr)
                if url:
                    return urljoin(base_url, url)
        except Exception as e:
            logger.debug(f"Error extracting URL: {e}")
        
        return base_url

    def _extract_with_generic_patterns(self, soup: BeautifulSoup, base_url: str) -> List[ScrapedEvent]:
        """Extract events using generic patterns when specific selectors fail"""
        events = []
        
        # Look for any elements that might contain event information
        potential_containers = soup.find_all(['div', 'article', 'section', 'li'], limit=50)
        
        for container in potential_containers:
            if self._looks_like_event_container(container):
                try:
                    event = self._extract_event_generically(container, base_url)
                    if event and event.title:
                        events.append(event)
                except Exception as e:
                    logger.debug(f"Error in generic extraction: {e}")
        
        return events

    def _looks_like_event_container(self, element) -> bool:
        """Check if an element looks like it contains event information"""
        try:
            text = element.get_text(strip=True).lower()
            
            # Must have reasonable amount of text
            if len(text) < 20:
                return False
            
            # Look for event-related keywords
            event_keywords = [
                'event', 'date', 'time', 'location', 'venue', 'ticket', 'price',
                'upcoming', 'calendar', 'schedule', 'meeting', 'conference',
                'workshop', 'seminar', 'concert', 'show', 'performance'
            ]
            
            keyword_count = sum(1 for keyword in event_keywords if keyword in text)
            
            # Must have at least 2 event-related keywords
            return keyword_count >= 2
            
        except Exception:
            return False

    def _extract_event_generically(self, container, base_url: str) -> Optional[ScrapedEvent]:
        """Extract event information generically from a container"""
        event = ScrapedEvent(title="", source=base_url)
        
        # Try to find title in headings
        for tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            title_elem = container.find(tag)
            if title_elem:
                event.title = title_elem.get_text(strip=True)
                break
        
        # If no title found, use first significant text
        if not event.title:
            text_elements = container.find_all(['p', 'span', 'div'], limit=5)
            for elem in text_elements:
                text = elem.get_text(strip=True)
                if len(text) > 10 and len(text) < 100:
                    event.title = text
                    break
        
        # Extract other information
        event.description = self._extract_description_generically(container)
        event.start_datetime = self._extract_datetime_generically(container)
        event.location_name = self._extract_location_generically(container)
        event.price = self._extract_price_generically(container)
        event.url = self._extract_url_from_container(container, base_url)
        
        return event

    def _extract_description_generically(self, container) -> str:
        """Extract description generically"""
        # Look for paragraphs or divs with substantial text
        for elem in container.find_all(['p', 'div', 'span']):
            text = elem.get_text(strip=True)
            if 50 <= len(text) <= 500:  # Reasonable description length
                return text
        return ""

    def _extract_datetime_generically(self, container) -> str:
        """Extract date/time generically"""
        text = container.get_text()
        
        # Look for date patterns
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        # Look for time patterns
        for pattern in self.time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""

    def _extract_location_generically(self, container) -> str:
        """Extract location generically"""
        text = container.get_text()
        
        # Look for location indicators
        location_indicators = ['at ', 'in ', 'location:', 'venue:', 'address:']
        for indicator in location_indicators:
            if indicator in text.lower():
                # Try to extract text after the indicator
                parts = text.lower().split(indicator)
                if len(parts) > 1:
                    location = parts[1].split('\n')[0].strip()
                    if location and len(location) < 100:
                        return location
        
        return ""

    def _extract_price_generically(self, container) -> str:
        """Extract price generically"""
        text = container.get_text()
        
        # Look for price patterns
        price_patterns = [
            r'\$\d+(?:\.\d{2})?',  # $10.00
            r'\d+\s*dollars?',     # 10 dollars
            r'free',               # free
            r'no cost',            # no cost
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return ""

    def _extract_with_content_analysis(self, soup: BeautifulSoup, base_url: str) -> List[ScrapedEvent]:
        """Extract events using content analysis when other methods fail"""
        events = []
        
        # Look for any text that might be event titles
        all_text_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div'])
        
        for elem in all_text_elements:
            text = elem.get_text(strip=True)
            
            # Check if this looks like an event title
            if self._looks_like_event_title(text):
                event = ScrapedEvent(
                    title=text,
                    source=base_url,
                    url=base_url
                )
                events.append(event)
        
        return events

    def _looks_like_event_title(self, text: str) -> bool:
        """Check if text looks like an event title"""
        if not text or len(text) < 10 or len(text) > 200:
            return False
        
        # Look for event-related keywords
        event_keywords = [
            'event', 'concert', 'show', 'meeting', 'conference', 'workshop',
            'seminar', 'class', 'training', 'festival', 'exhibition', 'gala',
            'party', 'celebration', 'performance', 'presentation', 'talk'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in event_keywords)

    def _parse_datetime(self, date_text: str, time_text: str) -> str:
        """Parse date and time text into a standardized format"""
        combined = f"{date_text} {time_text}".strip()
        
        if not combined:
            return ""
        
        # Try to parse common date formats
        try:
            # This is a simplified parser - you might want to use dateutil.parser
            # for more robust date parsing
            return combined
        except Exception:
            return combined

    def test_scraper(self, url: str) -> Dict:
        """Test the scraper on a URL and return results"""
        try:
            start_time = time.time()
            events = self.extract_events(url)
            end_time = time.time()
            
            return {
                'success': True,
                'message': f"Successfully extracted {len(events)} events",
                'events_found': len(events),
                'sample_events': [
                    {
                        'title': event.title,
                        'description': event.description[:100] + "..." if len(event.description) > 100 else event.description,
                        'date': event.start_datetime,
                        'location': event.location_name,
                        'price': event.price
                    }
                    for event in events[:3]
                ],
                'response_time': round((end_time - start_time) * 1000, 2)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Scraping failed: {str(e)}",
                'events_found': 0,
                'sample_events': []
            }

# Example usage
if __name__ == "__main__":
    scraper = AdvancedWebScraper()
    
    # Test URLs
    test_urls = [
        "https://www.washingtonian.com/calendar-2/",
        "https://www.eventbrite.com/d/washington-dc/events/",
        "https://www.meetup.com/find/events/?location=us--dc--washington"
    ]
    
    for url in test_urls:
        print(f"\nTesting: {url}")
        result = scraper.test_scraper(url)
        print(f"Result: {result}")
