# 🔧 Scraper Fix Prompt - Pacers Running & Future Issues

## 🚨 Current Issue
**Pacers Running scraper** (https://runpacers.com/pages/events) is showing:
- ✅ **Strategy detected**: `api_endpoints` 
- ❌ **Events found**: 0 events
- ❌ **Status**: "No events found yet"

## 🎯 **PROMPT FOR CURSOR TO FIX THIS NOW AND FOR THE FUTURE**

### **IMMEDIATE FIX NEEDED:**

```markdown
# Fix Pacers Running Scraper - Zero Events Issue

## Problem Analysis:
The Pacers Running scraper at https://runpacers.com/pages/events is detecting the correct strategy (api_endpoints) but finding 0 events. This suggests:

1. **API endpoint detection is working** ✅
2. **Event extraction logic is failing** ❌
3. **Need to investigate the actual API structure**

## Required Actions:

### 1. **Investigate the Website Structure**
- Visit https://runpacers.com/pages/events manually
- Check if it's a JavaScript-heavy site that loads events dynamically
- Look for actual API endpoints in Network tab
- Identify the correct selectors for event containers

### 2. **Update Enhanced Web Scraper**
- Add specific handling for `runpacers.com` in `enhanced_web_scraper.py`
- Create a specialized scraping method for this site
- Test different strategies: `static_html`, `javascript_heavy`, `pagination`

### 3. **Debug the Current Scraper**
- Add detailed logging to see what the scraper is actually finding
- Check if the API endpoint detection is correct
- Verify the event extraction logic

### 4. **Create Fallback Strategies**
- If API endpoints don't work, try static HTML scraping
- If static HTML doesn't work, try JavaScript-heavy approach
- Add specific selectors for Pacers Running events

## Implementation Steps:

### Step 1: Manual Investigation
```bash
# Check the website structure
curl -s "https://runpacers.com/pages/events" | grep -i "event"
```

### Step 2: Update Enhanced Scraper
Add to `enhanced_web_scraper.py`:
```python
def _scrape_pacers_running(self, url):
    """Specialized scraper for Pacers Running events"""
    try:
        # Try different approaches
        # 1. Check if it's a Shopify store
        # 2. Look for specific event containers
        # 3. Try different selectors
        pass
    except Exception as e:
        logger.error(f"Error scraping Pacers Running: {e}")
        return []
```

### Step 3: Add Debug Logging
```python
# Add detailed logging to see what's happening
logger.info(f"Pacers Running - URL: {url}")
logger.info(f"Pacers Running - Response status: {response.status_code}")
logger.info(f"Pacers Running - Content length: {len(response.text)}")
logger.info(f"Pacers Running - Found containers: {len(containers)}")
```

### Step 4: Test Different Strategies
```python
# Force different strategies for testing
strategies_to_try = ['static_html', 'javascript_heavy', 'pagination']
for strategy in strategies_to_try:
    result = self._try_strategy(strategy, url)
    if result:
        return result
```

## Expected Outcome:
- Pacers Running scraper should find and extract events
- Detailed logging should show what's happening
- Fallback strategies should work if primary method fails

## Future Prevention:
- Add comprehensive logging to all scrapers
- Create specialized methods for common website types
- Implement fallback strategies for all scrapers
- Add monitoring for zero-event scrapers
```

## 🔧 **IMMEDIATE DEBUGGING STEPS**

### 1. **Check the Website Manually**
```bash
# Test the website directly
curl -s "https://runpacers.com/pages/events" | head -50
```

### 2. **Add Debug Logging**
Add this to the enhanced scraper to see what's happening:

```python
def _scrape_with_api_endpoints(self, url):
    """Enhanced API endpoint scraping with debug logging"""
    logger.info(f"🔍 API Scraping: {url}")
    
    try:
        response = requests.get(url, headers=self.headers, timeout=30)
        logger.info(f"📊 Response Status: {response.status_code}")
        logger.info(f"📊 Content Length: {len(response.text)}")
        
        # Check if it's a Shopify store
        if 'shopify' in response.text.lower():
            logger.info("🏪 Detected Shopify store")
            return self._scrape_shopify_events(url)
        
        # Check for common event patterns
        soup = BeautifulSoup(response.text, 'html.parser')
        event_containers = soup.find_all(['div', 'article', 'section'], 
                                       class_=re.compile(r'event|card|item', re.I))
        logger.info(f"🎯 Found {len(event_containers)} potential event containers")
        
        if len(event_containers) == 0:
            # Try alternative selectors
            event_containers = soup.find_all(['div', 'article'], 
                                           class_=re.compile(r'product|listing|grid', re.I))
            logger.info(f"🔄 Alternative selectors found {len(event_containers)} containers")
        
        return self._extract_events_from_containers(event_containers, url)
        
    except Exception as e:
        logger.error(f"❌ API scraping error: {e}")
        return []
```

### 3. **Create Shopify-Specific Scraper**
```python
def _scrape_shopify_events(self, url):
    """Specialized scraper for Shopify-based event pages"""
    try:
        # Shopify stores often use specific patterns
        # Look for product/event JSON data
        # Check for AJAX endpoints
        pass
    except Exception as e:
        logger.error(f"Shopify scraping error: {e}")
        return []
```

## 🚀 **QUICK FIX COMMAND**

Run this to test the website and get debug info:

```bash
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"
source venv/bin/activate

# Test the website directly
curl -s "https://runpacers.com/pages/events" | grep -i "event\|product\|card" | head -10

# Check if it's a Shopify store
curl -s "https://runpacers.com/pages/events" | grep -i "shopify" | head -5

# Test the scraper with debug logging
python3 -c "
from enhanced_web_scraper import EnhancedWebScraper
scraper = EnhancedWebScraper()
result = scraper.scrape_website('https://runpacers.com/pages/events')
print(f'Found {len(result)} events')
for event in result[:3]:
    print(f'- {event.get(\"title\", \"No title\")}')
"
```

## 📋 **CHECKLIST FOR FUTURE SCRAPER ISSUES**

### When a scraper shows 0 events:

1. **✅ Check website manually** - Visit the URL and see what's there
2. **✅ Test different strategies** - Try static_html, javascript_heavy, pagination
3. **✅ Add debug logging** - See what the scraper is actually finding
4. **✅ Check for common patterns** - Shopify, WordPress, custom APIs
5. **✅ Test selectors** - Verify event container selectors are correct
6. **✅ Add fallback methods** - Create specialized scrapers for common site types
7. **✅ Monitor results** - Set up alerts for zero-event scrapers

## 🎯 **EXPECTED RESULT**

After implementing these fixes:
- ✅ Pacers Running scraper should find events
- ✅ Detailed logging should show the scraping process
- ✅ Fallback strategies should work for similar sites
- ✅ Future zero-event issues should be easier to debug

## 🔄 **CONTINUOUS MONITORING**

Add this to your admin interface:
- Alert when any scraper finds 0 events
- Show last successful scrape date
- Provide manual testing tools for each scraper
- Display detailed logs for debugging

**This prompt will help fix the current issue and prevent similar problems in the future!** 🚀
