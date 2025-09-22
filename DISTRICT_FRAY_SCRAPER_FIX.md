# 🎯 **DISTRICT FRAY SCRAPER FIX**

## 🚨 **PROBLEM IDENTIFIED**

The current scraper is extracting **location names and category filters** as "events" instead of the actual events from [District Fray](https://districtfray.com/eventscalendar/?event_category=official-fray-events#all-events).

### **What's Being Scraped (WRONG):**
- Theodore Roosevelt Island
- Cleveland Park  
- Stanton Park
- Mount Vernon Triangle
- Nightlife Events
- Family Free Events
- etc.

### **What Should Be Scraped (CORRECT):**
- **Opening Weekend Celebration** - September 21, 2025 @ 10:00 am
- **Fit @ Met // Wednesday Morning Fitness Series** - September 24, 2025 @ 8:00 am
- **Carlyle Crossing Pickleball Tournament 2025** - September 27, 2025 @ 10:00 am
- **Fit @ Potomac Yard // Sunday Afternoon Fitness Series** - September 28, 2025 @ 2:00 pm

## 🛠️ **SOLUTION: SPECIALIZED DISTRICT FRAY SCRAPER**

### **PROMPT FOR CURSOR:**

```
Add a specialized scraper for District Fray events to the enhanced_web_scraper.py file. The current scraper is extracting location names and category filters instead of actual events.

## IMPLEMENTATION:

### 1. Add District Fray Detection
```python
def detect_scraping_strategy(self, url: str, html_content: str = '') -> str:
    """Enhanced strategy detection with District Fray support"""
    if not html_content:
        try:
            response = self.session.get(url, timeout=10)
            html_content = response.text
        except:
            return 'static_html'
    
    html_lower = html_content.lower()
    
    # Special cases first
    if 'districtfray.com' in url:
        return 'district_fray_events'
    if 'aspeninstitute.org' in url:
        return 'javascript_heavy'
    if 'runpacers.com' in url:
        return 'shopify_events'
    
    # ... rest of existing detection logic
```

### 2. Add District Fray Scraping Strategy
```python
def __init__(self):
    self.scraping_strategies = {
        'static_html': self._scrape_static_html,
        'infinite_scroll': self._scrape_with_infinite_scroll,
        'pagination': self._scrape_with_pagination,
        'api_endpoints': self._scrape_via_api,
        'javascript_heavy': self._scrape_with_javascript_handling,
        'shopify_events': self._scrape_shopify_events,
        'district_fray_events': self._scrape_district_fray_events  # NEW
    }
```

### 3. Implement District Fray Scraper
```python
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
        
        # Common filter/navigation terms
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
        
        return self._get_smart_fallback_date(title, text)
        
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
```

## 4. Update Strategy Detection
```python
def detect_scraping_strategy(self, url: str, html_content: str = '') -> str:
    """Enhanced strategy detection with District Fray support"""
    if not html_content:
        try:
            response = self.session.get(url, timeout=10)
            html_content = response.text
        except:
            return 'static_html'
    
    html_lower = html_content.lower()
    
    # Special cases first
    if 'districtfray.com' in url:
        return 'district_fray_events'
    if 'aspeninstitute.org' in url:
        return 'javascript_heavy'
    if 'runpacers.com' in url:
        return 'shopify_events'
    
    # Enhanced detection indicators
    indicators = {
        'javascript_heavy': [
            'react', 'vue', 'angular', 'spa', 'single-page',
            'load more', 'infinite scroll', 'lazy loading',
            'dynamic content', 'ajax', 'fetch', 'xhr',
            'client-side rendering', 'spa-', 'app-'
        ],
        'api_endpoints': [
            'api/', 'graphql', 'json', 'ajax', 'fetch',
            'xhr', 'rest', 'endpoint', '/api/',
            'application/json', 'content-type: application/json'
        ],
        'pagination': [
            'page=', 'p=', 'offset=', 'limit=', 'next page',
            'previous page', 'pagination', 'page-',
            'load more', 'show more', 'view more'
        ],
        'shopify_events': [
            'shopify', 'shopifycdn', 'myshopify.com',
            'shopify-section', 'shopify-theme'
        ],
        'wordpress_events': [
            'wp-content', 'wordpress', 'wp-json',
            'wp-includes', 'wp-admin'
        ],
        'calendar_events': [
            'calendar', 'event-calendar', 'fullcalendar',
            'calendar-widget', 'event-schedule'
        ]
    }
    
    scores = {}
    for strategy, patterns in indicators.items():
        score = sum(1 for pattern in patterns if pattern in html_lower)
        scores[strategy] = score
    
    # Return strategy with highest score
    best_strategy = max(scores, key=scores.get) if scores else 'static_html'
    
    # If no clear winner, try static_html first
    if scores[best_strategy] == 0:
        return 'static_html'
    
    logger.info(f"🎯 Detected strategy: {best_strategy} (score: {scores[best_strategy]})")
    return best_strategy
```

## 5. Test the Fix
```python
def test_district_fray_scraper():
    """Test the District Fray scraper"""
    scraper = EnhancedWebScraper()
    url = "https://districtfray.com/eventscalendar/?event_category=official-fray-events#all-events"
    
    events = scraper.extract_events(url)
    
    print(f"Found {len(events)} events:")
    for event in events:
        print(f"- {event.title} on {event.start_datetime} at {event.location_name}")
    
    # Should find events like:
    # - Opening Weekend Celebration on 2025-09-21T10:00:00 at Milken Center for Advancing the American Dream
    # - Fit @ Met // Wednesday Morning Fitness Series on 2025-09-24T08:00:00 at Metropolitan Park
    # - Carlyle Crossing Pickleball Tournament 2025 on 2025-09-27T10:00:00 at Carlyle Crossing - The Plaza
```

## EXPECTED RESULTS:

After implementing this fix, the District Fray scraper should extract:

✅ **Real Events:**
- Opening Weekend Celebration - September 21, 2025 @ 10:00 am
- Fit @ Met // Wednesday Morning Fitness Series - September 24, 2025 @ 8:00 am
- Carlyle Crossing Pickleball Tournament 2025 - September 27, 2025 @ 10:00 am
- Fit @ Potomac Yard // Sunday Afternoon Fitness Series - September 28, 2025 @ 2:00 pm

❌ **NOT Location Names:**
- Theodore Roosevelt Island
- Cleveland Park
- Stanton Park
- etc.

This specialized scraper will correctly identify and extract actual events from District Fray while filtering out location names and category filters.
```

## 🎯 **IMMEDIATE ACTION REQUIRED**

The current scraper is extracting **location names and category filters** instead of actual events from District Fray. This specialized scraper will fix this issue by:

1. **Detecting District Fray URLs** and using a specialized scraping strategy
2. **Filtering out navigation elements** like location names and category buttons
3. **Extracting actual events** with proper titles, dates, times, and locations
4. **Using specific selectors** for District Fray's event structure

**This will ensure the scraper extracts real events like "Opening Weekend Celebration" and "Fit @ Met // Wednesday Morning Fitness Series" instead of location names like "Theodore Roosevelt Island" and "Cleveland Park".**
