#!/usr/bin/env python3
"""
Test script to verify RSS feed addition is working
"""

import requests
import sys

def test_rss_feed_addition():
    """Test RSS feed addition functionality"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🧪 Testing RSS Feed Addition...")
    print("=" * 40)
    
    # Test 1: Login
    print("1. Testing admin login...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    response = session.post('http://localhost:5001/admin/login', data=login_data, allow_redirects=False)
    if response.status_code == 302 and 'admin' in response.headers.get('Location', ''):
        print("   ✅ Login successful")
    else:
        print("   ❌ Login failed")
        return False
    
    # Test 2: Get current feeds
    print("2. Getting current feeds...")
    response = session.get('http://localhost:5001/api/rss-feeds')
    if response.status_code == 200:
        feeds = response.json()
        print(f"   ✅ Found {len(feeds)} existing feeds")
    else:
        print("   ❌ Failed to get feeds")
        return False
    
    # Test 3: Add a new RSS feed
    print("3. Adding new RSS feed...")
    feed_data = {
        'name': 'Test RSS Feed 2',
        'url': 'https://feeds.npr.org/1001/rss.xml',
        'description': 'Test feed for verification',
        'category': 'news',
        'update_interval': 30
    }
    
    response = session.post('http://localhost:5001/api/rss-feeds', 
                          json=feed_data,
                          headers={'Content-Type': 'application/json'})
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Feed added successfully: {result.get('message', '')}")
    else:
        print(f"   ❌ Failed to add feed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False
    
    # Test 4: Verify feed was added
    print("4. Verifying feed was added...")
    response = session.get('http://localhost:5001/api/rss-feeds')
    if response.status_code == 200:
        new_feeds = response.json()
        if len(new_feeds) > len(feeds):
            print(f"   ✅ Feed count increased from {len(feeds)} to {len(new_feeds)}")
        else:
            print("   ❌ Feed count did not increase")
            return False
    else:
        print("   ❌ Failed to verify feeds")
        return False
    
    print("\n🎉 All tests passed! RSS feed addition is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = test_rss_feed_addition()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
