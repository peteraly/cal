"""
Fix Brookings Date Extraction Issues
Debug and fix the specific date parsing problems for Brookings events
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from dateutil import parser as date_parser
from datetime import datetime

def analyze_brookings_date_extraction():
    """Analyze how dates are being extracted from Brookings pages"""
    print('🔍 ANALYZING BROOKINGS DATE EXTRACTION')
    print('=' * 50)
    
    url = 'https://www.brookings.edu/events/is-everything-we-think-we-know-about-gun-violence-wrong/'
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print('📅 STEP 1: FIND ALL DATE-RELATED CONTENT')
        
        # Check JSON-LD structured data first
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                print('   JSON-LD Structure Data:')
                
                def find_dates_in_json(obj, path=""):
                    """Recursively find date-related fields in JSON"""
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if any(date_word in key.lower() for date_word in ['date', 'time', 'start', 'end']):
                                print(f'     {path}.{key}: {value}')
                            find_dates_in_json(value, f'{path}.{key}')
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            find_dates_in_json(item, f'{path}[{i}]')
                
                find_dates_in_json(data)
                
            except json.JSONDecodeError:
                print('   JSON-LD parsing failed')
        
        # Check time elements
        print('\\n📅 STEP 2: TIME ELEMENTS')
        time_elements = soup.find_all('time')
        for i, elem in enumerate(time_elements):
            print(f'   Time {i+1}: "{elem.get_text(strip=True)}" (datetime="{elem.get("datetime", "None")}")')
        
        # Check elements with date-related classes
        print('\\n📅 STEP 3: DATE CLASS ELEMENTS')
        date_classes = ['date', 'event-date', 'start-date', 'event-time', 'datetime']
        for class_name in date_classes:
            elements = soup.find_all(class_=lambda x: x and class_name in x.lower() if x else False)
            for elem in elements[:3]:
                print(f'   .{class_name}: "{elem.get_text(strip=True)[:100]}"')
        
        # Check for specific Brookings date patterns
        print('\\n📅 STEP 4: BROOKINGS-SPECIFIC PATTERNS')
        
        # Look for the correct date format in text
        text = soup.get_text()
        
        # Pattern 1: "Wednesday, October 1, 2025"
        full_date_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})'
        matches = re.findall(full_date_pattern, text, re.IGNORECASE)
        for match in matches:
            day_name, month, day, year = match
            print(f'   Full date pattern: {day_name}, {month} {day}, {year}')
        
        # Pattern 2: "10:00 am - 11:00 am EDT"
        time_range_pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)\s*(EDT|EST|PST|PDT)'
        time_matches = re.findall(time_range_pattern, text, re.IGNORECASE)
        for match in time_matches:
            start_hour, start_min, start_ampm, end_hour, end_min, end_ampm, tz = match
            print(f'   Time range: {start_hour}:{start_min} {start_ampm} - {end_hour}:{end_min} {end_ampm} {tz}')
        
        return True
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

def test_improved_date_extraction():
    """Test improved date extraction logic"""
    print('\\n🔧 TESTING IMPROVED DATE EXTRACTION')
    print('=' * 45)
    
    url = 'https://www.brookings.edu/events/is-everything-we-think-we-know-about-gun-violence-wrong/'
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Strategy 1: Look for structured data first
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                
                def extract_event_dates(obj):
                    """Extract start/end dates from JSON-LD"""
                    dates = {}
                    if isinstance(obj, dict):
                        if obj.get('@type') == 'Event':
                            dates['startDate'] = obj.get('startDate')
                            dates['endDate'] = obj.get('endDate')
                            dates['eventSchedule'] = obj.get('eventSchedule')
                        
                        for value in obj.values():
                            dates.update(extract_event_dates(value))
                    elif isinstance(obj, list):
                        for item in obj:
                            dates.update(extract_event_dates(item))
                    
                    return dates
                
                event_dates = extract_event_dates(data)
                print('   Structured data dates:')
                for key, value in event_dates.items():
                    if value:
                        print(f'     {key}: {value}')
                        
                        # Try to parse the date
                        try:
                            parsed = date_parser.parse(str(value))
                            print(f'       → Parsed: {parsed}')
                        except:
                            print(f'       → Parse failed')
                            
            except json.JSONDecodeError:
                print('   JSON-LD parsing failed')
        
        # Strategy 2: Text-based extraction with better patterns
        text = soup.get_text()
        
        # Look for "October 1, 2025" followed by time
        date_time_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})\\s*(\d{1,2}):(\d{2})\s*(am|pm)\s*-\s*(\d{1,2}):(\d{2})\s*(am|pm)\s*(EDT|EST)'
        
        matches = re.findall(date_time_pattern, text, re.IGNORECASE)
        
        print('\\n   Text-based extraction:')
        for match in matches:
            day_name, month, day, year, start_hour, start_min, start_ampm, end_hour, end_min, end_ampm, tz = match
            
            date_str = f'{month} {day}, {year} {start_hour}:{start_min} {start_ampm}'
            print(f'     Found: {date_str}')
            
            try:
                parsed = date_parser.parse(date_str)
                print(f'     → Parsed: {parsed}')
                print(f'     → ISO format: {parsed.isoformat()}')
            except Exception as e:
                print(f'     → Parse failed: {e}')
        
        # Strategy 3: Look for standalone October 1 references
        oct_pattern = r'October\\s+1,?\\s+2025'
        oct_matches = re.findall(oct_pattern, text, re.IGNORECASE)
        print(f'\\n   October 1 references found: {len(oct_matches)}')
        
        for match in oct_matches[:3]:
            print(f'     "{match}"')
            try:
                parsed = date_parser.parse(match + ' 10:00 AM')  # Add default time
                print(f'     → Parsed with default time: {parsed}')
            except Exception as e:
                print(f'     → Parse failed: {e}')
        
    except Exception as e:
        print(f'❌ Error in improved extraction: {e}')

def fix_database_event():
    """Fix the specific gun violence event in the database"""
    print('\\n🔧 FIXING DATABASE EVENT')
    print('=' * 30)
    
    import sqlite3
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Find the gun violence event
    cursor.execute('''
        SELECT id, title, start_datetime, url
        FROM events 
        WHERE title LIKE '%gun violence%'
        AND url LIKE '%brookings%'
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    
    event = cursor.fetchone()
    
    if event:
        event_id, title, current_date, url = event
        
        # Set the correct date and time
        correct_datetime = '2025-10-01T10:00:00-04:00'  # October 1, 2025 10:00 AM EDT
        
        cursor.execute('''
            UPDATE events 
            SET start_datetime = ? 
            WHERE id = ?
        ''', (correct_datetime, event_id))
        
        conn.commit()
        
        print(f'✅ FIXED EVENT:')
        print(f'   ID: {event_id}')
        print(f'   Title: {title}')
        print(f'   Old date: {current_date}')
        print(f'   New date: {correct_datetime}')
        print(f'   URL: {url}')
        
    else:
        print('❌ Event not found in database')
    
    conn.close()

def main():
    """Main analysis and fix process"""
    print('🚀 BROOKINGS DATE EXTRACTION FIX')
    print('=' * 40)
    
    # Step 1: Analyze current extraction
    analyze_brookings_date_extraction()
    
    # Step 2: Test improved extraction
    test_improved_date_extraction()
    
    # Step 3: Fix the database
    fix_database_event()
    
    print('\\n🎯 SUMMARY:')
    print('The issue is that the scraper can see the correct date')
    print('("October 1, 2025 10:00 AM") but the date parsing')
    print('algorithm is extracting the wrong text or failing to parse it.')
    print('')
    print('Next steps:')
    print('1. Update enhanced_scraper.py with better date extraction')
    print('2. Add Brookings-specific date patterns')
    print('3. Improve JSON-LD parsing for structured events')

if __name__ == '__main__':
    main()
