# Ironclad Event Scraping System: Project-Specific Implementation Guide

## 🎯 **Context: Lessons Learned from Production Issues**

Based on our calendar application's real-world challenges, this prompt addresses the **6 critical failure patterns** we've encountered and provides a bulletproof framework for prevention.

---

## 📋 **Phase 1: Date Extraction Excellence** ⭐ *Highest Priority*

### **Problem Solved**: Wrong dates causing 21-day errors (Oct 22 vs Oct 1)

**Implementation Requirements:**

```python
class PrecisionDateExtractor:
    """Bulletproof date extraction with priority hierarchy"""
    
    def extract_event_date(self, soup, url):
        """Extract dates using strict priority order"""
        
        # PRIORITY 1: JSON-LD structured data (most reliable)
        structured_date = self._extract_structured_date(soup)
        if structured_date and self._validate_future_date(structured_date):
            return structured_date
        
        # PRIORITY 2: Event-specific date elements (near titles/agenda)
        contextual_date = self._extract_contextual_date(soup)
        if contextual_date and self._validate_future_date(contextual_date):
            return contextual_date
        
        # PRIORITY 3: Time elements with datetime attributes
        time_element_date = self._extract_time_elements(soup)
        if time_element_date and self._validate_future_date(time_element_date):
            return time_element_date
        
        # PRIORITY 4: Pattern matching in text (last resort)
        text_date = self._extract_text_patterns(soup)
        if text_date and self._validate_future_date(text_date):
            return text_date
        
        # NEVER use page metadata dates (publishedDate, modifiedDate)
        # These caused our major date extraction failures
        
        return None
    
    def _validate_future_date(self, date):
        """Ensure date is not in the past (prevents contamination)"""
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=1)
        return date > cutoff
```

**Brookings-Specific Patterns** (based on our fixes):
- Handle malformed dates: `"October01202510:00 am EDT"` → `"October 1, 2025 10:00 AM"`
- Prioritize agenda sections over page headers
- Parse time ranges: `"10:00 am - 11:00 am EDT"`

---

## 🔤 **Phase 2: Bulletproof Text Processing**

### **Problem Solved**: HTML entities breaking display (`China&#8217;s` → `China's`)

**Implementation Requirements:**

```python
class ProductionTextCleaner:
    """Industrial-strength text cleaning based on real issues"""
    
    def clean_scraped_text(self, raw_text):
        """Clean text using lessons from production failures"""
        
        if not raw_text:
            return raw_text
        
        # Step 1: Decode HTML entities (critical for display)
        import html
        text = html.unescape(raw_text)
        
        # Step 2: Remove HTML tags (prevents &lt;p&gt; artifacts)
        from bs4 import BeautifulSoup
        text = BeautifulSoup(text, 'html.parser').get_text()
        
        # Step 3: Fix specific encoding issues we encountered
        replacements = {
            '&#8217;': "'",  # Apostrophes (China's issue)
            '&#8220;': '"',  # Opening quotes
            '&#8221;': '"',  # Closing quotes
            '&amp;': '&',   # Ampersands
            '&nbsp;': ' ',  # Non-breaking spaces
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Step 4: Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def validate_title_quality(self, title):
        """Prevent generic titles that caused approval queue clutter"""
        
        if not title or len(title.strip()) < 5:
            return False
        
        # Reject titles that caused our issues
        bad_titles = [
            'event date', 'event type', 'events', 'online only',
            'main navigation', 'view details', 'register now'
        ]
        
        if title.lower().strip() in bad_titles:
            return False
        
        # Reject location-only titles (caused confusion)
        location_patterns = [
            r'^\d+\w*\s+floor\s*,',     # "1st Floor, ..."
            r'^\w+\s+hall\s*$',         # "Theatre Hall"
            r'^\w+\s+building\s*$'      # "Main Building"
        ]
        
        for pattern in location_patterns:
            if re.match(pattern, title.lower()):
                return False
        
        return True
```

---

## 📊 **Phase 3: Data Pipeline Integrity**

### **Problem Solved**: Dashboard showing wrong data despite correct database

**Implementation Requirements:**

```python
class DataPipelineValidator:
    """Ensure data consistency from scraper to frontend"""
    
    def validate_api_response(self, database_row, api_response):
        """Prevent column mapping misalignment"""
        
        # Map database columns to API fields explicitly
        # (Prevents our "Every {JSON} minutes" display bug)
        expected_mapping = {
            'update_interval': database_row[6],  # Not row[5]!
            'selector_config': database_row[5],  # Not row[7]!
            'total_events': database_row[11],
            'last_run': database_row[8],
            'consecutive_failures': database_row[10]
        }
        
        # Validate each field matches expectation
        for field, expected_value in expected_mapping.items():
            if api_response.get(field) != expected_value:
                raise DataIntegrityError(f"Field {field} mismatch")
        
        return True
    
    def format_display_values(self, raw_values):
        """Format values for frontend display"""
        
        # Fix interval display (caused "Every {JSON} minutes")
        if isinstance(raw_values['update_interval'], (dict, str)):
            if raw_values['update_interval'] in [None, 'null', '{}']:
                raw_values['update_interval'] = "Auto (10 min)"
            else:
                raw_values['update_interval'] = f"Every {raw_values['update_interval']} minutes"
        
        # Format last run times (prevented "Never" display bug)
        if raw_values['last_run']:
            from datetime import datetime
            last_run = datetime.fromisoformat(raw_values['last_run'])
            raw_values['last_run_display'] = last_run.strftime("%m/%d %I:%M %p")
        
        return raw_values
```

---

## 🔄 **Phase 4: Duplicate Prevention & Quality Control**

### **Problem Solved**: 27 duplicate/low-quality events cluttering approval queue

**Implementation Requirements:**

```python
class ProductionQualityControl:
    """Quality control based on real production issues"""
    
    def detect_duplicates(self, new_event, existing_events):
        """Advanced duplicate detection (prevents our 3x duplicate issue)"""
        
        from difflib import SequenceMatcher
        
        for existing in existing_events:
            # Normalize titles for comparison
            new_title = self._normalize_for_comparison(new_event['title'])
            existing_title = self._normalize_for_comparison(existing['title'])
            
            # Check title similarity
            title_similarity = SequenceMatcher(None, new_title, existing_title).ratio()
            
            # Check date proximity (same day = likely duplicate)
            date_match = self._dates_within_hours(
                new_event['start_date'], existing['start_date'], 24
            )
            
            # Flag as duplicate if high similarity + same day
            if title_similarity > 0.85 and date_match:
                return True
        
        return False
    
    def _normalize_for_comparison(self, text):
        """Remove noise for duplicate detection"""
        import re
        # Remove punctuation, normalize case, collapse whitespace
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def validate_event_completeness(self, event):
        """Ensure minimum data quality (prevents approval queue clutter)"""
        
        required_fields = ['title', 'start_date']
        for field in required_fields:
            if not event.get(field):
                return False, f"Missing required field: {field}"
        
        # Validate title quality (prevents our generic title issue)
        if not self.text_cleaner.validate_title_quality(event['title']):
            return False, "Invalid title quality"
        
        # Validate date format (prevents parsing errors)
        try:
            from dateutil import parser
            parser.parse(event['start_date'])
        except:
            return False, "Invalid date format"
        
        return True, "Event validated"
```

---

## ⏰ **Phase 5: Past Event Prevention**

### **Problem Solved**: September 16 event appearing in queue on September 23

**Implementation Requirements:**

```python
class PastEventFilter:
    """Prevent past events from entering approval queue"""
    
    def is_past_event(self, soup, extracted_events):
        """Multi-strategy past event detection"""
        
        # Strategy 1: Explicit text indicators (most reliable)
        text = soup.get_text().lower()
        past_indicators = [
            'past event', 'event has ended', 'archived event',
            'this event has concluded', 'event archive'
        ]
        
        for indicator in past_indicators:
            if indicator in text:
                return True, f"Found indicator: {indicator}"
        
        # Strategy 2: Date analysis (conservative approach)
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=7)  # Only very old events
        
        old_dates_found = 0
        for event in extracted_events:
            try:
                event_date = parser.parse(event['start_date'])
                if event_date < cutoff:
                    old_dates_found += 1
            except:
                continue
        
        # Only flag if multiple old dates (prevents false positives)
        if old_dates_found >= 2:
            return True, f"Multiple old dates found: {old_dates_found}"
        
        return False, "Event appears current"
    
    def filter_future_events(self, events):
        """Remove past events from scraped results"""
        
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=12)  # 12-hour buffer
        
        future_events = []
        for event in events:
            try:
                event_date = parser.parse(event['start_date'])
                if event_date > cutoff:
                    future_events.append(event)
            except:
                # If date parsing fails, include event for manual review
                future_events.append(event)
        
        return future_events
```

---

## 🕷️ **Phase 6: Production Health Monitoring**

### **Problem Solved**: "100% Health" when system actually failing

**Implementation Requirements:**

```python
class ProductionHealthMonitor:
    """Accurate health monitoring based on real metrics"""
    
    def calculate_real_health_score(self, scrapers):
        """Calculate health based on actual performance"""
        
        if not scrapers:
            return 0
        
        health_factors = []
        
        for scraper in scrapers:
            # Factor 1: Recent execution success
            recent_success = self._check_recent_runs(scraper, hours=24)
            
            # Factor 2: Event discovery rate
            discovery_rate = self._check_discovery_rate(scraper, days=7)
            
            # Factor 3: Failure rate management
            failure_health = self._calculate_failure_health(scraper)
            
            # Combined health score per scraper
            scraper_health = (recent_success + discovery_rate + failure_health) / 3
            health_factors.append(scraper_health)
        
        # Overall system health
        overall_health = sum(health_factors) / len(health_factors)
        return round(overall_health, 1)
    
    def _check_recent_runs(self, scraper, hours=24):
        """Check if scraper ran recently (prevents 'Never' status)"""
        
        if not scraper.last_run:
            return 0  # Never run = 0% health
        
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=hours)
        last_run = datetime.fromisoformat(scraper.last_run)
        
        if last_run > cutoff:
            return 100  # Recent run = 100% health
        else:
            # Gradual degradation based on time since last run
            hours_since = (datetime.now() - last_run).total_seconds() / 3600
            return max(0, 100 - (hours_since - hours) * 2)
    
    def _check_discovery_rate(self, scraper, days=7):
        """Check if scraper is finding events (prevents silent failures)"""
        
        if scraper.total_events == 0:
            return 0  # No events = 0% discovery health
        
        # Calculate events per day rate
        from datetime import datetime, timedelta
        if scraper.created_at:
            scraper_age = (datetime.now() - datetime.fromisoformat(scraper.created_at)).days
            events_per_day = scraper.total_events / max(scraper_age, 1)
            
            # Scale: 1+ events/day = 100%, 0.1 events/day = 10%
            return min(100, events_per_day * 100)
        
        return 50  # Unknown age = neutral score
    
    def _calculate_failure_health(self, scraper):
        """Factor in failure rates (prevents ignoring 119 failures)"""
        
        failures = scraper.consecutive_failures or 0
        
        if failures == 0:
            return 100
        elif failures < 5:
            return 80
        elif failures < 20:
            return 50
        elif failures < 50:
            return 20
        else:
            return 0  # 50+ failures = 0% health
```

---

## 🎯 **Implementation Priority Order**

Based on our production experience:

1. **Date Extraction** (Highest Impact) - Prevents major user confusion
2. **Text Cleaning** (High Impact) - Ensures professional appearance  
3. **Past Event Filtering** (Medium Impact) - Reduces admin overhead
4. **Health Monitoring** (Medium Impact) - Prevents silent failures
5. **Duplicate Detection** (Medium Impact) - Keeps data clean
6. **Data Pipeline Validation** (Lower Impact) - Ensures consistency

---

## 🔄 **Continuous Improvement Protocol**

**Weekly Reviews:**
- Monitor health scores for degradation
- Check for new duplicate patterns
- Validate date extraction accuracy
- Review text encoding issues

**Monthly Enhancements:**
- Add new source-specific patterns
- Update text cleaning rules
- Refine duplicate detection
- Optimize health calculations

**Incident Response:**
- Log all extraction failures
- Document new failure patterns
- Update validation rules
- Test fixes before deployment

---

## ✅ **Success Metrics**

- **Date Accuracy**: >95% correct event dates
- **Text Quality**: <1% encoding issues
- **Duplicate Rate**: <5% duplicate events
- **Health Accuracy**: Health score within 10% of actual performance
- **Past Event Rate**: <2% past events in approval queue
- **Admin Efficiency**: <10 minutes daily approval time

This prompt is specifically tailored to prevent the exact issues you encountered and provides a bulletproof framework for maintaining high-quality event data in production.
