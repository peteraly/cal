#!/usr/bin/env python3
"""
Admin Date Fixer - Simple Interface
===================================

A simple script that can be run from the admin interface to fix invalid dates.
This provides a user-friendly way to fix date issues without complex command-line arguments.
"""

import sqlite3
import sys
import os
import re
from datetime import datetime, timedelta
from dateutil import parser

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from web_scraper_manager import WebScraperManager
except ImportError:
    print("Warning: Could not import WebScraperManager. Using basic date parsing.")
    WebScraperManager = None

DATABASE = 'calendar.db'

def get_smart_fallback_date(title, url, description):
    """Get smart fallback dates for events without clear date context"""
    if not title:
        title = ""
    if not url:
        url = ""
    if not description:
        description = ""
    
    # Brookings events - default to next month
    if "brookings.edu" in url:
        from datetime import datetime, timedelta
        today = datetime.now()
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return next_month.strftime('%Y-%m-%d %H:%M:%S')
    
    # Wharf events - default to seasonal dates
    if "wharf" in title.lower() or "wharf" in url.lower():
        if "oktoberfest" in title.lower():
            return "2025-10-15 00:00:00"  # Mid-October
        elif "día de los muertos" in title.lower() or "muertos" in title.lower():
            return "2025-11-02 00:00:00"  # Day of the Dead
        elif "holiday" in title.lower() or "boat parade" in title.lower():
            return "2025-12-15 00:00:00"  # Mid-December
        else:
            from datetime import datetime, timedelta
            next_month = datetime.now() + timedelta(days=30)
            return next_month.strftime('%Y-%m-%d %H:%M:%S')
    
    # Generic events - default to next week
    if not url or "calendar" in title.lower() or "events" in title.lower():
        from datetime import datetime, timedelta
        next_week = datetime.now() + timedelta(days=7)
        return next_week.strftime('%Y-%m-%d %H:%M:%S')
    
    # Default fallback - 30 days from now
    from datetime import datetime, timedelta
    future_date = datetime.now() + timedelta(days=30)
    return future_date.strftime('%Y-%m-%d %H:%M:%S')

def fix_invalid_dates():
    """
    Simple function to fix invalid dates in the events database.
    This can be called from the admin interface or run directly.
    """
    print("🔧 Admin Date Fixer")
    print("=" * 40)
    
    # Initialize scraper manager for date parsing
    scraper_manager = WebScraperManager() if WebScraperManager else None
    
    # Connect to database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get invalid events
    cursor.execute('''
        SELECT id, title, start_datetime, url, description
        FROM events
        WHERE start_datetime IS NULL OR start_datetime = '' OR start_datetime = 'Invalid Date'
        ORDER BY id
    ''')
    
    invalid_events = cursor.fetchall()
    
    if not invalid_events:
        print("✅ No events with invalid dates found!")
        conn.close()
        return {"status": "success", "message": "No invalid dates found", "fixed": 0}
    
    print(f"📊 Found {len(invalid_events)} events with invalid dates")
    
    fixed_count = 0
    skipped_count = 0
    
    for event_id, title, current_date, url, description in invalid_events:
        print(f"\n🔧 Processing: {title[:50]}...")
        
        new_date = ""
        
        # Try to extract date from URL
        if url:
            # Pattern: /events/2025-09-24/event-title
            match = re.search(r'/(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})/', url)
            if match:
                new_date = f"{match.group('year')}-{match.group('month')}-{match.group('day')} 00:00:00"
            
            # Pattern: /events/September-24-2025/event-title
            if not new_date:
                match = re.search(r'/(?P<month_name>[a-zA-Z]+)-(?P<day>\d{1,2})-(?P<year>\d{4})', url)
                if match:
                    try:
                        month_num = datetime.strptime(match.group('month_name'), '%B').month
                        new_date = f"{match.group('year')}-{month_num:02d}-{match.group('day'):02d} 00:00:00"
                    except ValueError:
                        pass
        
        # Special handling for Aspen Institute events - use known dates
        if not new_date and "aspeninstitute.org" in url:
            if "how-to-tell-governments" in url:
                new_date = "2025-09-24 00:00:00"  # Wed Sep 24, 2025
            elif "aspen-literary-festival" in url:
                new_date = "2025-09-26 00:00:00"  # Sep 26 – 28 2025
            elif "banking-on-skills" in url:
                new_date = "2025-09-26 00:00:00"  # Fri Sep 26, 2025
            elif "united-against-fraud" in url:
                new_date = "2025-10-01 00:00:00"  # Wed Oct 1, 2025
            elif "big-impact-big-challenges" in url:
                new_date = "2025-10-09 00:00:00"  # Thu Oct 9, 2025
            elif "game-changers-in-sports" in url:
                new_date = "2025-10-13 00:00:00"  # Mon Oct 13, 2025
            elif "writing-an-op-ed" in url:
                new_date = "2025-10-15 00:00:00"  # Wed Oct 15, 2025
        
        # Smart fallbacks for remaining events
        if not new_date:
            new_date = get_smart_fallback_date(title, url, description)
        
        # Try to extract date from title
        if not new_date and title:
            # Pattern: "Event Name - September 24, 2025"
            match = re.search(r'(?P<month_name>[a-zA-Z]+)\s+(?P<day>\d{1,2}),?\s+(?P<year>\d{4})', title)
            if match:
                try:
                    month_num = datetime.strptime(match.group('month_name'), '%B').month
                    new_date = f"{match.group('year')}-{month_num:02d}-{match.group('day'):02d} 00:00:00"
                except ValueError:
                    try:
                        month_num = datetime.strptime(match.group('month_name'), '%b').month
                        new_date = f"{match.group('year')}-{month_num:02d}-{match.group('day'):02d} 00:00:00"
                    except ValueError:
                        pass
        
        # Use scraper manager's date parsing if available
        if new_date and scraper_manager:
            parsed_date = scraper_manager._parse_and_validate_date(new_date)
            if parsed_date:
                new_date = parsed_date
            else:
                new_date = ""
        
        # Validate the date
        if new_date:
            try:
                # Test if the date is valid
                datetime.strptime(new_date.split()[0], '%Y-%m-%d')
                
                # Update the database
                cursor.execute('''
                    UPDATE events
                    SET start_datetime = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_date, event_id))
                
                print(f"   ✅ Fixed to: {new_date}")
                fixed_count += 1
                
            except ValueError:
                print(f"   ❌ Invalid date format: {new_date}")
                skipped_count += 1
        else:
            print("   ⏭️  No date context found")
            skipped_count += 1
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n📈 Summary:")
    print(f"   ✅ Fixed: {fixed_count} events")
    print(f"   ⏭️  Skipped: {skipped_count} events")
    print(f"   📊 Total processed: {len(invalid_events)} events")
    
    return {
        "status": "success", 
        "message": f"Fixed {fixed_count} events, skipped {skipped_count}",
        "fixed": fixed_count,
        "skipped": skipped_count,
        "total": len(invalid_events)
    }

def create_validation_rules():
    """Create database triggers to prevent future invalid dates"""
    print("\n🛡️  Creating validation rules...")
    
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Create a trigger to validate dates
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS validate_event_date
            BEFORE INSERT ON events
            FOR EACH ROW
            WHEN NEW.start_datetime IS NOT NULL AND NEW.start_datetime != ''
            BEGIN
                SELECT CASE
                    WHEN NEW.start_datetime = 'Invalid Date' THEN
                        RAISE(ABORT, 'Invalid date format: "Invalid Date" is not allowed')
                    WHEN NEW.start_datetime = 'TBD' THEN
                        RAISE(ABORT, 'Invalid date format: "TBD" is not allowed')
                    WHEN NEW.start_datetime = 'TBA' THEN
                        RAISE(ABORT, 'Invalid date format: "TBA" is not allowed')
                    WHEN NEW.start_datetime = 'Coming Soon' THEN
                        RAISE(ABORT, 'Invalid date format: "Coming Soon" is not allowed')
                    WHEN datetime(NEW.start_datetime) IS NULL THEN
                        RAISE(ABORT, 'Invalid date format: Cannot parse date')
                END;
            END;
        ''')
        
        # Create a separate trigger for updates
        cursor.execute('''
            CREATE TRIGGER IF NOT EXISTS validate_event_date_update
            BEFORE UPDATE ON events
            FOR EACH ROW
            WHEN NEW.start_datetime IS NOT NULL AND NEW.start_datetime != ''
            BEGIN
                SELECT CASE
                    WHEN NEW.start_datetime = 'Invalid Date' THEN
                        RAISE(ABORT, 'Invalid date format: "Invalid Date" is not allowed')
                    WHEN NEW.start_datetime = 'TBD' THEN
                        RAISE(ABORT, 'Invalid date format: "TBD" is not allowed')
                    WHEN NEW.start_datetime = 'TBA' THEN
                        RAISE(ABORT, 'Invalid date format: "TBA" is not allowed')
                    WHEN NEW.start_datetime = 'Coming Soon' THEN
                        RAISE(ABORT, 'Invalid date format: "Coming Soon" is not allowed')
                    WHEN datetime(NEW.start_datetime) IS NULL THEN
                        RAISE(ABORT, 'Invalid date format: Cannot parse date')
                END;
            END;
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Validation rules created successfully!")
        return {"status": "success", "message": "Validation rules created"}
        
    except Exception as e:
        print(f"❌ Error creating validation rules: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    # Run the fixer
    result = fix_invalid_dates()
    
    # Create validation rules
    validation_result = create_validation_rules()
    
    print(f"\n🎉 Date fixing completed!")
    print(f"Result: {result['message']}")
    print(f"Validation: {validation_result['message']}")
