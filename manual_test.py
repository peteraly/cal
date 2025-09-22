#!/usr/bin/env python3
"""
Manual Testing Script for Load More Logic
Simple script to manually test specific URLs and see the results
"""

import sys
import os
import time

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_web_scraper import EnhancedWebScraper

def manual_test():
    """Manual testing function"""
    print("🧪 MANUAL LOAD MORE TESTING")
    print("=" * 60)
    print("Enter a URL to test the Load More logic")
    print("Type 'quit' to exit")
    print("=" * 60)
    
    scraper = EnhancedWebScraper()
    
    while True:
        print(f"\n🌐 Enter URL to test (or 'quit' to exit):")
        url = input("> ").strip()
        
        if url.lower() == 'quit':
            print("👋 Goodbye!")
            break
        
        if not url:
            print("❌ Please enter a valid URL")
            continue
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        print(f"\n🧪 Testing: {url}")
        print("-" * 60)
        
        try:
            start_time = time.time()
            result = scraper.test_scraper(url)
            end_time = time.time()
            
            print(f"✅ Success: {result['success']}")
            print(f"📊 Events Found: {result['events_found']}")
            print(f"🎯 Strategy Used: {result['strategy_used']}")
            print(f"⏱️  Response Time: {end_time - start_time:.2f}s")
            
            if result['sample_events']:
                print(f"\n📋 Sample Events:")
                for i, event in enumerate(result['sample_events'], 1):
                    print(f"   {i}. {event['title']}")
                    if event['date']:
                        print(f"      📅 Date: {event['date']}")
                    if event['location']:
                        print(f"      📍 Location: {event['location']}")
                    if event['price']:
                        print(f"      💰 Price: {event['price']}")
                    if event['description']:
                        print(f"      📝 Description: {event['description'][:100]}...")
                    print()
            else:
                print("   No events found")
            
            if not result['success']:
                print(f"❌ Error: {result['message']}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n" + "=" * 60)

if __name__ == "__main__":
    manual_test()
