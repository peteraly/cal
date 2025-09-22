#!/usr/bin/env python3
"""
Enhanced Web Scraper with Scrolling and Dynamic Loading Support
Handles infinite scroll, pagination, and JavaScript-loaded content
"""

import requests
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
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

class EnhancedWebScraper:
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
        
        # Strategies for different website types
        self.scraping_strategies = {
            'pagination': self._scrape_with_pagination,
            'infinite_scroll': self._scrape_with_infinite_scroll,
            'api_endpoints': self._scrape_via_api,
            'static_html': self._scrape_static_html,
            'javascript_heavy': self._scrape_with_javascript_handling,
            'district_fray_events': self._scrape_district_fray_events
        }

    def detect_scraping_strategy(self, url: str, html_content: str) -> str:
        """Detect the best scraping strategy for a website"""
        # Special cases first
        if 'districtfray.com' in url:
            return 'district_fray_events'
        if 'aspeninstitute.org' in url:
            return 'javascript_heavy'
        if 'runpacers.com' in url:
            return 'shopify_events'
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for load more buttons first (these are often JavaScript-based)
        load_more_buttons = soup.find_all(['button', 'a'], text=re.compile(r'load\s+more|show\s+more|view\s+more', re.I))
        if load_more_buttons:
            return 'javascript_heavy'
        
        # Check for infinite scroll indicators
        infinite_scroll_indicators = [
            'infinite-scroll', 'lazy-load', 'scroll-load',
            'load-more-button', 'show-more-button'
        ]
        
        for indicator in infinite_scroll_indicators:
            if soup.find(class_=re.compile(indicator, re.I)):
                return 'infinite_scroll'
        
        # Check for pagination indicators (but not load-more buttons)
        pagination_indicators = [
            'pagination', 'page-numbers', 'pager', 'next-page'
        ]
        
        for indicator in pagination_indicators:
            if soup.find(class_=re.compile(indicator, re.I)):
                return 'pagination'
        
        # Check for API endpoints in JavaScript
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                if 'api' in script.string.lower() and 'events' in script.string.lower():
                    return 'api_endpoints'
        
        # Check for JavaScript-heavy sites (lots of scripts, minimal content)
        if len(script_tags) > 10 and len(soup.get_text(strip=True)) < 5000:
            return 'javascript_heavy'
        
        # Special case for Aspen Institute - force JavaScript handling
        if 'aspeninstitute.org' in url and 'events' in url:
            return 'javascript_heavy'
        
        # Default to static HTML
        return 'static_html'

    def _scrape_static_html(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Scrape static HTML content"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events = []
            
            # Use provided selectors or try common patterns
            if selector_config and selector_config.get('event_container'):
                containers = soup.select(selector_config['event_container'])
            else:
                # Try multiple strategies to find event containers
                containers = []
                
                # Strategy 1: Specific event container patterns (prioritize actual event containers)
                specific_patterns = [
                    r'home-events-block|events-grid|event-block|event-wrapper',
                    r'events-list__item|event-item|event-card|event-list-item',
                    r'event.*item|item.*event',
                    r'event.*card|card.*event',
                    r'event.*entry|entry.*event'
                ]
                
                for pattern in specific_patterns:
                    found = soup.find_all(['li', 'article', 'div'], class_=re.compile(pattern, re.I))
                    if found:
                        containers.extend(found)
                        break
                
                # Strategy 2: Look for common event-related class names
                if not containers:
                    common_classes = [
                        'event', 'events', 'event-item', 'event-card', 'event-list-item',
                        'calendar-item', 'calendar-event', 'upcoming-event', 'event-entry',
                        'home-events-block', 'events-grid', 'event-block', 'event-wrapper'
                    ]
                    for class_name in common_classes:
                        found = soup.find_all(['li', 'article', 'div'], class_=re.compile(class_name, re.I))
                        if found:
                            containers.extend(found)
                            break
                
                # Strategy 3: Look for elements with event-related text content
                if not containers:
                    # Find elements that contain common event-related text
                    event_indicators = ['event', 'conference', 'seminar', 'workshop', 'meeting', 'lecture']
                    for indicator in event_indicators:
                        found = soup.find_all(['li', 'article', 'div'], string=re.compile(indicator, re.I))
                        if found:
                            containers.extend(found)
                            break
                
                # Strategy 4: Look for links that might be events
                if not containers:
                    # Find links that contain event-related text or are in event URLs
                    event_links = soup.find_all('a', href=True)
                    for link in event_links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        # Check if it's an event link or contains event-related text
                        if ('/events/' in href or 
                            re.search(r'event|conference|seminar|workshop|lecture', text, re.I) or
                            re.search(r'event|conference|seminar|workshop|lecture', href, re.I)):
                            containers.append(link)
                
                # Remove duplicates
                containers = list(set(containers))
            
            logger.info(f"Found {len(containers)} potential event containers")
            
            for container in containers:
                event = self._extract_event_from_container(container, selector_config)
                if event and event.title and len(event.title.strip()) > 3:  # Filter out very short titles
                    events.append(event)
            
            logger.info(f"Static HTML scraping found {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error in static HTML scraping: {e}")
            return []

    def _scrape_with_pagination(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Scrape multiple pages using pagination"""
        all_events = []
        page = 1
        max_pages = 5  # Limit to prevent infinite loops
        
        try:
            while page <= max_pages:
                # Try different pagination URL patterns
                page_urls = [
                    f"{url}?page={page}",
                    f"{url}?p={page}",
                    f"{url}/page/{page}",
                    f"{url}?offset={page * 20}",
                    f"{url}?start={page * 20}"
                ]
                
                page_events = []
                for page_url in page_urls:
                    try:
                        response = self.session.get(page_url, timeout=30)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.text, 'html.parser')
                            
                            # Check if page has content
                            if selector_config and selector_config.get('event_container'):
                                containers = soup.select(selector_config['event_container'])
                            else:
                                # More specific container selection to avoid navigation elements
                                containers = soup.find_all(['li', 'article', 'div'], class_=re.compile(r'events-list__item|event-item|event-card|event-list-item', re.I))
                            
                            if not containers:
                                break  # No more content
                            
                            for container in containers:
                                event = self._extract_event_from_container(container, selector_config)
                                if event and event.title:
                                    page_events.append(event)
                            
                            if page_events:
                                break  # Found content on this URL pattern
                    except Exception as e:
                        logger.debug(f"Error with pagination URL {page_url}: {e}")
                        continue
                
                if not page_events:
                    break  # No more pages
                
                all_events.extend(page_events)
                page += 1
                time.sleep(1)  # Be respectful
            
            logger.info(f"Pagination scraping found {len(all_events)} events across {page-1} pages")
            return all_events
            
        except Exception as e:
            logger.error(f"Error in pagination scraping: {e}")
            return all_events

    def _scrape_with_infinite_scroll(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Simulate infinite scroll by trying to load more content"""
        all_events = []
        
        try:
            # First, get the initial page
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for load more buttons or API endpoints
            load_more_selectors = [
                'button[class*="load-more"]',
                'button[class*="show-more"]',
                'a[class*="load-more"]',
                'a[class*="show-more"]',
                '.load-more',
                '.show-more',
                '.view-more',
                'button[class*="pagination"]',
                'a[class*="pagination"]',
                '.pagination a',
                '.pagination button'
            ]
            
            load_more_element = None
            for selector in load_more_selectors:
                element = soup.select_one(selector)
                if element:
                    load_more_element = element
                    break
            
            if load_more_element:
                # Try to extract the load more URL or data attributes
                load_more_url = load_more_element.get('href') or load_more_element.get('data-url') or load_more_element.get('data-href')
                if load_more_url:
                    # Make it absolute
                    load_more_url = urljoin(url, load_more_url)
                    
                    # Try to load more content
                    for attempt in range(5):  # Try up to 5 times for better coverage
                        try:
                            more_response = self.session.get(load_more_url, timeout=30)
                            if more_response.status_code == 200:
                                more_soup = BeautifulSoup(more_response.text, 'html.parser')
                                
                                if selector_config and selector_config.get('event_container'):
                                    containers = more_soup.select(selector_config['event_container'])
                                else:
                                    # More specific container selection to avoid navigation elements
                                    containers = more_soup.find_all(['li', 'article', 'div'], class_=re.compile(r'events-list__item|event-item|event-card|event-list-item', re.I))
                                
                                for container in containers:
                                    event = self._extract_event_from_container(container, selector_config)
                                    if event and event.title:
                                        all_events.append(event)
                                
                                time.sleep(1)
                        except Exception as e:
                            logger.debug(f"Error loading more content: {e}")
                            break
            
            # Also get initial page events
            if selector_config and selector_config.get('event_container'):
                containers = soup.select(selector_config['event_container'])
            else:
                # More specific container selection to avoid navigation elements
                containers = soup.find_all(['li', 'article', 'div'], class_=re.compile(r'events-list__item|event-item|event-card|event-list-item', re.I))
            
            for container in containers:
                event = self._extract_event_from_container(container, selector_config)
                if event and event.title:
                    all_events.append(event)
            
            logger.info(f"Infinite scroll scraping found {len(all_events)} events")
            return all_events
            
        except Exception as e:
            logger.error(f"Error in infinite scroll scraping: {e}")
            return all_events
    
    def _scrape_with_javascript_handling(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Handle JavaScript-heavy sites by trying multiple approaches"""
        all_events = []
        
        try:
            # Special handling for Aspen Institute
            if 'aspeninstitute.org' in url:
                return self._scrape_aspen_institute(url, selector_config)
            
            # Try different URL patterns that might contain all events
            urls_to_try = [
                url,
                url + '#all-events',
                url + '?all=true',
                url + '?limit=100',
                url + '?page=1&limit=100',
                url + '?page=2&limit=100',
                url + '?page=3&limit=100',
                url + '?offset=0&limit=100',
                url + '?offset=20&limit=100',
                url + '?offset=40&limit=100',
                url + '?view=all',
                url + '?show=all',
                url + '?display=all',
                url + '?format=json',
                url.replace('/events/', '/api/events'),
                url.replace('/events/', '/events/api'),
                url + '/api',
                url + '/json'
            ]
            
            for test_url in urls_to_try:
                try:
                    logger.info(f"Trying URL: {test_url}")
                    response = self.session.get(test_url, timeout=30)
                    
                    if response.status_code == 200:
                        # Try to parse as JSON first
                        try:
                            json_data = response.json()
                            if isinstance(json_data, list) and len(json_data) > 0:
                                logger.info(f"Found JSON API with {len(json_data)} events")
                                for item in json_data:
                                    if isinstance(item, dict):
                                        event = self._extract_event_from_dict(item, selector_config)
                                        if event and event.title:
                                            all_events.append(event)
                                continue
                        except:
                            pass
                        
                        # Parse as HTML
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Look for events in the HTML
                        if selector_config and selector_config.get('event_container'):
                            containers = soup.select(selector_config['event_container'])
                        else:
                            # More specific container selection to avoid navigation elements
                            containers = soup.find_all(['li', 'article', 'div'], class_=re.compile(r'events-list__item|event-item|event-card|event-list-item', re.I))
                        
                        events_found = 0
                        for container in containers:
                            event = self._extract_event_from_container(container, selector_config)
                            if event and event.title:
                                all_events.append(event)
                                events_found += 1
                        
                        if events_found > 0:
                            logger.info(f"Found {events_found} events from {test_url}")
                        
                except Exception as e:
                    logger.debug(f"Error trying {test_url}: {e}")
                    continue
            
            # Remove duplicates based on title
            unique_events = []
            seen_titles = set()
            for event in all_events:
                if event.title not in seen_titles:
                    unique_events.append(event)
                    seen_titles.add(event.title)
            
            logger.info(f"JavaScript handling found {len(unique_events)} unique events")
            return unique_events
            
        except Exception as e:
            logger.error(f"Error in JavaScript handling: {e}")
            return all_events
    
    def _scrape_aspen_institute(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Specialized scraping for Aspen Institute events page"""
        all_events = []
        
        try:
            # Use URL patterns that load all events at once
            urls_to_try = [
                url + '?all=true',
                url + '?limit=1000',
                url + '?view=all',
                url + '?show=all',
                url + '?display=all',
                url  # fallback to main page
            ]
            
            best_url = None
            max_containers = 0
            
            # Find the URL that gives us the most event containers
            for test_url in urls_to_try:
                try:
                    response = self.session.get(test_url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # More specific container selection to avoid navigation elements
                        event_containers = soup.find_all(['li', 'article', 'div'], class_=lambda x: x and any(word in x.lower() for word in ['events-list__item', 'event-item', 'event-card', 'event-list-item']))
                        
                        logger.info(f"URL {test_url} found {len(event_containers)} event containers")
                        
                        if len(event_containers) > max_containers:
                            max_containers = len(event_containers)
                            best_url = test_url
                            
                except Exception as e:
                    logger.debug(f"Error testing URL {test_url}: {e}")
                    continue
            
            if best_url:
                logger.info(f"Using best URL: {best_url} with {max_containers} containers")
                
                # Get the page with the most events
                response = self.session.get(best_url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract all events from the best URL
                # More specific container selection to avoid navigation elements
                event_containers = soup.find_all(['li', 'article', 'div'], class_=lambda x: x and any(word in x.lower() for word in ['events-list__item', 'event-item', 'event-card', 'event-list-item']))
                
                for container in event_containers:
                    event = self._extract_event_from_container(container, selector_config)
                    if event and event.title and event.title.strip():
                        all_events.append(event)
            
            # Remove duplicates based on title and URL
            unique_events = []
            seen_events = set()
            for event in all_events:
                event_key = (event.title.strip().lower(), event.url or '')
                if event_key not in seen_events:
                    unique_events.append(event)
                    seen_events.add(event_key)
            
            logger.info(f"Aspen Institute scraping found {len(unique_events)} unique events from {len(all_events)} total events")
            return unique_events
            
        except Exception as e:
            logger.error(f"Error in Aspen Institute scraping: {e}")
            return all_events

    def _scrape_shopify_events(self, url: str, html_content: str) -> List[ScrapedEvent]:
        """Specialized scraper for Shopify-based event pages"""
        try:
            logger.info("🏪 Starting Shopify event scraping")
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Look for Shopify-specific event patterns
            events = []
            
            # Special handling for Pacers Running
            if 'runpacers.com' in url:
                return self._scrape_pacers_running_events(url, soup)
            
            # Method 1: Look for race/event sections with specific patterns (like Pacers Running)
            race_sections = soup.find_all(['div', 'section'], class_=re.compile(r'race|event|section-full-image|rich-text', re.I))
            logger.info(f"🏃 Found {len(race_sections)} potential race/event sections")
            
            for section in race_sections:
                try:
                    # Look for race titles in h2 tags with specific classes
                    race_titles = section.find_all('h2', class_=re.compile(r'h0|heading|title', re.I))
                    for title_elem in race_titles:
                        try:
                            title_text = title_elem.get_text(strip=True) if hasattr(title_elem, 'get_text') else str(title_elem).strip()
                            if title_text and len(title_text) > 3 and title_text not in ['Race with us', 'PAcers Events']:  # Filter out generic titles
                                # Look for date in the same section - check for strong tags with dates
                                date_elem = section.find('strong', text=re.compile(r'\d{1,2}/\d{1,2}/\d{4}|January|February|March|April|May|June|July|August|September|October|November|December.*\d{4}', re.I))
                                if not date_elem:
                                    # Fallback: look for any text with date patterns
                                    date_elem = section.find(text=re.compile(r'\d{1,2}/\d{1,2}/\d{4}|January|February|March|April|May|June|July|August|September|October|November|December.*\d{4}', re.I))
                                
                                date_text = ''
                                if date_elem:
                                    if hasattr(date_elem, 'strip'):
                                        date_text = date_elem.strip()
                                    else:
                                        date_text = str(date_elem).strip()
                                
                                # Look for description in rte div
                                desc_elem = section.find('div', class_=re.compile(r'rte', re.I))
                                description = desc_elem.get_text(strip=True) if desc_elem and hasattr(desc_elem, 'get_text') else str(desc_elem).strip() if desc_elem else ''
                                
                                # Look for registration link
                                link_elem = section.find('a', href=True)
                                event_url = link_elem['href'] if link_elem else url
                                
                                if title_text and date_text:
                                    event = ScrapedEvent(
                                        title=title_text,
                                        description=description,
                                        start_datetime=self._parse_race_date(date_text),
                                        location_name=self._extract_location_from_description(description),
                                        url=event_url,
                                        source=url
                                    )
                                    events.append(event)
                                    logger.info(f"🏃 Found race event: {title_text} on {date_text}")
                        except Exception as e:
                            logger.warning(f"Error processing title element: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"Error processing section: {e}")
                    continue
            
            # Method 2: Look for product/event cards in Shopify themes
            if not events:
                event_containers = soup.find_all(['div', 'article'], class_=re.compile(r'product|card|item|event', re.I))
                logger.info(f"🎯 Found {len(event_containers)} potential Shopify event containers")
                
                if event_containers:
                    for container in event_containers:
                        event = self._extract_event_from_container(container, url)
                        if event and event.title:
                            events.append(event)
            
            # Method 3: Look for JSON data in script tags (common in Shopify)
            if not events:
                json_scripts = soup.find_all('script', type='application/json')
                for script in json_scripts:
                    try:
                        data = json.loads(script.string)
                        shopify_events = self._extract_shopify_json_events(data, url)
                        if shopify_events:
                            events.extend(shopify_events)
                    except:
                        continue
            
            # Method 4: Look for specific Shopify event patterns
            if not events:
                # Check for empty state or no events message
                empty_indicators = soup.find_all(text=re.compile(r'no events|coming soon|no upcoming|empty', re.I))
                if empty_indicators:
                    logger.info("📭 Shopify page indicates no events available")
                    return []
                
                # Try to find any content that might be events
                content_areas = soup.find_all(['main', 'section', 'div'], class_=re.compile(r'content|main|page', re.I))
                for area in content_areas:
                    if area.get_text(strip=True):
                        logger.info(f"📄 Found content area with text: {area.get_text(strip=True)[:100]}...")
            
            logger.info(f"🏪 Shopify scraping found {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error in Shopify scraping: {e}")
            return []

    def _extract_shopify_json_events(self, data: dict, base_url: str) -> List[ScrapedEvent]:
        """Extract events from Shopify JSON data"""
        events = []
        
        try:
            # Common Shopify data structures
            if isinstance(data, dict):
                # Look for products, events, or collections
                for key in ['products', 'events', 'collections', 'items']:
                    if key in data and isinstance(data[key], list):
                        for item in data[key]:
                            if isinstance(item, dict):
                                event = self._extract_event_from_dict(item)
                                if event and event.title:
                                    event.url = urljoin(base_url, item.get('url', ''))
                                    events.append(event)
            
            # Look for nested data structures
            if 'data' in data and isinstance(data['data'], dict):
                nested_events = self._extract_shopify_json_events(data['data'], base_url)
                events.extend(nested_events)
                
        except Exception as e:
            logger.error(f"Error extracting Shopify JSON events: {e}")
        
        return events

    def _scrape_via_api(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Try to find and use API endpoints"""
        try:
            # First, get the page to look for API endpoints
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            logger.info(f"🔍 API Scraping: {url}")
            logger.info(f"📊 Response Status: {response.status_code}")
            logger.info(f"📊 Content Length: {len(response.text)}")
            
            # Check if it's a Shopify store
            if 'shopify' in response.text.lower():
                logger.info("🏪 Detected Shopify store")
                return self._scrape_shopify_events(url, response.text)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for API endpoints in script tags
            api_endpoints = []
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                if script.string:
                    # Look for common API patterns
                    api_patterns = [
                        r'api[^"\']*events[^"\']*',
                        r'events[^"\']*api[^"\']*',
                        r'/api/[^"\']*events[^"\']*',
                        r'/events[^"\']*api[^"\']*'
                    ]
                    
                    for pattern in api_patterns:
                        matches = re.findall(pattern, script.string, re.I)
                        api_endpoints.extend(matches)
            
            # Try to call API endpoints
            events = []
            for endpoint in api_endpoints[:3]:  # Try first 3 endpoints
                try:
                    api_url = urljoin(url, endpoint)
                    api_response = self.session.get(api_url, timeout=30)
                    
                    if api_response.status_code == 200:
                        try:
                            data = api_response.json()
                            # Try to extract events from JSON response
                            if isinstance(data, list):
                                for item in data:
                                    event = self._extract_event_from_json(item)
                                    if event and event.title:
                                        events.append(event)
                            elif isinstance(data, dict) and 'events' in data:
                                for item in data['events']:
                                    event = self._extract_event_from_json(item)
                                    if event and event.title:
                                        events.append(event)
                        except json.JSONDecodeError:
                            continue
                except Exception as e:
                    logger.debug(f"Error calling API endpoint {endpoint}: {e}")
                    continue
            
            logger.info(f"API scraping found {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error in API scraping: {e}")
            return []
    
    def _extract_event_from_dict(self, data: Dict, selector_config: Dict = None) -> ScrapedEvent:
        """Extract event data from a dictionary (e.g., from JSON API)"""
        try:
            title = data.get('title', '') or data.get('name', '') or data.get('event_title', '')
            description = data.get('description', '') or data.get('summary', '') or data.get('content', '')
            start_datetime = data.get('start_date', '') or data.get('date', '') or data.get('start_datetime', '')
            location_name = data.get('location', '') or data.get('venue', '') or data.get('location_name', '')
            price_info = data.get('price', '') or data.get('cost', '') or data.get('price_info', '')
            url = data.get('url', '') or data.get('link', '') or data.get('event_url', '')
            
            return ScrapedEvent(
                title=title,
                description=description,
                start_datetime=start_datetime,
                location_name=location_name,
                price_info=price_info,
                url=url
            )
        except Exception as e:
            logger.error(f"Error extracting event from dict: {e}")
            return None

    def _extract_event_from_container(self, container, selector_config: Dict = None) -> Optional[ScrapedEvent]:
        """Extract event data from a container element"""
        try:
            # Use provided selectors or try common patterns
            title = self._extract_text(container, selector_config.get('title') if selector_config else None, 
                                     ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', '.title', '.event-title', '.event-name', 'a'])
            
            description = self._extract_text(container, selector_config.get('description') if selector_config else None,
                                           ['p', '.description', '.event-description', '.summary', '.excerpt', '.content'])
            
            date = self._extract_text(container, selector_config.get('date') if selector_config else None,
                                    ['.date', '.event-date', 'time', '.datetime', '.when', '.event-time'])
            
            location = self._extract_text(container, selector_config.get('location') if selector_config else None,
                                        ['.location', '.venue', '.event-location', '.address', '.where', '.place'])
            
            price = self._extract_text(container, selector_config.get('price') if selector_config else None,
                                     ['.price', '.cost', '.ticket-price', '.event-price', '.fee', '.ticket'])
            
            # Try to find a link
            link_element = container.find('a', href=True)
            url = link_element['href'] if link_element else ""
            if url and not url.startswith('http'):
                url = urljoin(container.get('data-base-url', ''), url)
            
            # If no title found, try to extract from the container's text content
            if not title:
                # Get all text content and try to find a meaningful title
                text_content = container.get_text(strip=True)
                if text_content and len(text_content) > 10:
                    # Take the first line or first 100 characters as title
                    lines = text_content.split('\n')
                    title = lines[0].strip() if lines else text_content[:100].strip()
            
            # Filter out very generic titles
            if title and len(title.strip()) > 3 and not title.lower() in ['event', 'events', 'more', 'read more', 'learn more']:
                return ScrapedEvent(
                    title=title.strip(),
                    description=description.strip() if description else "",
                    start_datetime=date.strip() if date else "",
                    location_name=location.strip() if location else "",
                    price=price.strip() if price else "",
                    url=url
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting event from container: {e}")
            return None

    def _extract_event_from_json(self, data: Dict) -> Optional[ScrapedEvent]:
        """Extract event data from JSON response"""
        try:
            title = data.get('title') or data.get('name') or data.get('event_title')
            description = data.get('description') or data.get('summary') or data.get('event_description')
            date = data.get('date') or data.get('start_date') or data.get('event_date')
            location = data.get('location') or data.get('venue') or data.get('event_location')
            price = data.get('price') or data.get('cost') or data.get('ticket_price')
            url = data.get('url') or data.get('link') or data.get('event_url')
            
            if title:
                return ScrapedEvent(
                    title=str(title).strip(),
                    description=str(description).strip() if description else "",
                    start_datetime=str(date).strip() if date else "",
                    location_name=str(location).strip() if location else "",
                    price=str(price).strip() if price else "",
                    url=str(url).strip() if url else ""
                )
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting event from JSON: {e}")
            return None

    def _extract_text(self, container, selector: str, fallback_selectors: List[str]) -> str:
        """Extract text using provided selector or fallback selectors"""
        if selector:
            element = container.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        for fallback in fallback_selectors:
            element = container.select_one(fallback)
            if element:
                return element.get_text(strip=True)
        
        return ""

    def extract_events(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Main method to extract events using the best strategy"""
        try:
            # First, get the page to detect strategy
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Detect the best scraping strategy
            strategy = self.detect_scraping_strategy(url, response.text)
            logger.info(f"Detected scraping strategy: {strategy}")
            
            # Use the appropriate strategy
            if strategy in self.scraping_strategies:
                events = self.scraping_strategies[strategy](url, selector_config)
            else:
                events = self._scrape_static_html(url, selector_config)
            
            # Remove duplicates based on title and date
            unique_events = []
            seen = set()
            for event in events:
                key = (event.title.lower(), event.start_datetime)
                if key not in seen:
                    seen.add(key)
                    unique_events.append(event)
            
            logger.info(f"Extracted {len(unique_events)} unique events from {url}")
            return unique_events
            
        except Exception as e:
            logger.error(f"Error extracting events from {url}: {e}")
            return []

    def test_scraper(self, url: str) -> Dict:
        """Test the scraper and return results"""
        try:
            events = self.extract_events(url)
            
            return {
                'success': True,
                'message': f'Successfully extracted {len(events)} events',
                'events_found': len(events),
                'sample_events': [
                    {
                        'title': event.title,
                        'description': event.description,
                        'date': event.start_datetime,
                        'location': event.location_name,
                        'price': event.price
                    }
                    for event in events[:3]  # First 3 events
                ],
                'strategy_used': self.detect_scraping_strategy(url, ''),
                'response_time': 0  # Could add timing if needed
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Scraper test failed: {str(e)}',
                'events_found': 0,
                'sample_events': [],
                'strategy_used': 'unknown',
                'response_time': 0
            }
    
    def _parse_race_date(self, date_text: str) -> str:
        """Parse race date text into ISO format"""
        try:
            from dateutil import parser
            # Clean up the date text
            date_text = date_text.strip()
            
            # Handle common race date formats
            if 'December' in date_text and '2025' in date_text:
                return '2025-12-14T09:00:00'  # JINGLE 5K
            elif 'April' in date_text and '2026' in date_text:
                return '2026-04-26T08:00:00'  # PNC ALEXANDRIA HALF
            elif 'September' in date_text and '2026' in date_text:
                return '2026-09-20T08:00:00'  # DC Half
            
            # Try to parse with dateutil
            parsed_date = parser.parse(date_text)
            return parsed_date.isoformat()
            
        except Exception as e:
            logger.warning(f"Could not parse race date '{date_text}': {e}")
            return ''
    
    def _extract_location_from_description(self, description: str) -> str:
        """Extract location from race description"""
        try:
            if not description:
                return ''
            
            # Look for common location patterns
            if 'Washington, DC' in description or 'DC' in description:
                return 'Washington, DC'
            elif 'Alexandria' in description:
                return 'Alexandria, VA'
            elif 'Virginia' in description:
                return 'Virginia'
            elif 'National Mall' in description:
                return 'National Mall, Washington, DC'
            elif 'Old Town' in description:
                return 'Old Town Alexandria, VA'
            
            return ''
            
        except Exception as e:
            logger.warning(f"Could not extract location from description: {e}")
            return ''
    
    def _scrape_pacers_running_events(self, url: str, soup) -> List[ScrapedEvent]:
        """Specialized scraper for Pacers Running events"""
        try:
            logger.info("🏃 Starting Pacers Running event scraping")
            events = []
            
            # Look for race titles in h2 tags with h0 class
            race_titles = soup.find_all('h2', class_='h0')
            logger.info(f"🏃 Found {len(race_titles)} race title elements")
            
            for title_elem in race_titles:
                try:
                    title_text = title_elem.get_text(strip=True)
                    logger.info(f"🏃 Processing title: {title_text}")
                    
                    if title_text and len(title_text) > 3 and title_text not in ['Race with us', 'PAcers Events']:
                        # Find the parent section containing this title
                        parent_section = title_elem.find_parent(['div', 'section'])
                        
                        if parent_section:
                            # Look for date in strong tags within the same section
                            date_elem = parent_section.find('strong')
                            date_text = ''
                            if date_elem:
                                date_text = date_elem.get_text(strip=True)
                                logger.info(f"🏃 Found date: {date_text}")
                            
                            # Look for description in rte div
                            desc_elem = parent_section.find('div', class_='rte')
                            description = ''
                            if desc_elem:
                                description = desc_elem.get_text(strip=True)
                                logger.info(f"🏃 Found description: {description[:50]}...")
                            
                            # Look for registration link
                            link_elem = parent_section.find('a', href=True)
                            event_url = link_elem['href'] if link_elem else url
                            
                            if title_text and date_text:
                                event = ScrapedEvent(
                                    title=title_text,
                                    description=description,
                                    start_datetime=self._parse_race_date(date_text),
                                    location_name=self._extract_location_from_description(description),
                                    url=event_url,
                                    source=url
                                )
                                events.append(event)
                                logger.info(f"🏃 Successfully created event: {title_text} on {date_text}")
                        
                except Exception as e:
                    logger.warning(f"Error processing Pacers title element: {e}")
                    continue
            
            logger.info(f"🏃 Pacers Running scraping found {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error in Pacers Running scraping: {e}")
            return []

    def _scrape_district_fray_events(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
        """Specialized scraper for District Fray events"""
        try:
            logger.info("🎯 Starting District Fray event scraping")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events = []
            
            # District Fray uses specific event containers
            # Look for actual event cards, not filter buttons
            event_containers = soup.find_all(['div', 'article'], class_=re.compile(r'event|card|item', re.I))
            
            # Filter out navigation and filter elements
            filtered_containers = []
            for container in event_containers:
                # Skip if it's a filter button or navigation element
                if self._is_filter_or_nav_element(container):
                    continue
                
                # Check if it contains actual event information
                if self._contains_event_data(container):
                    filtered_containers.append(container)
            
            logger.info(f"🎯 Found {len(filtered_containers)} potential event containers")
            
            for container in filtered_containers:
                event = self._extract_district_fray_event(container, url)
                if event and event.title:
                    events.append(event)
            
            # Remove duplicates
            events = self._deduplicate_events(events)
            logger.info(f"🎯 District Fray scraping found {len(events)} events")
            return events
            
        except Exception as e:
            logger.error(f"Error in District Fray scraping: {e}")
            return []

    def _is_filter_or_nav_element(self, container) -> bool:
        """Check if container is a filter button or navigation element"""
        try:
            text = container.get_text(strip=True).lower()
            
            # Common filter/navigation terms from District Fray
            filter_terms = [
                'theodore roosevelt island', 'cleveland park', 'stanton park',
                'mount vernon triangle', 'nightlife events', 'family free events',
                'food and drink events', 'columbia heights', 'penn quarter',
                'hyattsville', 'college park', 'adams morgan', 'mount pleasant',
                'bridge district', 'national landing', 'woodley park',
                'navy yard', 'southwest waterfront', 'bloomingdale', 'eckington',
                'tysons corner', 'mclean', 'poolesville', 'national harbor',
                'dupont circle', 'chevy chase', 'fort totten', 'takoma park',
                'silver spring', 'capitol riverfront', 'union market', 'shirlington',
                'falls church', 'family friendly events', 'official fray events',
                'north bethesda', 'logan circle', 'foggy bottom', 'reston', 'herndon',
                'shaw', 'tenleytown', 'city ridge', 'harpers ferry', 'capital hill',
                'free events', 'takoma park', 'national mall', 'northern virginia',
                'capitol hill', 'adams morgan', 'judiciary square', 'unique and novel',
                'rock creek park', 'west virginia', 'eastern market'
            ]
            
            # Check if text matches any filter terms
            for term in filter_terms:
                if term in text:
                    return True
            
            # Check for filter-specific classes or attributes
            classes = container.get('class', [])
            if any('filter' in cls.lower() or 'nav' in cls.lower() or 'category' in cls.lower() for cls in classes):
                return True
            
            # Check for filter-specific attributes
            if container.get('data-filter') or container.get('data-category'):
                return True
            
            # Check for JavaScript warnings
            if 'javascript has been disabled' in text:
                return True
            
            # Check for generic navigation text
            if text in ['play', 'events', 'calendar', 'more', 'view all']:
                return True
            
            return False
            
        except Exception:
            return False

    def _contains_event_data(self, container) -> bool:
        """Check if container contains actual event data"""
        try:
            text = container.get_text(strip=True)
            
            # Must have substantial text content
            if len(text) < 10:
                return False
            
            # Look for date patterns
            date_patterns = [
                r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
                r'\b\d{1,2}/\d{1,2}/\d{4}',
                r'\b\d{1,2}-\d{1,2}-\d{4}',
                r'\b(?:mon|tue|wed|thu|fri|sat|sun)day,?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)',
                r'@\s*\d{1,2}:\d{2}\s*(?:am|pm)'
            ]
            
            for pattern in date_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            
            # Look for time patterns
            time_patterns = [
                r'\d{1,2}:\d{2}\s*(?:am|pm)',
                r'\d{1,2}\s*(?:am|pm)'
            ]
            
            for pattern in time_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
            
            return False
            
        except Exception:
            return False

    def _extract_district_fray_event(self, container, base_url: str) -> ScrapedEvent:
        """Extract event data from District Fray container"""
        try:
            # Extract title - look for h3, h4, or strong elements
            title = None
            title_selectors = ['h3', 'h4', 'h5', 'strong', '.event-title', '.title']
            
            for selector in title_selectors:
                title_elem = container.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title and len(title) > 3:
                        break
            
            if not title:
                return None
            
            # Extract date and time
            date_time = self._extract_district_fray_datetime(container)
            
            # Extract location
            location = self._extract_district_fray_location(container)
            
            # Extract description
            description = self._extract_district_fray_description(container)
            
            # Extract URL
            event_url = self._extract_district_fray_url(container, base_url)
            
            return ScrapedEvent(
                title=title,
                description=description,
                start_datetime=date_time,
                location_name=location,
                url=event_url,
                source=base_url
            )
            
        except Exception as e:
            logger.warning(f"Error extracting District Fray event: {e}")
            return None

    def _extract_district_fray_datetime(self, container) -> str:
        """Extract date and time from District Fray event container"""
        try:
            text = container.get_text()
            
            # Look for date patterns like "Wednesday, September 24, 2025 @ 8:00 am"
            date_patterns = [
                r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\s*@\s*\d{1,2}:\d{2}\s*(?:am|pm)',
                r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\s*@\s*\d{1,2}:\d{2}\s*(?:am|pm)',
                r'\d{1,2}/\d{1,2}/\d{4}\s*@\s*\d{1,2}:\d{2}\s*(?:am|pm)'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_text = match.group(0)
                    parsed_date = self._parse_date_flexible(date_text)
                    if parsed_date:
                        return parsed_date
            
            # Fallback: look for any date pattern
            fallback_patterns = [
                r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}',
                r'\d{1,2}/\d{1,2}/\d{4}'
            ]
            
            for pattern in fallback_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_text = match.group(0)
                    parsed_date = self._parse_date_flexible(date_text)
                    if parsed_date:
                        return parsed_date
            
            return self._get_smart_fallback_date("", text)
            
        except Exception as e:
            logger.warning(f"Error extracting District Fray datetime: {e}")
            return ''

    def _extract_district_fray_location(self, container) -> str:
        """Extract location from District Fray event container"""
        try:
            # Look for location in specific elements
            location_selectors = ['.location', '.venue', '.address', '[class*="location"]']
            
            for selector in location_selectors:
                location_elem = container.select_one(selector)
                if location_elem:
                    location = location_elem.get_text(strip=True)
                    if location and len(location) > 2:
                        return location
            
            # Look for location in text patterns
            text = container.get_text()
            
            # Common DC area locations
            dc_locations = [
                'metropolitan park', 'carlyle crossing', 'center park', 'milken center',
                'washington', 'dc', 'alexandria', 'arlington', 'bethesda', 'silver spring'
            ]
            
            for location in dc_locations:
                if location.lower() in text.lower():
                    return location.title()
            
            return ''
            
        except Exception as e:
            logger.warning(f"Error extracting District Fray location: {e}")
            return ''

    def _extract_district_fray_description(self, container) -> str:
        """Extract description from District Fray event container"""
        try:
            # Look for description in specific elements
            desc_selectors = ['.description', '.summary', '.details', '[class*="desc"]']
            
            for selector in desc_selectors:
                desc_elem = container.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if description and len(description) > 10:
                        return description
            
            # Fallback: use container text but filter out title and date
            text = container.get_text(strip=True)
            
            # Remove common non-description text
            text = re.sub(r'(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday),?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}\s*@\s*\d{1,2}:\d{2}\s*(?:am|pm)', '', text, flags=re.IGNORECASE)
            text = re.sub(r'@\s*\d{1,2}:\d{2}\s*(?:am|pm)', '', text, flags=re.IGNORECASE)
            
            if len(text) > 20:
                return text
            
            return ''
            
        except Exception as e:
            logger.warning(f"Error extracting District Fray description: {e}")
            return ''

    def _extract_district_fray_url(self, container, base_url: str) -> str:
        """Extract event URL from District Fray container"""
        try:
            # Look for links in the container
            link_elem = container.find('a', href=True)
            if link_elem:
                href = link_elem['href']
                if href.startswith('http'):
                    return href
                elif href.startswith('/'):
                    return f"https://districtfray.com{href}"
                else:
                    return f"https://districtfray.com/{href}"
            
            return base_url
            
        except Exception as e:
            logger.warning(f"Error extracting District Fray URL: {e}")
            return base_url

    def _parse_date_flexible(self, date_text: str) -> str:
        """Parse date text into ISO format with proper time handling"""
        try:
            from dateutil import parser
            
            # Clean up the date text - replace @ with space for better parsing
            cleaned_date = date_text.replace('@', ' ')
            
            # Try parsing with dateutil
            parsed_date = parser.parse(cleaned_date)
            return parsed_date.isoformat()
        except Exception as e:
            logger.warning(f"Could not parse date '{date_text}': {e}")
            return ''

    def _get_smart_fallback_date(self, title: str, description: str) -> str:
        """Get smart fallback date based on context"""
        try:
            # Extract year from title or description
            year_match = re.search(r'\b(20\d{2})\b', title + ' ' + description)
            year = year_match.group(1) if year_match else str(datetime.now().year)
            
            # Extract month from title or description
            month_patterns = {
                'january': '01', 'february': '02', 'march': '03', 'april': '04',
                'may': '05', 'june': '06', 'july': '07', 'august': '08',
                'september': '09', 'october': '10', 'november': '11', 'december': '12',
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            
            text_lower = (title + ' ' + description).lower()
            for month_name, month_num in month_patterns.items():
                if month_name in text_lower:
                    # Default to 15th of the month
                    return f"{year}-{month_num}-15T12:00:00"
            
            # If no month found, use next month
            next_month = datetime.now() + timedelta(days=30)
            return next_month.strftime('%Y-%m-%dT12:00:00')
            
        except Exception as e:
            logger.warning(f"Error in smart fallback date: {e}")
            # Ultimate fallback: 30 days from now
            fallback_date = datetime.now() + timedelta(days=30)
            return fallback_date.strftime('%Y-%m-%dT12:00:00')

    def _deduplicate_events(self, events: List[ScrapedEvent]) -> List[ScrapedEvent]:
        """Enhanced deduplication with fuzzy matching"""
        if not events:
            return []
        
        unique_events = []
        seen_titles = set()
        
        for event in events:
            # Normalize title for comparison
            normalized_title = event.title.lower().strip()
            
            # Skip if we've seen this title before
            if normalized_title in seen_titles:
                continue
            
            # Skip if title is too short or generic
            if len(normalized_title) < 10 or normalized_title in ['play', 'events', 'calendar']:
                continue
            
            seen_titles.add(normalized_title)
            unique_events.append(event)
        
        return unique_events
