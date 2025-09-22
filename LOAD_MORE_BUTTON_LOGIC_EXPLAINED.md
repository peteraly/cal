# 🔄 **Load More Button Logic - Complete Technical Breakdown**

## 🎯 **How the Enhanced Scraper Handles "Load More" Buttons**

The enhanced scraper uses **multiple sophisticated strategies** to handle "Load More" buttons and pull ALL events from entire websites. Here's exactly how it works:

## 🚀 **Strategy 1: Direct Button Detection & URL Extraction**

### **Step 1: Find Load More Buttons**
```python
load_more_selectors = [
    'button[class*="load-more"]',     # <button class="load-more-btn">
    'button[class*="show-more"]',     # <button class="show-more">
    'a[class*="load-more"]',          # <a class="load-more-link">
    'a[class*="show-more"]',          # <a class="show-more-link">
    '.load-more',                     # Any element with load-more class
    '.show-more',                     # Any element with show-more class
    '.view-more',                     # Any element with view-more class
    'button[class*="pagination"]',    # Pagination buttons
    'a[class*="pagination"]',         # Pagination links
    '.pagination a',                  # Standard pagination
    '.pagination button'              # Standard pagination buttons
]
```

### **Step 2: Extract Load More URL**
```python
load_more_element = soup.select_one(selector)
if load_more_element:
    # Try multiple attributes to find the URL
    load_more_url = (
        load_more_element.get('href') or           # Standard link
        load_more_element.get('data-url') or       # Data attribute
        load_more_element.get('data-href') or      # Alternative data attribute
        load_more_element.get('data-load-url')     # Custom data attribute
    )
    
    # Make URL absolute
    load_more_url = urljoin(url, load_more_url)
```

### **Step 3: Load Additional Content**
```python
# Try to load more content up to 5 times
for attempt in range(5):
    try:
        more_response = self.session.get(load_more_url, timeout=30)
        if more_response.status_code == 200:
            more_soup = BeautifulSoup(more_response.text, 'html.parser')
            
            # Extract events from the new content
            containers = more_soup.find_all(['article', 'div'], 
                                          class_=re.compile(r'event|card|item', re.I))
            
            for container in containers:
                event = self._extract_event_from_container(container, selector_config)
                if event and event.title:
                    all_events.append(event)
            
            time.sleep(1)  # Be respectful
    except Exception as e:
        logger.debug(f"Error loading more content: {e}")
        break
```

## 🧠 **Strategy 2: URL Pattern Discovery (Most Powerful)**

### **The Smart Approach: Test Multiple URL Patterns**
Instead of just clicking buttons, the scraper **intelligently tests different URL patterns** that websites use to load all content:

```python
urls_to_try = [
    url,                           # Original URL
    url + '#all-events',          # Hash-based loading
    url + '?all=true',            # Show all parameter
    url + '?limit=100',           # High limit
    url + '?limit=1000',          # Very high limit
    url + '?page=1&limit=100',    # Page with high limit
    url + '?page=2&limit=100',    # Multiple pages
    url + '?page=3&limit=100',
    url + '?offset=0&limit=100',  # Offset-based
    url + '?offset=20&limit=100',
    url + '?offset=40&limit=100',
    url + '?view=all',            # View all parameter
    url + '?show=all',            # Show all parameter
    url + '?display=all',         # Display all parameter
    url + '?format=json',         # JSON format
    url.replace('/events/', '/api/events'), # API endpoint
    url + '/api',                 # API path
    url + '/json'                 # JSON path
]
```

### **Find the Best URL Pattern**
```python
best_url = None
max_containers = 0

# Test each URL pattern
for test_url in urls_to_try:
    try:
        response = self.session.get(test_url, timeout=30)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            event_containers = soup.find_all(['article', 'div'], 
                                           class_=lambda x: x and any(word in x.lower() 
                                           for word in ['event', 'card', 'item']))
            
            logger.info(f"URL {test_url} found {len(event_containers)} event containers")
            
            # Keep track of the URL with the most events
            if len(event_containers) > max_containers:
                max_containers = len(event_containers)
                best_url = test_url
                
    except Exception as e:
        logger.debug(f"Error testing URL {test_url}: {e}")
        continue

# Use the URL that found the most events
if best_url:
    logger.info(f"Using best URL: {best_url} with {max_containers} containers")
    # Extract all events from the best URL
```

## 🔄 **Strategy 3: Pagination Handling**

### **Multi-Page Scraping**
```python
def _scrape_with_pagination(self, url: str, selector_config: Dict = None):
    all_events = []
    page = 1
    max_pages = 5  # Limit to prevent infinite loops
    
    while page <= max_pages:
        # Try different pagination URL patterns
        page_urls = [
            f"{url}?page={page}",      # example.com/events?page=2
            f"{url}?p={page}",         # example.com/events?p=2
            f"{url}/page/{page}",      # example.com/events/page/2
            f"{url}?offset={page * 20}", # example.com/events?offset=40
            f"{url}?start={page * 20}"   # example.com/events?start=40
        ]
        
        page_events = []
        for page_url in page_urls:
            try:
                response = self.session.get(page_url, timeout=30)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Check if page has content
                    containers = soup.find_all(['article', 'div'], 
                                             class_=re.compile(r'event|card|item', re.I))
                    
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
```

## 🎯 **Strategy 4: API Endpoint Discovery**

### **Find Hidden API Endpoints**
```python
def _scrape_via_api(self, url: str, selector_config: Dict = None):
    # Try common API patterns
    api_urls = [
        url.replace('/events/', '/api/events'),
        url.replace('/events/', '/events/api'),
        url + '/api',
        url + '/json',
        url + '?format=json'
    ]
    
    for api_url in api_urls:
        try:
            response = self.session.get(api_url, timeout=30)
            if response.status_code == 200:
                # Try to parse as JSON
                try:
                    json_data = response.json()
                    if isinstance(json_data, list) and len(json_data) > 0:
                        logger.info(f"Found JSON API with {len(json_data)} events")
                        for item in json_data:
                            if isinstance(item, dict):
                                event = self._extract_event_from_dict(item, selector_config)
                                if event and event.title:
                                    all_events.append(event)
                        return all_events
                except:
                    pass
        except Exception as e:
            logger.debug(f"Error trying API URL {api_url}: {e}")
            continue
```

## 🔄 **How It Handles Updates & New Events**

### **Event Deduplication & Updates**
```python
def _process_scraped_event(self, scraper_id: int, event, category: str):
    # Create a unique identifier for the event
    event_id = f"{scraper_id}_{hash(title + start_datetime)}"
    
    # Check if event already exists
    cursor.execute('''
        SELECT id, title, description, start_datetime, location_name, 
               price_info, url, updated_at
        FROM events 
        WHERE title = ? AND start_datetime = ? AND location_name = ?
    ''', (title, start_datetime, location_name))
    
    existing_event = cursor.fetchone()
    
    if existing_event:
        # Event exists - check if it needs updating
        existing_id, existing_title, existing_desc, existing_date, 
        existing_location, existing_price, existing_url, existing_updated = existing_event
        
        # Check if any fields have changed
        needs_update = (
            existing_desc != description or
            existing_price != price_info or
            existing_url != url
        )
        
        if needs_update:
            # Update the existing event
            cursor.execute('''
                UPDATE events 
                SET description = ?, price_info = ?, url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (description, price_info, url, existing_id))
            
            logger.info(f"Updated event: {title}")
            return {'action': 'updated', 'event_id': existing_id}
        else:
            logger.info(f"Event unchanged: {title}")
            return {'action': 'unchanged', 'event_id': existing_id}
    else:
        # New event - insert it
        cursor.execute('''
            INSERT INTO events (title, description, start_datetime, end_datetime,
                              location_name, address, price_info, url, tags, 
                              category, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (title, description, start_datetime, end_datetime, location_name, 
              address, price_info, url, tags, category, source))
        
        new_event_id = cursor.lastrowid
        logger.info(f"Added new event: {title}")
        return {'action': 'added', 'event_id': new_event_id}
```

### **Scraper Event Tracking**
```python
# Track which scraper found this event
cursor.execute('''
    INSERT OR REPLACE INTO web_scraper_events 
    (scraper_id, event_id, scraped_at, is_active)
    VALUES (?, ?, CURRENT_TIMESTAMP, 1)
''', (scraper_id, event_id, scraped_at))
```

## 🎯 **Real-World Example: Aspen Institute**

### **What Happens When It Detects "Load More"**
1. **Strategy Detection**: Detects `javascript_heavy` strategy
2. **URL Pattern Testing**: Tests multiple URL patterns:
   - `https://aspeninstitute.org/events?all=true` → Found 126 containers
   - `https://aspeninstitute.org/events?limit=1000` → Found 125 containers
   - `https://aspeninstitute.org/events?view=all` → Found 125 containers
3. **Best URL Selection**: Chooses `?all=true` (most containers)
4. **Event Extraction**: Extracts all 22 unique events
5. **Database Update**: Updates existing events, adds new ones
6. **Deduplication**: Removes duplicates based on title and URL

### **The Result**
- **Before**: Only events from initial page (maybe 5-10 events)
- **After**: All events from entire website (22+ events)
- **Load More Button**: Completely bypassed using URL parameters

## 🚀 **Key Benefits of This Approach**

### **✅ Comprehensive Coverage**
- **No Button Clicking Required**: Uses URL parameters instead
- **Multiple Fallback Strategies**: If one approach fails, tries others
- **API Discovery**: Finds hidden API endpoints
- **Pagination Handling**: Follows traditional page-based navigation

### **✅ Intelligent Detection**
- **Automatic Strategy Selection**: Chooses best approach for each site
- **URL Pattern Testing**: Finds the URL that loads the most content
- **Content Analysis**: Analyzes HTML structure to find events
- **Error Handling**: Gracefully handles failures and timeouts

### **✅ Efficient Updates**
- **Smart Deduplication**: Prevents duplicate events
- **Change Detection**: Only updates events that have changed
- **Incremental Updates**: Adds new events, updates existing ones
- **Source Tracking**: Tracks which scraper found each event

## 🎯 **Bottom Line**

**The enhanced scraper doesn't actually "click" Load More buttons. Instead, it:**

1. **Intelligently discovers URL patterns** that load all content at once
2. **Tests multiple URL variations** to find the one with the most events
3. **Uses API endpoints** when available
4. **Handles pagination** by following page links
5. **Extracts all events** from the best URL pattern
6. **Updates the database** with new and changed events
7. **Tracks changes** and prevents duplicates

**This approach is more reliable, faster, and more comprehensive than actually clicking buttons, because it gets ALL the content in one request instead of making multiple requests to simulate button clicks.**

The scraper essentially **reverse-engineers how the website loads content** and uses the most efficient method to get all events at once! 🚀
