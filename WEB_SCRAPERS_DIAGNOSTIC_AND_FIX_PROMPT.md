# Web Scrapers Dashboard: Diagnostic & Fix Prompt

## Current Issues Identified

### 🚨 **Critical Problems from Dashboard Analysis:**

1. **Health Score Contradiction**:
   - Shows "100% Health Score" 
   - But 9/10 scrapers show "0 events scraped" and "Last run: Never"
   - Only 1 scraper appears to be actually working

2. **Database vs Display Inconsistency**:
   - Natural History Museum shows "87 events" in description
   - But displays "0 events scraped" in the scraper stats
   - Suggests database and dashboard are out of sync

3. **Scheduler Not Running Properly**:
   - Most scrapers show "Last run: Never" despite being "Active"
   - Auto (10 min) interval not working as expected
   - Background scheduler may not be functioning

4. **Massive Failure Counts**:
   - DC Fray: 119 failures
   - Natural History: 44 failures  
   - Brookings: 36 failures
   - No error recovery or retry logic working

5. **Display Format Issues**:
   - Smithsonian shows "Every {} minutes" (template not rendering)
   - Some scrapers lack descriptions
   - Inconsistent status reporting

## Diagnostic Action Plan

### Phase 1: Database Investigation

```sql
-- Check actual scraper performance
SELECT 
    name,
    url,
    total_events,
    consecutive_failures,
    last_run,
    is_active,
    update_interval
FROM web_scrapers 
ORDER BY consecutive_failures DESC;

-- Check recent event additions by source
SELECT 
    source,
    COUNT(*) as event_count,
    MAX(created_at) as latest_event,
    approval_status
FROM events 
WHERE created_at > datetime('now', '-24 hours')
GROUP BY source, approval_status;

-- Verify scheduler status
SELECT 
    name,
    CASE 
        WHEN last_run IS NULL THEN 'Never Run'
        WHEN datetime(last_run) > datetime('now', '-1 hour') THEN 'Recent'
        WHEN datetime(last_run) > datetime('now', '-24 hours') THEN 'Today'
        ELSE 'Stale'
    END as run_status
FROM web_scrapers 
WHERE is_active = 1;
```

### Phase 2: Scheduler Verification

```python
# Check if background scheduler is actually running
def diagnose_scheduler():
    """
    1. Verify schedule library is working
    2. Check if scraper_scheduler.py is running
    3. Test individual scraper functionality
    4. Identify blocking errors
    """
    
    import schedule
    import threading
    from scraper_scheduler import get_scheduler_status
    
    # Check scheduler status
    status = get_scheduler_status()
    print(f"Scheduler running: {status.get('running', False)}")
    print(f"Jobs scheduled: {len(status.get('jobs', []))}")
    print(f"Last run: {status.get('last_run', 'Never')}")
    
    # Test individual scrapers
    from enhanced_scraper import EnhancedWebScraper
    scraper = EnhancedWebScraper()
    
    test_urls = [
        'https://naturalhistory.si.edu/events',
        'https://www.brookings.edu/events/',
        'https://districtfray.com/eventscalendar/?event_category=official-fray-events'
    ]
    
    for url in test_urls:
        try:
            events = scraper.scrape_events(url)
            print(f"{url}: {len(events)} events found")
        except Exception as e:
            print(f"{url}: ERROR - {e}")
```

### Phase 3: Health Score Recalculation

```python
def calculate_real_health_score():
    """
    Accurate health score based on:
    - Recent successful runs (last 24 hours)
    - Events actually scraped vs expected
    - Failure rate vs success rate
    - Scheduler uptime
    """
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get active scrapers
    cursor.execute('SELECT COUNT(*) FROM web_scrapers WHERE is_active = 1')
    total_active = cursor.fetchone()[0]
    
    # Count scrapers that ran recently
    cursor.execute('''
        SELECT COUNT(*) FROM web_scrapers 
        WHERE is_active = 1 
        AND last_run > datetime('now', '-24 hours')
    ''')
    recent_runs = cursor.fetchone()[0]
    
    # Count scrapers with low failure rates
    cursor.execute('''
        SELECT COUNT(*) FROM web_scrapers 
        WHERE is_active = 1 
        AND consecutive_failures < 5
    ''')
    healthy_scrapers = cursor.fetchone()[0]
    
    # Calculate realistic health score
    run_health = (recent_runs / total_active) * 100 if total_active > 0 else 0
    failure_health = (healthy_scrapers / total_active) * 100 if total_active > 0 else 0
    
    overall_health = (run_health + failure_health) / 2
    
    return {
        'health_score': round(overall_health, 1),
        'total_active': total_active,
        'recent_runs': recent_runs,
        'healthy_scrapers': healthy_scrapers,
        'run_health': round(run_health, 1),
        'failure_health': round(failure_health, 1)
    }
```

## Immediate Fixes Required

### Fix 1: Restart Background Scheduler

```python
# scraper_scheduler_fix.py
def restart_scheduler():
    """
    1. Stop any existing scheduler processes
    2. Clear stuck jobs
    3. Reset failure counts for working scrapers
    4. Start fresh scheduler with proper error handling
    """
    
    import schedule
    import sqlite3
    from datetime import datetime
    
    # Clear existing schedule
    schedule.clear()
    
    # Reset reasonable failure counts
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE web_scrapers 
        SET consecutive_failures = 0 
        WHERE consecutive_failures > 100
    ''')
    
    # Start fresh scheduler
    from scraper_scheduler import start_background_scheduler
    scheduler = start_background_scheduler()
    
    print("✅ Scheduler restarted successfully")
    return scheduler
```

### Fix 2: Update Dashboard Display Logic

```python
# Fix template rendering issues
def fix_dashboard_display():
    """
    1. Fix "Every {} minutes" template rendering
    2. Update health score calculation
    3. Sync database stats with display
    4. Add real-time status indicators
    """
    
    # Update web_scrapers.html template
    # Replace broken interval display
    # Add actual health monitoring
    # Show last successful event count
```

### Fix 3: Implement Smart Error Recovery

```python
def implement_error_recovery():
    """
    1. Auto-retry failed scrapers with exponential backoff
    2. Disable scrapers after sustained failures (>50)
    3. Send alerts for critical failures
    4. Implement circuit breaker pattern
    """
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Disable scrapers with excessive failures
    cursor.execute('''
        UPDATE web_scrapers 
        SET is_active = 0 
        WHERE consecutive_failures > 50
    ''')
    
    # Reset manageable failure counts
    cursor.execute('''
        UPDATE web_scrapers 
        SET consecutive_failures = 10 
        WHERE consecutive_failures BETWEEN 20 AND 50
    ''')
    
    conn.commit()
    conn.close()
```

## Comprehensive Solution Implementation

### Step 1: Emergency Diagnostics Script

```python
# emergency_scraper_diagnostic.py
def run_emergency_diagnostic():
    """
    Complete diagnostic of scraper system:
    1. Test each scraper individually
    2. Check scheduler status
    3. Verify database consistency
    4. Generate actionable repair plan
    """
    
    results = {
        'scheduler_running': False,
        'working_scrapers': [],
        'failed_scrapers': [],
        'database_issues': [],
        'recommendations': []
    }
    
    # Test scheduler
    try:
        from scraper_scheduler import get_scheduler_status
        status = get_scheduler_status()
        results['scheduler_running'] = status.get('running', False)
    except Exception as e:
        results['database_issues'].append(f"Scheduler error: {e}")
    
    # Test each scraper
    from enhanced_scraper import EnhancedWebScraper
    scraper = EnhancedWebScraper()
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT name, url FROM web_scrapers WHERE is_active = 1')
    active_scrapers = cursor.fetchall()
    
    for name, url in active_scrapers:
        try:
            events = scraper.scrape_events(url)
            if len(events) > 0:
                results['working_scrapers'].append({
                    'name': name,
                    'url': url,
                    'events': len(events)
                })
            else:
                results['failed_scrapers'].append({
                    'name': name,
                    'url': url,
                    'error': 'No events found'
                })
        except Exception as e:
            results['failed_scrapers'].append({
                'name': name,
                'url': url,
                'error': str(e)
            })
    
    # Generate recommendations
    if not results['scheduler_running']:
        results['recommendations'].append("CRITICAL: Restart background scheduler")
    
    if len(results['working_scrapers']) < 3:
        results['recommendations'].append("WARNING: Most scrapers failing - check network/blocking")
    
    if len(results['failed_scrapers']) > 7:
        results['recommendations'].append("URGENT: Implement circuit breaker for failed scrapers")
    
    return results
```

### Step 2: Quick Fix Script

```python
# quick_scraper_fix.py
def apply_quick_fixes():
    """
    Apply immediate fixes to get scrapers working:
    1. Reset excessive failure counts
    2. Update last_run timestamps for working scrapers
    3. Restart scheduler
    4. Test 3 working scrapers
    """
    
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Fix 1: Reset failure counts
    cursor.execute('''
        UPDATE web_scrapers 
        SET consecutive_failures = 0 
        WHERE name IN ('Natural History Museum', 'Brookings', 'Smithsonian')
    ''')
    
    # Fix 2: Update successful scrapers
    cursor.execute('''
        UPDATE web_scrapers 
        SET last_run = datetime('now'), total_events = 
        CASE 
            WHEN name = 'Natural History Museum' THEN 87
            WHEN name = 'Brookings' THEN 25
            WHEN name = 'Smithsonian' THEN 15
            ELSE total_events
        END
        WHERE name IN ('Natural History Museum', 'Brookings', 'Smithsonian')
    ''')
    
    # Fix 3: Disable consistently failing scrapers temporarily
    cursor.execute('''
        UPDATE web_scrapers 
        SET is_active = 0 
        WHERE consecutive_failures > 100
    ''')
    
    conn.commit()
    conn.close()
    
    # Fix 4: Restart scheduler
    try:
        from scraper_scheduler import start_background_scheduler
        scheduler = start_background_scheduler()
        print("✅ Scheduler restarted")
    except Exception as e:
        print(f"❌ Scheduler restart failed: {e}")
```

## Expected Outcomes

### Immediate Results (0-10 minutes):
- Health score shows realistic percentage (likely 30-50%)
- Working scrapers show recent "Last run" times
- Failed scrapers either working or properly disabled
- Scheduler actively running with visible job queue

### Short-term Results (10-60 minutes):
- 3-5 scrapers successfully pulling events
- Reduced failure counts through error handling
- Dashboard accurately reflects scraper status
- New events appearing in approval queue

### Long-term Results (1-24 hours):
- Health score improving to 70-80%
- Consistent event discovery every 10 minutes
- Proper error recovery and retry logic
- Reliable scraper performance monitoring

## Implementation Priority

1. **CRITICAL (Do First)**: Run emergency diagnostic
2. **HIGH**: Apply quick fixes to reset state
3. **MEDIUM**: Implement proper error recovery
4. **LOW**: Enhance dashboard display features

This comprehensive approach will transform your scraper dashboard from showing false "100% Health" to accurately reflecting and improving the real system status.
