# Universal Web Scraper Enhancement Prompt

## Overview
This prompt provides comprehensive instructions for enhancing the web scraper to work across different website formats and handle various edge cases that may arise in the future.

## Current Scraper Capabilities

### ✅ Working Scrapers
1. **Aspen Institute** - JavaScript-heavy site with "load more" functionality
2. **Pacers Running** - Shopify store with specific HTML structure
3. **District Fray** - Event calendar with location/category filtering
4. **Brookings** - Static HTML with event containers
5. **Cato Institute** - Blocked by Incapsula (recommend removal)

### 🔧 Scraping Strategies Available
- `static_html` - Basic HTML parsing
- `infinite_scroll` - Handles "load more" buttons
- `javascript_heavy` - For dynamic content sites
- `pagination` - For multi-page results
- `api_endpoints` - For JSON API responses
- `shopify_events` - Specialized for Shopify stores
- `district_fray_events` - Specialized for District Fray

## Universal Enhancement Guidelines

### 1. Date Parsing Robustness
```python
def _parse_date_flexible(self, date_text: str) -> str:
    """Parse date text into ISO format with multiple fallbacks"""
    try:
        from dateutil import parser
        
        # Clean up common date format issues
        cleaned_date = date_text.replace('@', 'at')  # Handle @ symbols
        cleaned_date = cleaned_date.replace('TBD', '')  # Remove TBD
        cleaned_date = cleaned_date.replace('TBA', '')  # Remove TBA
        
        # Try parsing with dateutil
        parsed_date = parser.parse(cleaned_date)
        return parsed_date.isoformat()
    except Exception as e:
        logger.warning(f"Could not parse date '{date_text}': {e}")
        return self._get_smart_fallback_date(title, description)
```

### 2. Event Container Detection
```python
def _find_event_containers(self, soup, url):
    """Find event containers using multiple strategies"""
    containers = []
    
    # Strategy 1: Common event class patterns
    event_patterns = [
        r'event', r'card', r'item', r'post', r'article',
        r'listing', r'entry', r'activity', r'program'
    ]
    
    for pattern in event_patterns:
        containers.extend(soup.find_all(['div', 'article', 'section'], 
                                      class_=re.compile(pattern, re.I)))
    
    # Strategy 2: Data attributes
    containers.extend(soup.find_all(attrs={'data-event': True}))
    containers.extend(soup.find_all(attrs={'data-id': True}))
    
    # Strategy 3: Time elements (events often have dates)
    time_elements = soup.find_all('time')
    for time_elem in time_elements:
        parent = time_elem.find_parent(['div', 'article', 'section'])
        if parent and parent not in containers:
            containers.append(parent)
    
    return containers
```

### 3. Title Extraction Robustness
```python
def _extract_title(self, container, url):
    """Extract event title with multiple fallbacks"""
    # Strategy 1: Common title selectors
    title_selectors = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        '.title', '.event-title', '.name', '.heading',
        '[data-title]', '.card-title', '.post-title'
    ]
    
    for selector in title_selectors:
        title_elem = container.select_one(selector)
        if title_elem and title_elem.get_text(strip=True):
            return title_elem.get_text(strip=True)
    
    # Strategy 2: Link text
    link = container.find('a')
    if link and link.get_text(strip=True):
        return link.get_text(strip=True)
    
    # Strategy 3: First significant text
    text = container.get_text(strip=True)
    if text and len(text) > 10 and len(text) < 200:
        return text.split('\n')[0].strip()
    
    return 'Untitled Event'
```

### 4. Location Extraction
```python
def _extract_location(self, container, url):
    """Extract location with multiple strategies"""
    # Strategy 1: Common location selectors
    location_selectors = [
        '.location', '.venue', '.address', '.place',
        '.where', '.site', '.location-name'
    ]
    
    for selector in location_selectors:
        loc_elem = container.select_one(selector)
        if loc_elem and loc_elem.get_text(strip=True):
            return loc_elem.get_text(strip=True)
    
    # Strategy 2: Address elements
    address = container.find('address')
    if address:
        return address.get_text(strip=True)
    
    # Strategy 3: Extract from description
    desc = self._extract_description(container, url)
    if desc:
        # Look for location patterns in description
        location_patterns = [
            r'at\s+([A-Z][^,]+)',
            r'in\s+([A-Z][^,]+)',
            r'@\s+([A-Z][^,]+)'
        ]
        for pattern in location_patterns:
            match = re.search(pattern, desc, re.I)
            if match:
                return match.group(1).strip()
    
    return 'Location TBD'
```

### 5. URL Extraction
```python
def _extract_url(self, container, base_url):
    """Extract event URL with proper handling"""
    # Strategy 1: Direct link
    link = container.find('a', href=True)
    if link:
        href = link['href']
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            from urllib.parse import urljoin
            return urljoin(base_url, href)
        else:
            return f"{base_url.rstrip('/')}/{href}"
    
    # Strategy 2: Data attributes
    data_url = container.get('data-url') or container.get('data-href')
    if data_url:
        if data_url.startswith('http'):
            return data_url
        else:
            from urllib.parse import urljoin
            return urljoin(base_url, data_url)
    
    return base_url
```

### 6. Smart Fallback Dates
```python
def _get_smart_fallback_date(self, title: str, description: str) -> str:
    """Get intelligent fallback dates based on context"""
    from datetime import datetime, timedelta
    
    text = (title + ' ' + description).lower()
    
    # Extract year
    year_match = re.search(r'\b(20\d{2})\b', text)
    year = year_match.group(1) if year_match else str(datetime.now().year)
    
    # Extract month
    month_patterns = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    
    for month_name, month_num in month_patterns.items():
        if month_name in text:
            return f"{year}-{month_num}-15T12:00:00"
    
    # Context-specific fallbacks
    if 'brookings' in text:
        # Brookings events typically monthly
        next_month = datetime.now() + timedelta(days=30)
        return next_month.strftime('%Y-%m-%dT12:00:00')
    
    if 'wharf' in text and 'oktoberfest' in text:
        return f"{year}-10-15T12:00:00"
    
    if 'wharf' in text and 'dia de los muertos' in text:
        return f"{year}-11-02T12:00:00"
    
    if 'wharf' in text and 'holiday' in text:
        return f"{year}-12-15T12:00:00"
    
    # Generic fallback
    return (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%dT12:00:00')
```

## Future-Proofing Strategies

### 1. New Website Detection
```python
def detect_scraping_strategy(self, url: str) -> str:
    """Detect the best scraping strategy for a URL"""
    domain = urlparse(url).netloc.lower()
    
    # Known patterns
    if 'shopify' in domain or 'runpacers.com' in domain:
        return 'shopify_events'
    
    if 'districtfray.com' in domain:
        return 'district_fray_events'
    
    if 'aspeninstitute.org' in domain:
        return 'javascript_heavy'
    
    # Auto-detect based on content
    try:
        response = self.session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for "load more" buttons
        load_more = soup.find_all(['button', 'a'], 
                                 text=re.compile(r'load more|show more|see more', re.I))
        if load_more:
            return 'infinite_scroll'
        
        # Check for pagination
        pagination = soup.find_all(['a', 'button'], 
                                 text=re.compile(r'next|page \d+|more', re.I))
        if pagination:
            return 'pagination'
        
        # Check for JavaScript-heavy content
        scripts = soup.find_all('script')
        if len(scripts) > 10:
            return 'javascript_heavy'
        
        return 'static_html'
        
    except Exception:
        return 'static_html'
```

### 2. Error Handling and Recovery
```python
def extract_events(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
    """Extract events with fallback strategies"""
    strategy = self.detect_scraping_strategy(url)
    
    try:
        # Try primary strategy
        events = self.scraping_strategies[strategy](url, selector_config)
        if events:
            return events
    except Exception as e:
        logger.warning(f"Primary strategy {strategy} failed: {e}")
    
    # Fallback to static HTML
    try:
        events = self._scrape_static_html(url, selector_config)
        if events:
            logger.info(f"Fallback to static HTML successful: {len(events)} events")
            return events
    except Exception as e:
        logger.error(f"All strategies failed: {e}")
    
    return []
```

### 3. Data Validation
```python
def _validate_event(self, event: ScrapedEvent) -> ScrapedEvent:
    """Validate and clean event data"""
    # Ensure required fields
    if not event.title or event.title.strip() == '':
        event.title = 'Untitled Event'
    
    if not event.start_datetime or event.start_datetime == 'Invalid Date':
        event.start_datetime = self._get_smart_fallback_date(event.title, event.description)
    
    if not event.location_name or event.location_name.strip() == '':
        event.location_name = 'Location TBD'
    
    if not event.url or event.url.strip() == '':
        event.url = self.base_url
    
    # Clean up text fields
    event.title = event.title.strip()
    event.description = (event.description or '').strip()
    event.location_name = event.location_name.strip()
    
    return event
```

## Implementation Checklist

### ✅ Completed
- [x] Enhanced date parsing with @ symbol handling
- [x] District Fray specialized scraper
- [x] Pacers Running Shopify scraper
- [x] Aspen Institute JavaScript scraper
- [x] Smart fallback dates
- [x] Event deduplication
- [x] Error handling and logging

### 🔄 To Implement
- [ ] Universal container detection
- [ ] Enhanced title extraction
- [ ] Improved location extraction
- [ ] URL extraction robustness
- [ ] Data validation pipeline
- [ ] Strategy auto-detection
- [ ] Fallback mechanisms

## Testing Protocol

### 1. New Website Testing
```python
def test_new_website(url: str):
    """Test scraper on a new website"""
    scraper = EnhancedWebScraper()
    
    print(f"Testing: {url}")
    events = scraper.extract_events(url)
    
    print(f"Found {len(events)} events:")
    for i, event in enumerate(events[:5]):
        print(f"{i+1}. {event.title}")
        print(f"   Date: {event.start_datetime}")
        print(f"   Location: {event.location_name}")
        print(f"   URL: {event.url}")
        print()
    
    return events
```

### 2. Validation Checks
- [ ] All events have valid titles
- [ ] All events have parseable dates
- [ ] All events have locations (or "Location TBD")
- [ ] All events have valid URLs
- [ ] No duplicate events
- [ ] No generic titles like "Events" or "More"

## Maintenance Guidelines

### 1. Regular Monitoring
- Check scraper logs weekly for errors
- Monitor event counts for significant changes
- Test new websites before adding to production

### 2. Website Changes
- When a scraper stops working, check if the website structure changed
- Update selectors and patterns as needed
- Test thoroughly before deploying changes

### 3. Performance Optimization
- Monitor scraping times
- Implement caching where appropriate
- Use appropriate delays between requests

## Conclusion

This universal scraper enhancement provides a robust foundation for handling various website formats and edge cases. The modular approach allows for easy extension and maintenance as new websites are added to the system.

The key principles are:
1. **Multiple fallback strategies** for each extraction method
2. **Smart date parsing** with context-aware fallbacks
3. **Robust error handling** with graceful degradation
4. **Comprehensive validation** of extracted data
5. **Easy testing and debugging** capabilities

By following these guidelines, the scraper will be able to handle most website formats and adapt to changes over time.