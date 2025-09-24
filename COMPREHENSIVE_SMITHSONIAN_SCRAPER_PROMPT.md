# Comprehensive Smithsonian Event Scraper: Multi-Month Calendar Solution

## Problem Statement

The [Smithsonian main events page](https://www.si.edu/events) displays events in a **daily paginated calendar format**:
- Shows only ONE day at a time (e.g., Tuesday, September 23, 2025)
- Requires clicking "Previous Page/Next Page" to see other days
- Contains 13+ events per day across multiple museums
- Spans multiple months (September 2025 → December 2025 and beyond)

**Current Issue**: Scraper only captures 1 day's events, missing hundreds of events across the full calendar.

**Goal**: Capture ALL events from ALL days across the entire Smithsonian calendar system.

## Technical Analysis

### Calendar Structure
```
https://www.si.edu/events → Single day view (default: today)
- Previous Page/Next Page navigation
- Events span: American Art Museum, Natural History, Air & Space, etc.
- 10-15 events per day average
- Need to traverse entire calendar programmatically
```

### Sample Events from One Day (Sept 23, 2025):
- Art in the A.M. (American Art Museum, 9 AM)
- Little Critters: Nature Play (National Zoo, 9:30 AM)
- Play Date at NMNH: Colorful Corals (Natural History, 10:30 AM)
- Flights of Fancy Story Time (Air & Space, 11 AM)
- **13+ more events that day alone**

## Implementation Strategy

### Phase 1: Calendar Date Range Discovery
```python
def discover_calendar_range():
    """
    1. Parse main calendar page to find date range
    2. Identify earliest and latest available dates
    3. Generate all dates between start/end
    4. Account for different URL patterns for date navigation
    """
    base_url = "https://www.si.edu/events"
    
    # Test URL patterns:
    # https://www.si.edu/events?date=2025-09-23
    # https://www.si.edu/events/2025/09/23
    # https://www.si.edu/events?day=23&month=09&year=2025
```

### Phase 2: Multi-Day Traversal
```python
def scrape_all_calendar_days(start_date, end_date):
    """
    1. Generate all dates in range
    2. For each date, construct URL and scrape events
    3. Handle pagination within each day if needed
    4. Implement delays to avoid rate limiting
    5. Retry failed requests with exponential backoff
    """
    
    events = []
    for date in date_range(start_date, end_date):
        day_url = f"https://www.si.edu/events?date={date}"
        day_events = scrape_single_day(day_url)
        events.extend(day_events)
        
        # Be respectful to servers
        time.sleep(random.uniform(1, 3))
    
    return events
```

### Phase 3: Event Data Extraction
```python
def scrape_single_day(day_url):
    """
    Extract all events from a single day's page:
    - Event title (e.g., "Art in the A.M.")
    - Time (e.g., "Tuesday, September 23, 9 a.m. EDT")
    - Museum (e.g., "Smithsonian American Art Museum")
    - Location (e.g., "Renwick Gallery, Enter via 17th Street ramp")
    - Description/Details
    """
    
    # Target selectors based on the HTML structure shown
    event_containers = soup.select('[class*="event"], .event-item, article')
    
    for container in event_containers:
        event = {
            'title': extract_title(container),
            'datetime': extract_datetime(container), 
            'museum': extract_museum(container),
            'location': extract_location(container),
            'description': extract_description(container),
            'url': extract_details_url(container)
        }
        events.append(event)
```

### Phase 4: Alternative Comprehensive Sources
```python
# If daily traversal is too slow, look for comprehensive views:
comprehensive_urls = [
    "https://www.si.edu/events/all",
    "https://www.si.edu/events/list",
    "https://www.si.edu/events?view=list",
    "https://www.si.edu/calendar/month",
    "https://www.si.edu/events.json",
    "https://www.si.edu/api/events"
]
```

## Quality Assurance Framework

### 1. Coverage Validation
```python
def validate_coverage():
    """
    Ensure we're capturing events from all major museums:
    - Natural History Museum ✓
    - American History Museum ✓  
    - Air and Space Museum ✓
    - American Art Museum ✓
    - American Indian Museum ✓
    - Asian Art Museum ✓
    - Anacostia Community Museum ✓
    - National Zoo ✓
    """
```

### 2. Date Range Monitoring
```python
def monitor_date_coverage():
    """
    Track which months we successfully scrape:
    - September 2025: X events
    - October 2025: X events
    - November 2025: X events
    - December 2025: X events
    """
```

### 3. Automated Quality Checks
```python
def quality_checks():
    """
    1. Verify event counts are reasonable (10-20 per day)
    2. Check for date parsing accuracy
    3. Validate museum names are recognized
    4. Ensure no duplicate events
    5. Confirm events span multiple months
    """
```

## Implementation Steps

### Step 1: Enhanced Calendar Scraper
Create `smithsonian_calendar_scraper.py`:
```python
class SmithsonianCalendarScraper:
    def __init__(self):
        self.base_url = "https://www.si.edu/events"
        self.session = self.setup_session()
    
    def scrape_full_calendar(self, months_ahead=3):
        """Scrape all events for next N months"""
        
    def discover_date_navigation(self):
        """Figure out how to navigate between dates"""
        
    def scrape_date_range(self, start_date, end_date):
        """Scrape all events in date range"""
        
    def parse_daily_events(self, html_content, date):
        """Parse all events from a single day's HTML"""
```

### Step 2: Integration with Existing System
```python
# Update web_scrapers table
cursor.execute('''
    UPDATE web_scrapers 
    SET url = ?, 
        description = 'Smithsonian ALL Museums - Complete Calendar (Multi-Month)',
        update_interval = 60  -- Run hourly for comprehensive coverage
    WHERE name LIKE '%Smithsonian%'
''', ('https://www.si.edu/events',))

# Modify scraper scheduler to use new comprehensive method
def enhanced_smithsonian_scrape():
    scraper = SmithsonianCalendarScraper()
    all_events = scraper.scrape_full_calendar(months_ahead=4)
    
    # Add to approval queue
    for event in all_events:
        add_to_approval_queue(event)
```

### Step 3: Monitoring & Alerting
```python
def comprehensive_scraper_health_check():
    """
    Monitor scraper performance:
    1. Events per day should be 10-20
    2. Should capture events from 8+ museums
    3. Should span 3+ months
    4. No more than 5% failed day scrapes
    """
```

## Expected Results

### Before (Current State):
- ❌ 5-13 events (single day only)
- ❌ Missing hundreds of events
- ❌ No multi-month coverage

### After (Comprehensive Solution):
- ✅ 300-500+ events (full calendar)
- ✅ Events from all Smithsonian museums
- ✅ 3-4 months of future events
- ✅ Daily automated updates

## Success Metrics

1. **Event Volume**: 200+ events per month
2. **Museum Coverage**: 8+ Smithsonian venues
3. **Date Range**: 90+ days of future events  
4. **Update Frequency**: Daily fresh event additions
5. **Data Quality**: 95%+ events with valid dates/locations

## Risk Mitigation

### Rate Limiting Protection:
- Random delays between requests (1-3 seconds)
- Respect robots.txt
- Monitor response times and back off if needed

### Error Handling:
- Retry failed date scrapes
- Log missing dates for manual review
- Graceful degradation if calendar structure changes

### Data Validation:
- Verify event dates are in future
- Check museum names against known list
- Flag suspicious events for review

## API Integration Opportunities

### Alternative Data Sources:
```python
# Check for official Smithsonian APIs
smithsonian_apis = [
    "https://api.si.edu/openaccess/api/v1.0/search",
    "https://edan.si.edu/openaccess/apidocs/",
    "https://www.si.edu/rss"  # RSS feeds by museum
]
```

This comprehensive approach will transform your Smithsonian scraping from **single-day capture** to **complete calendar coverage**, ensuring you capture ALL events across ALL museums for multiple months ahead.
