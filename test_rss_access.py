#!/usr/bin/env python3
"""
Test script to verify RSS feeds access is working
"""

import requests
import sys

def test_rss_access():
    """Test RSS feeds access with proper authentication"""
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    print("🧪 Testing RSS Feeds Access...")
    print("=" * 40)
    
    # Test 1: Try to access RSS feeds without login (should redirect)
    print("1. Testing RSS feeds without login...")
    response = session.get('http://localhost:5001/admin/rss-feeds', allow_redirects=False)
    if response.status_code == 302 and 'admin/login' in response.headers.get('Location', ''):
        print("   ✅ Correctly redirects to login")
    else:
        print("   ❌ Should redirect to login")
        print(f"   Status: {response.status_code}, Location: {response.headers.get('Location', 'None')}")
        return False
    
    # Test 2: Login
    print("2. Testing admin login...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    response = session.post('http://localhost:5001/admin/login', data=login_data, allow_redirects=False)
    if response.status_code == 302 and 'admin' in response.headers.get('Location', ''):
        print("   ✅ Login successful")
    else:
        print("   ❌ Login failed")
        print(f"   Status: {response.status_code}, Location: {response.headers.get('Location', 'None')}")
        return False
    
    # Test 3: Access RSS feeds after login
    print("3. Testing RSS feeds after login...")
    response = session.get('http://localhost:5001/admin/rss-feeds')
    if 'RSS Feeds Management' in response.text:
        print("   ✅ RSS feeds page accessible")
    else:
        print("   ❌ RSS feeds page not accessible")
        print(f"   Response: {response.text[:200]}...")
        return False
    
    # Test 4: Test RSS API
    print("4. Testing RSS API...")
    response = session.get('http://localhost:5001/api/rss-feeds')
    if response.status_code == 200:
        print("   ✅ RSS API accessible")
    else:
        print(f"   ❌ RSS API not accessible (status: {response.status_code})")
        return False
    
    print("\n🎉 All tests passed! RSS feeds access is working correctly.")
    return True

if __name__ == "__main__":
    try:
        success = test_rss_access()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
