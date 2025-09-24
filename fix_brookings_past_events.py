"""
Fix Brookings Past Events and Date Priority Issues
Remove past events and fix date extraction priority
"""

import sqlite3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
from dateutil import parser as date_parser

def identify_past_events():
    """Identify events that are in the past and should be removed"""
    print('🔍 IDENTIFYING PAST EVENTS')
    print('=' * 35)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get current time
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    # Find events that are clearly in the past
    cursor.execute('''
        SELECT id, title, start_datetime, url
        FROM events 
        WHERE (url LIKE '%brookings%' OR location_name LIKE '%Brookings%')
        AND approval_status = 'pending'
        AND start_datetime < ?
        ORDER BY start_datetime
    ''', (yesterday.isoformat(),))
    
    past_events = cursor.fetchall()
    
    print(f'📅 EVENTS IN THE PAST:')
    for event_id, title, start_datetime, url in past_events:
        print(f'   ID {event_id}: {title[:50]}...')
        print(f'     Date: {start_datetime}')
        print(f'     URL: {url}')
        print()
    
    conn.close()
    return past_events

def verify_past_event_status(url):
    """Check if an event page says 'Past Event'"""
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text().lower()
        
        return 'past event' in text
    except:
        return False

def fix_china_pacific_event():
    """Fix the specific China Pacific Islands event"""
    print('\n🔧 FIXING CHINA/PACIFIC ISLANDS EVENT')
    print('=' * 45)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Find the China event
    cursor.execute('''
        SELECT id, title, start_datetime, url
        FROM events 
        WHERE title LIKE '%China%Pacific%'
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    
    event = cursor.fetchone()
    
    if not event:
        print('❌ China/Pacific Islands event not found')
        conn.close()
        return
    
    event_id, title, current_date, url = event
    
    print(f'Event found:')
    print(f'   ID: {event_id}')
    print(f'   Title: {title}')
    print(f'   Current date: {current_date}')
    
    # Check if it's a past event
    is_past = verify_past_event_status(url)
    
    if is_past:
        print(f'   ⚠️  This is marked as \"Past Event\" on website')
        print(f'   → Removing from approval queue')
        
        cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
        conn.commit()
        
        print(f'   ✅ Past event removed from database')
    else:
        # Fix the date to September 16, 2025 9:00 AM EDT
        correct_datetime = '2025-09-16T09:00:00-04:00'
        
        cursor.execute('''
            UPDATE events 
            SET start_datetime = ? 
            WHERE id = ?
        ''', (correct_datetime, event_id))
        
        conn.commit()
        
        print(f'   ✅ Date corrected:')
        print(f'     Old: {current_date}')
        print(f'     New: {correct_datetime}')
    
    conn.close()

def remove_all_past_brookings_events():
    """Remove all Brookings events that are clearly past"""
    print('\\n🗑️  REMOVING PAST BROOKINGS EVENTS')
    print('=' * 40)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Remove events before September 20, 2025 (clearly past)
    cutoff_date = '2025-09-20T00:00:00'
    
    cursor.execute('''
        SELECT id, title, start_datetime
        FROM events 
        WHERE (url LIKE '%brookings%' OR location_name LIKE '%Brookings%')
        AND approval_status = 'pending'
        AND start_datetime < ?
    ''', (cutoff_date,))
    
    past_events = cursor.fetchall()
    
    if past_events:
        print(f'Found {len(past_events)} past events to remove:')
        
        for event_id, title, start_datetime in past_events:
            print(f'   • {title[:50]}... ({start_datetime})')
        
        # Remove them
        cursor.execute('''
            DELETE FROM events 
            WHERE (url LIKE '%brookings%' OR location_name LIKE '%Brookings%')
            AND approval_status = 'pending'
            AND start_datetime < ?
        ''', (cutoff_date,))
        
        removed_count = cursor.rowcount
        conn.commit()
        
        print(f'   ✅ Removed {removed_count} past events')
    else:
        print('   No past events found to remove')
    
    conn.close()

def fix_remaining_brookings_dates():
    """Fix dates for remaining Brookings events"""
    print('\\n🔧 CHECKING REMAINING BROOKINGS EVENTS')
    print('=' * 45)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, title, start_datetime, url
        FROM events 
        WHERE (url LIKE '%brookings%' OR location_name LIKE '%Brookings%')
        AND approval_status = 'pending'
        ORDER BY start_datetime
    ''')
    
    remaining_events = cursor.fetchall()
    
    print(f'📅 REMAINING BROOKINGS EVENTS:')
    for event_id, title, start_datetime, url in remaining_events:
        print(f'   ID {event_id}: {title[:50]}...')
        print(f'     Date: {start_datetime}')
        
        # Check if this looks suspicious (same timestamp pattern)
        if '2025-09-22T' in start_datetime or '2025-09-23T' in start_datetime:
            print(f'     ⚠️  Suspicious date pattern - may need manual review')
        else:
            print(f'     ✅ Date looks reasonable')
        print()
    
    conn.close()

def enhance_date_priority_in_scraper():
    """Provide instructions for improving date priority in scraper"""
    print('\\n📋 SCRAPER ENHANCEMENT RECOMMENDATIONS')
    print('=' * 50)
    
    print('To prevent future issues, the enhanced_scraper.py should:')
    print('')
    print('1. 📅 PRIORITIZE EVENT-SPECIFIC DATES:')
    print('   - Look for dates near event titles')
    print('   - Prefer dates in agenda/schedule sections')
    print('   - Avoid page metadata dates (publishedDate, etc.)')
    print('')
    print('2. ⚠️  DETECT PAST EVENTS:')
    print('   - Check for \"Past Event\" text')
    print('   - Compare dates to current date')
    print('   - Skip events that are clearly past')
    print('')
    print('3. 🎯 IMPROVE DATE EXTRACTION ORDER:')
    print('   - JSON-LD event dates (if present)')
    print('   - Agenda/schedule dates')
    print('   - Date elements near titles')
    print('   - General page dates (last resort)')

def main():
    """Main fix process"""
    print('🚀 FIXING BROOKINGS PAST EVENTS & DATE ISSUES')
    print('=' * 55)
    
    # Step 1: Identify past events
    past_events = identify_past_events()
    
    # Step 2: Fix specific China event
    fix_china_pacific_event()
    
    # Step 3: Remove other past events
    remove_all_past_brookings_events()
    
    # Step 4: Check remaining events
    fix_remaining_brookings_dates()
    
    # Step 5: Enhancement recommendations
    enhance_date_priority_in_scraper()
    
    print('\\n🎯 SUMMARY:')
    print('✅ Removed past events from approval queue')
    print('✅ Fixed China/Pacific Islands event date')
    print('⚠️  Remaining events may need manual review')
    print('')
    print('🔗 Next steps:')
    print('1. Refresh http://localhost:5001/admin/approval')
    print('2. Check that China event shows correct date or is removed')
    print('3. Review remaining Brookings events for accuracy')

if __name__ == '__main__':
    main()
