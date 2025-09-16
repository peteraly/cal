#!/usr/bin/env python3
"""
Script to add Sara Curtin Millennium Stage event to the calendar database.
"""

import sqlite3
import os
from datetime import datetime, timedelta

DATABASE = 'calendar.db'

# Sara Curtin event data
EVENT_DATA = {
    'title': 'Sara Curtin - Millennium Stage (In-Person and Livestream)',
    'location_name': 'Millennium Stage, Kennedy Center',
    'address': '2700 F St NW, Washington, DC 20566',
    'price_info': 'Free - $0.00',
    'url': 'https://www.kennedy-center.org/whats-on/calendar/',
    'description': '''Sara Curtin is thrilled to return to the Kennedy Center's Millennium Stage fresh off the September 2025 release of her new indie-folk EP Don't Go Alone. The Washington Post calls Curtin's voice "angelic." Born and raised in Washington, D.C., she has performed at esteemed local venues including Millennium Stage, the 9:30 Club, Strathmore, The Black Cat, and The Birchmere, as well as having toured the US and abroad.

Genre: Popular Music
Price: Free
Ticket Limit: 4 per person
Available: In-Person and Livestream

Fresh off the September 2025 release of her new indie-folk EP, D.C. native Sara Curtin is thrilled to return to Millennium Stage.

TICKETING & ENTRY:
- Limited number of advance reservations available on a first come, first served basis
- Advance reservations do not guarantee a seat - arrive early
- Online advance reservations open every Wednesday two weeks out from the date
- Free tickets also available at the Hall of States Box Office on the day of performance, beginning at 4:30 p.m.
- Seating is first come, first served
- Standing room available behind the seated area as space allows

This event is available both in-person and via livestream.'''
}

# Event date and time
EVENT_DATE = ('2025-09-17', '18:00', 'Wed. Sep. 17, 2025 - 6:00 p.m.')

def add_sara_curtin_event():
    """Add Sara Curtin event to the database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    added_count = 0
    skipped_count = 0
    
    print(f"Adding Sara Curtin Millennium Stage event...")
    
    date_str, time_str, show_info = EVENT_DATE
    
    # Create start datetime
    start_datetime = f"{date_str}T{time_str}:00"
    
    # Create end datetime (assuming 1.5 hours for Millennium Stage performance)
    start_dt = datetime.strptime(start_datetime, '%Y-%m-%dT%H:%M:%S')
    end_dt = start_dt + timedelta(hours=1, minutes=30)
    end_datetime = end_dt.strftime('%Y-%m-%dT%H:%M:%S')
    
    # Create title with show info
    title = f"{EVENT_DATA['title']} - {show_info}"
    
    # Check if event already exists
    cursor.execute('''
        SELECT id FROM events 
        WHERE title = ? AND start_datetime = ?
    ''', (title, start_datetime))
    
    if cursor.fetchone():
        print(f"  Skipping: {title} (already exists)")
        skipped_count += 1
    else:
        # Insert new event
        cursor.execute('''
            INSERT INTO events (
                title, start_datetime, end_datetime, description,
                location_name, address, price_info, url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title,
            start_datetime,
            end_datetime,
            EVENT_DATA['description'],
            EVENT_DATA['location_name'],
            EVENT_DATA['address'],
            EVENT_DATA['price_info'],
            EVENT_DATA['url'],
            datetime.now().isoformat()
        ))
        
        added_count += 1
        print(f"  Added: {title}")
    
    conn.commit()
    conn.close()
    
    print(f"\nSummary:")
    print(f"  Added: {added_count} events")
    print(f"  Skipped: {skipped_count} events (already existed)")
    print(f"  Total: 1 event processed")

def show_database_stats():
    """Show current database statistics"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Total events
    cursor.execute('SELECT COUNT(*) FROM events')
    total_events = cursor.fetchone()[0]
    
    # Sara Curtin events
    cursor.execute('SELECT COUNT(*) FROM events WHERE title LIKE "%Sara Curtin%"')
    sara_curtin_events = cursor.fetchone()[0]
    
    # Millennium Stage events
    cursor.execute('SELECT COUNT(*) FROM events WHERE location_name LIKE "%Millennium Stage%"')
    millennium_stage_events = cursor.fetchone()[0]
    
    # Kennedy Center events
    cursor.execute('SELECT COUNT(*) FROM events WHERE location_name LIKE "%Kennedy Center%"')
    kennedy_center_events = cursor.fetchone()[0]
    
    # Free events
    cursor.execute('SELECT COUNT(*) FROM events WHERE price_info LIKE "%Free%" OR price_info LIKE "%$0%"')
    free_events = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\nDatabase Statistics:")
    print(f"  Total events: {total_events}")
    print(f"  Sara Curtin events: {sara_curtin_events}")
    print(f"  Millennium Stage events: {millennium_stage_events}")
    print(f"  Kennedy Center events: {kennedy_center_events}")
    print(f"  Free events: {free_events}")

def main():
    """Main function"""
    print("Sara Curtin Millennium Stage Event Import Tool")
    print("=" * 50)
    
    if not os.path.exists(DATABASE):
        print(f"Error: Database file '{DATABASE}' not found")
        return
    
    # Show current stats
    show_database_stats()
    
    # Add Sara Curtin event
    add_sara_curtin_event()
    
    # Show final stats
    print("\nFinal Statistics:")
    show_database_stats()

if __name__ == "__main__":
    main()
