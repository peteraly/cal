"""
Fix event title extraction issues
Clean up bad titles and re-scrape with improved logic
"""

import sqlite3
from datetime import datetime
from pagination_scraper import PaginationAwareScraper

def clean_bad_events():
    """Remove events with obviously bad titles"""
    print('🧹 CLEANING UP EVENTS WITH BAD TITLES')
    print('=' * 50)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Identify bad titles
    bad_title_patterns = [
        # Location-based titles
        '%Floor%', '%Hall%', '%Theater%', '%Gallery%', '%Center%', '%Building%',
        # Date-based titles  
        '%2025%EDT%', '%Monday%', '%Tuesday%', '%Wednesday%', '%Thursday%', '%Friday%', '%Saturday%', '%Sunday%',
        '%January%', '%February%', '%March%', '%April%', '%May%', '%June%',
        '%July%', '%August%', '%September%', '%October%', '%November%', '%December%',
        # Metadata titles
        'Event Date', 'Event Type', 'Event Series', 'Event Category'
    ]
    
    total_deleted = 0
    
    for pattern in bad_title_patterns:
        cursor.execute('SELECT COUNT(*) FROM events WHERE title LIKE ? AND approval_status = "pending"', (pattern,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute('DELETE FROM events WHERE title LIKE ? AND approval_status = "pending"', (pattern,))
            print(f'   Deleted {count} events with pattern: {pattern}')
            total_deleted += count
    
    # Also delete events with specific bad titles
    exact_bad_titles = ['Event Date', 'Event Type', 'Event Series']
    for bad_title in exact_bad_titles:
        cursor.execute('DELETE FROM events WHERE title = ? AND approval_status = "pending"', (bad_title,))
    
    conn.commit()
    
    # Show remaining events
    cursor.execute('SELECT COUNT(*) FROM events WHERE approval_status = "pending" AND url LIKE "%naturalhistory%"')
    remaining = cursor.fetchone()[0]
    
    print(f'   Total bad events deleted: {total_deleted}')
    print(f'   Remaining Natural History events: {remaining}')
    
    conn.close()
    return total_deleted

def re_scrape_with_improved_logic():
    """Re-scrape Natural History Museum with improved title extraction"""
    print('\n🔄 RE-SCRAPING WITH IMPROVED TITLE EXTRACTION')
    print('=' * 55)
    
    scraper = PaginationAwareScraper()
    events = scraper.scrape_natural_history_comprehensive()
    
    print(f'✅ Found {len(events)} events with improved scraper')
    
    # Show sample of improved titles
    print('\n📋 SAMPLE OF IMPROVED EVENT TITLES:')
    good_events = [e for e in events if scraper._is_likely_event_title(e.get('title', ''))]
    
    for i, event in enumerate(good_events[:10]):
        title = event.get('title', 'Unknown')
        location = event.get('location', 'Unknown')
        date = event.get('start_date', 'No date')
        print(f'   {i+1:2d}. Title: "{title}"')
        print(f'       Location: "{location}"')
        print(f'       Date: {date}')
        print()
    
    # Add good events to database
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    events_added = 0
    for event in good_events:
        title = event.get('title', '').strip()
        description = event.get('description', '').strip()
        start_date = event.get('start_date', '').strip()
        location = event.get('location', 'Natural History Museum').strip()
        
        if not start_date:
            start_date = datetime.now().isoformat()
        else:
            try:
                from dateutil import parser
                parsed_date = parser.parse(start_date, fuzzy=True)
                start_date = parsed_date.isoformat()
            except:
                start_date = datetime.now().isoformat()
        
        # Check for duplicates
        cursor.execute('SELECT id FROM events WHERE title = ?', (title,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO events (title, description, start_datetime, location_name, 
                                  url, source, approval_status, created_at, category_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title, description, start_date, location,
                'https://naturalhistory.si.edu/events', 'scraper', 'pending',
                datetime.now().isoformat(), 1
            ))
            events_added += 1
    
    conn.commit()
    conn.close()
    
    print(f'✅ Added {events_added} events with proper titles')
    return events_added

def analyze_title_quality():
    """Analyze the quality of current event titles"""
    print('\n📊 ANALYZING TITLE QUALITY AFTER IMPROVEMENTS')
    print('=' * 55)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get current events
    cursor.execute('''
        SELECT title, location_name, start_datetime 
        FROM events 
        WHERE approval_status = 'pending' 
        AND url LIKE '%naturalhistory%'
        ORDER BY created_at DESC
        LIMIT 20
    ''')
    
    events = cursor.fetchall()
    
    scraper = PaginationAwareScraper()
    good_titles = 0
    bad_titles = 0
    
    print('📋 CURRENT EVENT TITLES (TOP 20):')
    for i, (title, location, date) in enumerate(events, 1):
        is_good = scraper._is_likely_event_title(title)
        status = '✅' if is_good else '❌'
        
        if is_good:
            good_titles += 1
        else:
            bad_titles += 1
        
        print(f'   {i:2d}. {status} "{title}"')
        if location:
            print(f'       📍 {location}')
        print()
    
    total_events = len(events)
    if total_events > 0:
        quality_percentage = (good_titles / total_events) * 100
        print(f'📈 TITLE QUALITY ANALYSIS:')
        print(f'   Good titles: {good_titles}/{total_events} ({quality_percentage:.1f}%)')
        print(f'   Bad titles: {bad_titles}/{total_events}')
        
        if quality_percentage >= 80:
            print(f'   🎉 EXCELLENT: Title extraction is working well!')
        elif quality_percentage >= 60:
            print(f'   ✅ GOOD: Most titles are correct, minor improvements needed')
        else:
            print(f'   ⚠️  NEEDS WORK: Title extraction needs further refinement')
    
    conn.close()

def main():
    """Main function to fix event title issues"""
    print('🚀 FIXING EVENT TITLE EXTRACTION ISSUES')
    print('=' * 60)
    
    # Step 1: Clean up bad events
    deleted_count = clean_bad_events()
    
    # Step 2: Re-scrape with improved logic
    added_count = re_scrape_with_improved_logic()
    
    # Step 3: Analyze quality
    analyze_title_quality()
    
    print(f'\n🎯 SUMMARY:')
    print(f'   Bad events removed: {deleted_count}')
    print(f'   Good events added: {added_count}')
    print(f'   Net improvement: +{added_count - deleted_count} quality events')
    
    print(f'\n🔗 Next steps:')
    print(f'   Visit: http://localhost:5001/admin/approval')
    print(f'   Review the improved event titles')
    print(f'   Events should now show proper names like:')
    print(f'   - "Ship to Shore: Live from the Science Vessel Point Sur"')
    print(f'   - "Play Date at NMNH: Colorful Corals"')
    print(f'   - "Q?rius After Hours - September"')

if __name__ == '__main__':
    main()
