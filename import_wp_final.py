#!/usr/bin/env python3
"""
Final script to import Washington Post events with authentication
"""

import requests
import json
from washington_post_parser import WashingtonPostParser

def import_wp_events():
    """Import Washington Post events with proper authentication"""
    
    # Create a session to maintain login
    session = requests.Session()
    
    # First, login to get session
    print("🔐 Logging in to admin panel...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        # Login
        login_response = session.post('http://localhost:5001/admin/login', data=login_data)
        if login_response.status_code != 200:
            print("❌ Login failed")
            return False
        
        print("✅ Successfully logged in")
        
        # Read the events file
        try:
            with open('events - Washington Post.txt', 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"✅ Read events file ({len(content)} characters)")
        except FileNotFoundError:
            print("❌ Events file not found")
            return False
        
        # Parse events to see what we're working with
        parser = WashingtonPostParser()
        events = parser.parse_content(content)
        print(f"📊 Found {len(events)} events to import")
        
        if not events:
            print("❌ No events found in file")
            return False
        
        # Show preview
        print("\n📋 Events to import:")
        for i, event in enumerate(events[:3], 1):
            print(f"  {i}. {event.title}")
            print(f"     📍 {event.location_name}")
            print(f"     📅 {event.date} at {event.time}")
            print(f"     💰 {event.price}")
        
        if len(events) > 3:
            print(f"  ... and {len(events) - 3} more events")
        
        # Import via API
        print("\n🚀 Importing events...")
        import_response = session.post('http://localhost:5001/api/import/washington-post', 
                                     json={'content': content},
                                     headers={'Content-Type': 'application/json'})
        
        if import_response.status_code == 200:
            result = import_response.json()
            print(f"✅ Import successful!")
            print(f"   📥 Imported: {result['imported']} new events")
            print(f"   ⏭️  Skipped: {result['skipped']} duplicates")
            print(f"   📊 Total parsed: {result['total_parsed']} events")
            
            if result['imported'] > 0:
                print(f"\n🎉 Successfully added {result['imported']} Washington Post events to your calendar!")
                print("🌐 View them at: http://localhost:5001/admin")
            
            return True
        else:
            print(f"❌ Import failed: {import_response.status_code}")
            try:
                error_data = import_response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {import_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🎯 Washington Post Events Importer")
    print("=" * 40)
    
    success = import_wp_events()
    
    if success:
        print("\n✅ All done! Washington Post events have been imported.")
    else:
        print("\n❌ Import failed. Please check the errors above.")



