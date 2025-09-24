# Event Data Quality Issues: Analysis & Fix Plan

## 🚨 **Critical Issues Identified**

### 1. **HTML Entity Encoding Problems**
```
❌ "China&#8217;s influence in the Pacific Islands"
✅ Should be: "China's influence in the Pacific Islands"

❌ "&lt;p&gt;MEET IN THE LOBBY"
✅ Should be: "<p>MEET IN THE LOBBY" or clean text
```

### 2. **Truncated/Malformed Titles**
```
❌ "National Fossil Day at the Smithsonian National Museum of Natural History1st Flo..."
❌ "Play Date at NMNH: Awesome Arachnids!Q?rius, The Coralyn W. Whitney Science Educ..."
```

### 3. **Generic/Metadata Titles**
```
❌ "Event Date" (should be actual event name)
❌ "Events" (too generic)
❌ "Online Only" (location, not title)
```

### 4. **Duplicate Events**
- Multiple versions of same event with different discovery times
- Same content, different HTML formatting

### 5. **HTML in Content**
```
❌ "&lt;p&gt;" tags appearing in titles
❌ Raw HTML entities in descriptions
```

## 📋 **Root Causes**

1. **Web Scraper Text Extraction**: Not properly decoding HTML entities
2. **Title Length Limits**: Database or display truncating long titles
3. **Content Cleaning**: No HTML sanitization in scraping pipeline
4. **Duplicate Detection**: Not catching similar events with formatting differences
5. **Title Validation**: No validation for meaningful event names

## 🔧 **Comprehensive Fix Strategy**

### Phase 1: Immediate Text Cleanup

```python
import html
import re
from bs4 import BeautifulSoup

def clean_event_text(text):
    """Clean and normalize event text"""
    if not text:
        return text
    
    # Step 1: Decode HTML entities
    text = html.unescape(text)
    
    # Step 2: Remove/clean HTML tags
    text = BeautifulSoup(text, 'html.parser').get_text()
    
    # Step 3: Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Step 4: Fix common encoding issues
    replacements = {
        '&#8217;': "'",
        '&#8216;': "'", 
        '&#8220;': '"',
        '&#8221;': '"',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&nbsp;': ' '
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text
```

### Phase 2: Enhanced Title Validation

```python
def validate_event_title(title):
    """Validate if text is a proper event title"""
    if not title or len(title.strip()) < 5:
        return False
    
    # Exclude generic/metadata terms
    bad_titles = [
        'event date', 'event type', 'event series', 'events',
        'online only', 'main navigation', 'view details',
        'register now', 'more info'
    ]
    
    if title.lower().strip() in bad_titles:
        return False
    
    # Check for HTML artifacts
    if '<' in title or '&lt;' in title:
        return False
    
    # Check for location-only titles
    location_indicators = ['floor', 'building', 'room', 'hall', 'theater']
    if any(loc in title.lower() for loc in location_indicators) and ':' not in title:
        return False
    
    return True
```

### Phase 3: Duplicate Detection Enhancement

```python
def normalize_for_comparison(text):
    """Normalize text for duplicate detection"""
    # Remove HTML, lowercase, remove punctuation
    clean = re.sub(r'[^\w\s]', '', text.lower())
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def is_duplicate_event(title1, title2, threshold=0.8):
    """Check if two events are likely duplicates"""
    from difflib import SequenceMatcher
    
    norm1 = normalize_for_comparison(title1)
    norm2 = normalize_for_comparison(title2)
    
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold
```

## 🚀 **Implementation Script**

### Step 1: Clean Existing Events

```python
# fix_existing_events.py
import sqlite3
import html
import re
from bs4 import BeautifulSoup

def clean_existing_events():
    """Clean all existing events in database"""
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get all events that need cleaning
    cursor.execute('''
        SELECT id, title, description 
        FROM events 
        WHERE title LIKE '%&#%' 
        OR title LIKE '%&lt;%'
        OR title LIKE '%&gt;%'
        OR description LIKE '%&#%'
    ''')
    
    events_to_clean = cursor.fetchall()
    print(f"Found {len(events_to_clean)} events needing cleanup")
    
    cleaned_count = 0
    for event_id, title, description in events_to_clean:
        # Clean title
        clean_title = clean_event_text(title)
        clean_desc = clean_event_text(description) if description else description
        
        # Validate title
        if not validate_event_title(clean_title):
            print(f"Skipping invalid title: {clean_title}")
            continue
        
        # Update event
        cursor.execute('''
            UPDATE events 
            SET title = ?, description = ? 
            WHERE id = ?
        ''', (clean_title, clean_desc, event_id))
        
        cleaned_count += 1
        print(f"Cleaned: {title} → {clean_title}")
    
    conn.commit()
    conn.close()
    
    print(f"✅ Cleaned {cleaned_count} events")
```

### Step 2: Enhance Scrapers

```python
# enhanced_text_processing.py
def enhance_scraper_text_processing():
    """Add text cleaning to all scrapers"""
    
    # Update enhanced_scraper.py
    def extract_clean_text(self, element, selector):
        """Extract and clean text from element"""
        try:
            elem = element.select_one(selector)
            if elem:
                # Get text content
                text = elem.get_text(strip=True)
                
                # Clean HTML entities and normalize
                text = html.unescape(text)
                text = re.sub(r'\s+', ' ', text).strip()
                
                return text
        except:
            pass
        return ""
```

### Step 3: Prevent Future Issues

```python
# Add to scraper_scheduler.py
def validate_and_clean_scraped_events(events):
    """Validate and clean events before adding to database"""
    clean_events = []
    
    for event in events:
        # Clean title and description
        title = clean_event_text(event.get('title', ''))
        description = clean_event_text(event.get('description', ''))
        
        # Validate title
        if not validate_event_title(title):
            print(f"Rejected invalid title: {title}")
            continue
        
        # Check for duplicates against existing events
        # (implement duplicate check logic here)
        
        # Update event with cleaned data
        event['title'] = title
        event['description'] = description
        clean_events.append(event)
    
    return clean_events
```

## 🎯 **Immediate Actions Required**

### 1. **Emergency Cleanup** (Run Now)
```bash
python3 fix_existing_events.py
```

### 2. **Update Scrapers** (Prevent Future Issues)
- Add text cleaning to `enhanced_scraper.py`
- Update `scraper_scheduler.py` with validation
- Implement duplicate detection

### 3. **Database Maintenance**
```sql
-- Delete obviously bad events
DELETE FROM events 
WHERE title IN ('Event Date', 'Event Type', 'Events', 'Online Only');

-- Delete truncated titles
DELETE FROM events 
WHERE title LIKE '%...' AND length(title) < 50;
```

## 📊 **Expected Results**

### Before Fix:
- ❌ "China&#8217;s influence" (HTML entities)
- ❌ "&lt;p&gt;MEET IN THE LOBBY" (HTML tags)
- ❌ "Event Date" (metadata)
- ❌ Multiple duplicates

### After Fix:
- ✅ "China's influence in the Pacific Islands"
- ✅ "MEET IN THE LOBBY" (clean text)
- ✅ Meaningful event titles only
- ✅ No duplicates, clean formatting

## 🔄 **Ongoing Prevention**

1. **Scraper Enhancement**: All new events cleaned before database insertion
2. **Title Validation**: Reject generic/malformed titles automatically  
3. **Duplicate Detection**: Advanced similarity matching
4. **HTML Sanitization**: Strip all HTML artifacts
5. **Encoding Fixes**: Proper Unicode handling throughout pipeline

This comprehensive approach will fix existing issues and prevent future text quality problems.
