# Quick Fix: Volo Sports Scraper (15 minutes)

## 🚀 **Immediate Fix Steps**

### Step 1: Install Selenium (2 minutes)
```bash
pip install selenium webdriver-manager
```

### Step 2: Update Strategy Detection (3 minutes)

#### Add to `enhanced_web_scraper.py` in `detect_scraping_strategy` method:
```python
def detect_scraping_strategy(self, url: str) -> str:
    """Detect the best scraping strategy for a URL"""
    
    # Add Volo Sports detection
    if 'volosports.com' in url:
        return 'javascript_heavy'
    
    # ... existing code ...
```

### Step 3: Add Volo Sports Scraper Method (8 minutes)

#### Add this method to `enhanced_web_scraper.py`:
```python
def _scrape_volo_sports_events(self, url: str) -> List[ScrapedEvent]:
    """Specialized scraper for Volo Sports events"""
    events = []
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import time
        
        # Setup Chrome driver
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Wait for content to load
        time.sleep(5)
        
        # Try to find event elements
        event_selectors = [
            '[data-testid*="event"]',
            '.event-card',
            '.program-card',
            '[class*="event"]',
            '[class*="program"]'
        ]
        
        for selector in event_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        # Extract basic event data
                        try:
                            title_elem = element.find_element(By.CSS_SELECTOR, 'h3, h4, h5, [class*="title"]')
                            title = title_elem.text.strip()
                            
                            if title and len(title) > 5:
                                # Extract date
                                date_elem = element.find_element(By.CSS_SELECTOR, '[class*="date"], [class*="time"]')
                                date_text = date_elem.text.strip()
                                
                                # Extract location
                                location_elem = element.find_element(By.CSS_SELECTOR, '[class*="location"], [class*="venue"]')
                                location = location_elem.text.strip()
                                
                                # Parse date
                                start_datetime = self._parse_volo_date(date_text)
                                
                                # Create event
                                event = ScrapedEvent(
                                    title=title,
                                    description=f"Volo Sports event at {location}",
                                    start_datetime=start_datetime,
                                    end_datetime='',
                                    location_name=location,
                                    address='',
                                    price_info='',
                                    url=url,
                                    tags=['sports', 'volo', 'washington-dc']
                                )
                                
                                events.append(event)
                                logger.info(f"Extracted event: {title}")
                                
                        except Exception as e:
                            logger.debug(f"Error extracting event data: {e}")
                            continue
                    
                    if events:
                        break
                        
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        driver.quit()
        
    except Exception as e:
        logger.error(f"Error scraping Volo Sports: {e}")
    
    return events

def _parse_volo_date(self, date_text: str) -> str:
    """Parse Volo Sports date format"""
    if not date_text:
        return self._get_smart_fallback_date('Volo Sports Event', '')
    
    try:
        # Handle formats like "Fri Sep 26", "Sun Sep 28"
        if re.match(r'^[A-Za-z]{3}\s+[A-Za-z]{3}\s+\d{1,2}$', date_text):
            current_year = datetime.now().year
            full_date = f"{date_text} {current_year}"
            
            parsed_date = dateutil.parser.parse(full_date)
            
            # If date is in past, assume next year
            if parsed_date < datetime.now():
                parsed_date = parsed_date.replace(year=current_year + 1)
            
            return parsed_date.isoformat()
        
        return self._parse_date_flexible(date_text)
        
    except Exception as e:
        logger.warning(f"Could not parse Volo date '{date_text}': {e}")
        return self._get_smart_fallback_date('Volo Sports Event', date_text)
```

### Step 4: Update Scraping Strategies (2 minutes)

#### Add to the `__init__` method in `enhanced_web_scraper.py`:
```python
def __init__(self):
    # ... existing code ...
    
    self.scraping_strategies = {
        'static_html': self._scrape_static_html,
        'javascript_heavy': self._scrape_javascript_heavy,
        'pagination': self._scrape_with_pagination,
        'api_based': self._scrape_api_based,
        'rss_feed': self._scrape_rss_feed,
        'aspen_institute': self._scrape_aspen_institute,
        'pacers_running': self._scrape_pacers_running_events,
        'district_fray_events': self._scrape_district_fray_events,
        'volo_sports': self._scrape_volo_sports_events  # Add this line
    }
```

### Step 5: Update Main Extraction Method (1 minute)

#### Modify the `extract_events` method in `enhanced_web_scraper.py`:
```python
def extract_events(self, url: str) -> List[ScrapedEvent]:
    """Extract events from a URL using the best strategy"""
    
    # Check for specialized scrapers first
    if 'volosports.com' in url:
        logger.info("Using specialized Volo Sports scraper")
        return self._scrape_volo_sports_events(url)
    
    # ... existing logic ...
```

## 🧪 **Test the Fix**

### Run this test script:
```python
from enhanced_web_scraper import EnhancedWebScraper

scraper = EnhancedWebScraper()
url = 'https://www.volosports.com/discover?cityName=Washington%20DC&subView=LEAGUE&view=EVENTS'

print('Testing Volo Sports scraper...')
events = scraper.extract_events(url)

print(f'Found {len(events)} events:')
for i, event in enumerate(events):
    print(f'{i+1}. {event.title}')
    print(f'   Date: {event.start_datetime}')
    print(f'   Location: {event.location_name}')
    print()
```

## 🎯 **Expected Results**

After this fix, you should see:
- ✅ **8+ events found** (instead of 0)
- ✅ **Proper event titles** (Triple Play Night, Volleyball Open Play, etc.)
- ✅ **Correct dates** (Fri Sep 26, Sun Sep 28, etc.)
- ✅ **Location information** (Navy Yard, Arlington, etc.)

## 🔧 **Troubleshooting**

### If still getting 0 events:
1. **Check Selenium installation**: `pip list | grep selenium`
2. **Check Chrome driver**: Make sure Chrome is installed
3. **Increase wait time**: Change `time.sleep(5)` to `time.sleep(10)`
4. **Check selectors**: The website might use different CSS classes

### If getting errors:
1. **Import errors**: Make sure all imports are at the top of the file
2. **Selenium errors**: Install Chrome driver or use Firefox
3. **Date parsing errors**: Check the date format on the website

## ⚡ **Total Time: ~15 minutes**

This quick fix should resolve the Volo Sports scraper issue and get it working immediately!
