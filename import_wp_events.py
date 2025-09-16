#!/usr/bin/env python3
"""
Script to import all Washington Post events from the file
"""

import requests
import json
import time
from washington_post_parser import WashingtonPostParser

def import_washington_post_events():
    """Import all events from the Washington Post file"""
    
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(3)
    
    # Read the events file content
    try:
        with open('events - Washington Post.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Successfully read events file ({len(content)} characters)")
    except FileNotFoundError:
        print("❌ Error: 'events - Washington Post.txt' file not found")
        print("Please make sure the file is in the current directory")
        return False
    
    # Parse events first to see what we're working with
    parser = WashingtonPostParser()
    events = parser.parse_content(content)
    print(f"📊 Parsed {len(events)} events from the file")
    
    if not events:
        print("❌ No events found in the file")
        return False
    
    # Show preview of first few events
    print("\n📋 Preview of events to be imported:")
    for i, event in enumerate(events[:5], 1):
        print(f"  {i}. {event.title}")
        print(f"     📍 {event.location_name}")
        print(f"     📅 {event.date} at {event.time}")
        print(f"     💰 {event.price}")
        print()
    
    if len(events) > 5:
        print(f"  ... and {len(events) - 5} more events")
    
    # Import events via API
    print("🚀 Importing events to the database...")
    try:
        response = requests.post('http://localhost:5001/api/import/washington-post', 
                               json={'content': content},
                               headers={'Content-Type': 'application/json'},
                               timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Import completed successfully!")
            print(f"   📥 Imported: {result['imported']} events")
            print(f"   ⏭️  Skipped: {result['skipped']} events (duplicates)")
            print(f"   📊 Total parsed: {result['total_parsed']} events")
            
            if result['imported'] > 0:
                print(f"\n🎉 Successfully added {result['imported']} new events to your calendar!")
                print("You can now view them in your admin dashboard at http://localhost:5001/admin")
            
            return True
        else:
            error_data = response.json()
            print(f"❌ Import failed: {error_data.get('error', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the server")
        print("Make sure the server is running on localhost:5001")
        return False
    except requests.exceptions.Timeout:
        print("❌ Error: Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Washington Post Events Importer")
    print("=" * 40)
    
    success = import_washington_post_events()
    
    if success:
        print("\n✅ All done! Your events have been imported successfully.")
    else:
        print("\n❌ Import failed. Please check the errors above.")


