#!/usr/bin/env python3
"""
Precise script to remove events that were added in the last hour.
This version uses the created_at timestamp for accurate removal.
"""

import sqlite3
import os
from datetime import datetime, timedelta

DATABASE = 'calendar.db'

def remove_events_from_last_hour():
    """Remove events that were created in the last hour"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Calculate timestamp for one hour ago
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    
    # Find events created in the last hour
    cursor.execute('''
        SELECT id, title, start_datetime, created_at 
        FROM events 
        WHERE created_at > ? 
        ORDER BY created_at DESC
    ''', (one_hour_ago,))
    
    recent_events = cursor.fetchall()
    
    if not recent_events:
        print("No events found that were created in the last hour")
        conn.close()
        return
    
    print(f"Found {len(recent_events)} events created in the last hour:")
    for event_id, title, start_datetime, created_at in recent_events:
        print(f"  - ID {event_id}: {title[:50]}... (created: {created_at})")
    
    # Ask for confirmation
    response = input(f"\nDo you want to remove these {len(recent_events)} events? (y/N): ").strip().lower()
    
    if response == 'y':
        # Remove the events
        event_ids = [str(event[0]) for event in recent_events]
        placeholders = ','.join(['?'] * len(event_ids))
        
        cursor.execute(f'DELETE FROM events WHERE id IN ({placeholders})', event_ids)
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"✓ Successfully removed {deleted_count} events created in the last hour")
    else:
        print("Operation cancelled")
        conn.close()

def show_recent_events():
    """Show events created in the last hour without removing them"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Calculate timestamp for one hour ago
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    
    # Find events created in the last hour
    cursor.execute('''
        SELECT id, title, start_datetime, created_at 
        FROM events 
        WHERE created_at > ? 
        ORDER BY created_at DESC
    ''', (one_hour_ago,))
    
    recent_events = cursor.fetchall()
    conn.close()
    
    if not recent_events:
        print("No events found that were created in the last hour")
        return
    
    print(f"Found {len(recent_events)} events created in the last hour:")
    for event_id, title, start_datetime, created_at in recent_events:
        print(f"  - ID {event_id}: {title[:50]}... (created: {created_at})")

def main():
    """Main function"""
    print("Precise Recent Events Removal Tool")
    print("=" * 40)
    
    if not os.path.exists(DATABASE):
        print(f"Error: Database file '{DATABASE}' not found")
        return
    
    # Check if created_at column exists
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(events)")
    columns = [column[1] for column in cursor.fetchall()]
    conn.close()
    
    if 'created_at' not in columns:
        print("Error: created_at column not found in events table")
        print("Please run the database migration first")
        return
    
    # Show recent events first
    show_recent_events()
    
    # Ask if user wants to remove them
    if input("\nDo you want to remove these events? (y/N): ").strip().lower() == 'y':
        remove_events_from_last_hour()

if __name__ == "__main__":
    main()

