#!/usr/bin/env python3
"""
Quick Load More Testing Script
Simple script to test Load More functionality on specific websites
"""

import sys
import os
import time
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_web_scraper import EnhancedWebScraper

def test_single_website(url: str, description: str = ""):
    """Test a single website quickly"""
    print(f"\n🧪 Testing: {description}")
    print(f"🌐 URL: {url}")
    print("-" * 60)
    
    scraper = EnhancedWebScraper()
    
    try:
        start_time = time.time()
        result = scraper.test_scraper(url)
        end_time = time.time()
        
        print(f"✅ Success: {result['success']}")
        print(f"📊 Events Found: {result['events_found']}")
        print(f"🎯 Strategy: {result['strategy_used']}")
        print(f"⏱️  Time: {end_time - start_time:.2f}s")
        
        if result['sample_events']:
            print(f"\n📋 Sample Events:")
            for i, event in enumerate(result['sample_events'][:3], 1):
                print(f"   {i}. {event['title']}")
                if event['date']:
                    print(f"      📅 {event['date']}")
                if event['location']:
                    print(f"      📍 {event['location']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def main():
    """Quick test of key websites"""
    print("🚀 QUICK LOAD MORE TESTING")
    print("=" * 60)
    
    # Test key websites
    test_cases = [
        {
            'url': 'https://www.aspeninstitute.org/our-work/events/',
            'description': 'Aspen Institute - Load More Button Test'
        },
        {
            'url': 'https://www.wharfdc.com/upcoming-events',
            'description': 'Wharf DC - Static Events Test'
        },
        {
            'url': 'https://www.washingtonian.com/calendar-2/',
            'description': 'Washingtonian - JavaScript Calendar Test'
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        result = test_single_website(test_case['url'], test_case['description'])
        if result:
            results.append(result)
        time.sleep(1)  # Be respectful
    
    # Summary
    print(f"\n📊 SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    total_events = sum(r['events_found'] for r in results)
    
    print(f"Tests Run: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Total Events Found: {total_events}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests == total_tests:
        print("✅ All tests passed! Load More logic is working.")
    else:
        print("⚠️  Some tests failed. Check the results above.")

if __name__ == "__main__":
    main()
