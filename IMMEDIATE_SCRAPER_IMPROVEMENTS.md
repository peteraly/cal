# 🚀 **IMMEDIATE SCRAPER IMPROVEMENTS - QUICK WINS**

## 🎯 **OBJECTIVE**

Implement immediate improvements to make the current scraper more robust and adaptable to different website formats, building on the existing system.

## 📋 **CURRENT STATUS**

### **✅ What's Working:**
- Enhanced web scraper with multiple strategies
- Specialized scrapers for Aspen Institute and Pacers Running
- Robust error handling and logging
- Smart date parsing with fallbacks
- Deduplication logic

### **🔧 Quick Improvements Needed:**
- More generic pattern recognition
- Better fallback mechanisms
- Enhanced error recovery
- Improved strategy detection

## 🛠️ **IMMEDIATE IMPLEMENTATION PROMPT**

### **PROMPT FOR CURSOR:**

```
Enhance the existing enhanced_web_scraper.py to be more universal and adaptable. Implement these specific improvements to make it work across different website formats:

## 1. ENHANCE GENERIC PATTERN RECOGNITION

### Update `_scrape_static_html` method:
```python
def _scrape_static_html(self, url: str, selector_config: Dict = None) -> List[ScrapedEvent]:
    """Enhanced static HTML scraping with universal patterns"""
    try:
        logger.info("🔍 Starting enhanced static HTML scraping")
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        events = []
        
        # Universal event container detection
        event_containers = self._detect_event_containers_universal(soup)
        logger.info(f"🎯 Found {len(event_containers)} potential event containers")
        
        for container in event_containers:
            event = self._extract_event_universal(container, url)
            if event and event.title:
                events.append(event)
        
        # Remove duplicates and filter quality
        events = self._deduplicate_and_filter_events(events)
        logger.info(f"📊 Static HTML scraping found {len(events)} events")
        return events
        
    except Exception as e:
        logger.error(f"Error in static HTML scraping: {e}")
        return []
```

### Add universal container detection:
```python
def _detect_event_containers_universal(self, soup) -> List:
    """Detect event containers using universal patterns"""
    containers = []
    
    # Comprehensive selector patterns
    selectors = [
        # Event-specific classes
        '[class*="event"]', '[class*="card"]', '[class*="item"]',
        '[class*="listing"]', '[class*="post"]', '[class*="article"]',
        '[class*="tile"]', '[class*="block"]', '[class*="entry"]',
        '[class*="upcoming"]', '[class*="calendar"]', '[class*="schedule"]',
        
        # Semantic HTML
        'article', 'section[class*="event"]', 'div[role="article"]',
        'div[role="listitem"]', 'li[class*="event"]',
        
        # Framework-specific patterns
        '.event-item', '.event-card', '.event-listing', '.event-detail',
        '.calendar-event', '.upcoming-event', '.event-block',
        '.event-tile', '.event-entry', '.event-post',
        
        # Generic content patterns
        '.content-item', '.list-item', '.grid-item', '.card-item',
        '.item-card', '.content-card', '.info-card'
    ]
    
    for selector in selectors:
        try:
            found = soup.select(selector)
            if found:
                containers.extend(found)
        except Exception as e:
            logger.warning(f"Selector {selector} failed: {e}")
            continue
    
    # Remove duplicates and filter by content
    containers = self._deduplicate_containers(containers)
    containers = self._filter_containers_by_content(containers)
    
    return containers
```

## 2. IMPLEMENT UNIVERSAL EVENT EXTRACTION

### Add universal event extraction:
```python
def _extract_event_universal(self, container, base_url: str) -> ScrapedEvent:
    """Extract event data using universal patterns"""
    try:
        # Extract title using multiple strategies
        title = self._extract_title_universal(container)
        if not title or len(title.strip()) < 3:
            return None
        
        # Extract date using multiple strategies
        date = self._extract_date_universal(container, base_url, title)
        
        # Extract description
        description = self._extract_description_universal(container)
        
        # Extract location
        location = self._extract_location_universal(container, description)
        
        # Extract URL
        event_url = self._extract_url_universal(container, base_url)
        
        # Extract price information
        price_info = self._extract_price_universal(container)
        
        return ScrapedEvent(
            title=title,
            description=description,
            start_datetime=date,
            location_name=location,
            url=event_url,
            price_info=price_info,
            source=base_url
        )
        
    except Exception as e:
        logger.warning(f"Error extracting event from container: {e}")
        return None
```

### Add universal title extraction:
```python
def _extract_title_universal(self, container) -> str:
    """Extract title using multiple strategies"""
    title_selectors = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        '.title', '.event-title', '.card-title', '.item-title',
        '.heading', '.event-heading', '.card-heading',
        '[class*="title"]', '[class*="heading"]',
        'a[title]', 'a[aria-label]'
    ]
    
    for selector in title_selectors:
        try:
            element = container.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                if title and len(title) > 3:
                    return title
        except Exception:
            continue
    
    # Fallback: use container text
    text = container.get_text(strip=True)
    if text:
        # Take first line or first 100 characters
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if len(line) > 3 and len(line) < 200:
                return line
    
    return None
```

### Add universal date extraction:
```python
def _extract_date_universal(self, container, base_url: str, title: str) -> str:
    """Extract date using multiple strategies"""
    # Strategy 1: Look for date elements
    date_selectors = [
        '.date', '.event-date', '.card-date', '.item-date',
        '.time', '.event-time', '.datetime', '.event-datetime',
        '[class*="date"]', '[class*="time"]', '[datetime]',
        'time', 'abbr[title]'
    ]
    
    for selector in date_selectors:
        try:
            element = container.select_one(selector)
            if element:
                date_text = element.get_text(strip=True)
                if not date_text and element.get('datetime'):
                    date_text = element.get('datetime')
                if not date_text and element.get('title'):
                    date_text = element.get('title')
                
                if date_text:
                    parsed_date = self._parse_date_flexible(date_text)
                    if parsed_date:
                        return parsed_date
        except Exception:
            continue
    
    # Strategy 2: Extract from URL
    url_date = self._extract_date_from_url(base_url)
    if url_date:
        return url_date
    
    # Strategy 3: Extract from title
    title_date = self._extract_date_from_text(title)
    if title_date:
        return title_date
    
    # Strategy 4: Extract from container text
    container_text = container.get_text()
    text_date = self._extract_date_from_text(container_text)
    if text_date:
        return text_date
    
    # Strategy 5: Smart fallback
    return self._get_smart_fallback_date(title, container_text)
```

## 3. ENHANCE STRATEGY DETECTION

### Update strategy detection:
```python
def detect_scraping_strategy(self, url: str, html_content: str = '') -> str:
    """Enhanced strategy detection with more indicators"""
    if not html_content:
        try:
            response = self.session.get(url, timeout=10)
            html_content = response.text
        except:
            return 'static_html'
    
    html_lower = html_content.lower()
    
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
    
    # Special cases
    if 'aspeninstitute.org' in url:
        return 'javascript_heavy'
    if 'runpacers.com' in url:
        return 'shopify_events'
    
    # Return strategy with highest score
    best_strategy = max(scores, key=scores.get) if scores else 'static_html'
    
    # If no clear winner, try static_html first
    if scores[best_strategy] == 0:
        return 'static_html'
    
    logger.info(f"🎯 Detected strategy: {best_strategy} (score: {scores[best_strategy]})")
    return best_strategy
```

## 4. IMPLEMENT COMPREHENSIVE FALLBACKS

### Add comprehensive fallback system:
```python
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
```

## 5. ADD QUALITY FILTERING

### Add event quality filtering:
```python
def _deduplicate_and_filter_events(self, events: List[ScrapedEvent]) -> List[ScrapedEvent]:
    """Remove duplicates and filter by quality"""
    if not events:
        return []
    
    # Remove duplicates by title and date
    seen = set()
    unique_events = []
    
    for event in events:
        key = (event.title.lower().strip(), event.start_datetime)
        if key not in seen:
            seen.add(key)
            unique_events.append(event)
    
    # Filter by quality
    quality_events = []
    for event in unique_events:
        if self._is_quality_event(event):
            quality_events.append(event)
    
    logger.info(f"📊 Filtered {len(events)} events to {len(quality_events)} quality events")
    return quality_events

def _is_quality_event(self, event: ScrapedEvent) -> bool:
    """Check if event meets quality standards"""
    # Must have title
    if not event.title or len(event.title.strip()) < 3:
        return False
    
    # Must have date
    if not event.start_datetime:
        return False
    
    # Filter out generic titles
    generic_titles = [
        'event', 'events', 'upcoming events', 'calendar',
        'schedule', 'more info', 'learn more', 'read more',
        'click here', 'view details', 'details'
    ]
    
    if event.title.lower().strip() in generic_titles:
        return False
    
    # Filter out very short or very long titles
    if len(event.title) < 5 or len(event.title) > 200:
        return False
    
    return True
```

## 6. IMPLEMENT ERROR RECOVERY

### Add error recovery mechanisms:
```python
def extract_events(self, url: str) -> List[ScrapedEvent]:
    """Enhanced event extraction with error recovery"""
    try:
        # Try primary strategy
        strategy = self.detect_scraping_strategy(url)
        logger.info(f"🎯 Using strategy: {strategy}")
        
        if strategy in self.scraping_strategies:
            events = self.scraping_strategies[strategy](url)
            if events:
                return events
        
        # If primary strategy fails, try fallback strategies
        fallback_strategies = ['static_html', 'generic_pattern_matching']
        
        for fallback_strategy in fallback_strategies:
            try:
                logger.info(f"🔄 Trying fallback strategy: {fallback_strategy}")
                events = self.scraping_strategies[fallback_strategy](url)
                if events:
                    logger.info(f"✅ Fallback strategy succeeded: {fallback_strategy}")
                    return events
            except Exception as e:
                logger.warning(f"Fallback strategy {fallback_strategy} failed: {e}")
                continue
        
        # Ultimate fallback: minimal extraction
        logger.warning("🚨 All strategies failed, attempting minimal extraction")
        return self._minimal_extraction(url)
        
    except Exception as e:
        logger.error(f"Error in extract_events: {e}")
        return []

def _minimal_extraction(self, url: str) -> List[ScrapedEvent]:
    """Minimal extraction as last resort"""
    try:
        response = self.session.get(url, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract page title as event title
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            if title_text and len(title_text) > 3:
                return [ScrapedEvent(
                    title=title_text,
                    description=f"Event from {url}",
                    start_datetime=self._get_smart_fallback_date(title_text, ''),
                    location_name='',
                    url=url,
                    source=url
                )]
        
        return []
    except Exception as e:
        logger.error(f"Minimal extraction failed: {e}")
        return []
```

## 7. ADD COMPREHENSIVE LOGGING

### Enhance logging for debugging:
```python
def _log_scraping_attempt(self, url: str, strategy: str, success: bool, events_found: int, error: str = None):
    """Log scraping attempt for analysis"""
    log_entry = {
        'url': url,
        'strategy': strategy,
        'success': success,
        'events_found': events_found,
        'timestamp': datetime.now().isoformat(),
        'error': error
    }
    
    logger.info(f"📊 Scraping attempt: {json.dumps(log_entry)}")
    
    # Store in database for analysis
    try:
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scraper_attempts (url, strategy, success, events_found, error, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (url, strategy, success, events_found, error, datetime.now()))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to log scraping attempt: {e}")
```

## IMPLEMENTATION CHECKLIST:

- [ ] Update `_scrape_static_html` with universal patterns
- [ ] Add `_detect_event_containers_universal` method
- [ ] Implement `_extract_event_universal` method
- [ ] Add universal title, date, and location extraction
- [ ] Enhance strategy detection with more indicators
- [ ] Implement comprehensive fallback system
- [ ] Add quality filtering and deduplication
- [ ] Implement error recovery mechanisms
- [ ] Add comprehensive logging
- [ ] Test with various website types

## EXPECTED RESULTS:

1. **Better Compatibility**: Works with more website types
2. **Higher Success Rate**: >90% success rate across different sites
3. **Improved Quality**: Better event data extraction
4. **Enhanced Reliability**: Robust error handling and recovery
5. **Better Debugging**: Comprehensive logging for troubleshooting

This enhanced scraper will be much more universal and adaptable to different website formats while maintaining the existing specialized scrapers for optimal performance.
```

## 🎯 **IMMEDIATE ACTION ITEMS**

### **For Cursor to Implement:**

1. **Enhance `_scrape_static_html`** with universal pattern recognition
2. **Add `_detect_event_containers_universal`** method for better container detection
3. **Implement `_extract_event_universal`** for robust event extraction
4. **Enhance strategy detection** with more indicators and patterns
5. **Add comprehensive fallback system** for maximum reliability
6. **Implement quality filtering** to ensure high-quality events
7. **Add error recovery mechanisms** for better resilience
8. **Enhance logging** for better debugging and analysis

### **Key Improvements:**

- ✅ **Universal Pattern Recognition**: Works with any website structure
- ✅ **Enhanced Strategy Detection**: Better automatic strategy selection
- ✅ **Comprehensive Fallbacks**: Multiple fallback mechanisms
- ✅ **Quality Filtering**: Ensures high-quality event data
- ✅ **Error Recovery**: Robust error handling and recovery
- ✅ **Better Logging**: Comprehensive debugging information

### **Expected Results:**

- 🚀 **Higher Success Rate**: >90% success across different sites
- 🔧 **Better Compatibility**: Works with more website types
- 📊 **Improved Quality**: Better event data extraction
- 🛡️ **Enhanced Reliability**: Robust error handling
- 🔍 **Better Debugging**: Comprehensive logging and analysis

**These improvements will make your scraper much more universal and adaptable to different website formats!** 🎯
