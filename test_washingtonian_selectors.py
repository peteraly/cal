#!/usr/bin/env python3
"""
Test script to find the right CSS selectors for Washingtonian calendar
Run this to inspect the HTML structure and find the best selectors
"""

import requests
from bs4 import BeautifulSoup
import json

def test_washingtonian_selectors():
    """Test different selectors on the Washingtonian calendar page"""
    
    url = "https://www.washingtonian.com/calendar-2/#/"
    
    print("🔍 Testing Washingtonian Calendar Selectors")
    print("=" * 50)
    
    try:
        # Fetch the page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print(f"✅ Successfully fetched: {url}")
        print(f"📄 Page title: {soup.title.string if soup.title else 'No title'}")
        print()
        
        # Test different potential selectors
        selectors_to_test = [
            # Common event container selectors
            '.event',
            '.event-item',
            '.calendar-event',
            '.event-card',
            '.event-list-item',
            '[class*="event"]',
            '[class*="calendar"]',
            '[class*="listing"]',
            
            # Generic containers
            'article',
            '.card',
            '.item',
            '.listing',
            '.post',
            
            # Div-based selectors
            'div[class*="event"]',
            'div[class*="calendar"]',
            'div[class*="listing"]',
            
            # List-based selectors
            'li[class*="event"]',
            'li[class*="calendar"]',
            'li[class*="listing"]',
        ]
        
        print("🧪 Testing Event Container Selectors:")
        print("-" * 40)
        
        best_selectors = []
        
        for selector in selectors_to_test:
            try:
                elements = soup.select(selector)
                if elements:
                    print(f"✅ {selector}: Found {len(elements)} elements")
                    
                    # Show first element's structure
                    if len(elements) > 0:
                        first_elem = elements[0]
                        print(f"   📋 First element: <{first_elem.name}> class='{first_elem.get('class', [])}'")
                        
                        # Look for text content that might be event titles
                        text_content = first_elem.get_text(strip=True)[:100]
                        if text_content:
                            print(f"   📝 Sample text: {text_content}...")
                        
                        best_selectors.append({
                            'selector': selector,
                            'count': len(elements),
                            'sample_text': text_content
                        })
                else:
                    print(f"❌ {selector}: No elements found")
            except Exception as e:
                print(f"⚠️  {selector}: Error - {e}")
        
        print()
        print("🎯 Best Selectors Found:")
        print("-" * 30)
        
        # Sort by count and show top 5
        best_selectors.sort(key=lambda x: x['count'], reverse=True)
        
        for i, selector_info in enumerate(best_selectors[:5], 1):
            print(f"{i}. {selector_info['selector']} ({selector_info['count']} elements)")
            if selector_info['sample_text']:
                print(f"   Sample: {selector_info['sample_text'][:80]}...")
            print()
        
        # Test title selectors within the best container
        if best_selectors:
            best_selector = best_selectors[0]['selector']
            print(f"🔍 Testing Title Selectors within: {best_selector}")
            print("-" * 50)
            
            containers = soup.select(best_selector)[:3]  # Test first 3 containers
            
            title_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                '.title', '.event-title', '.listing-title',
                'a', '.link', '.event-link',
                '[class*="title"]', '[class*="name"]', '[class*="heading"]'
            ]
            
            for container in containers:
                print(f"\n📦 Container {containers.index(container) + 1}:")
                
                for title_sel in title_selectors:
                    try:
                        title_elem = container.select_one(title_sel)
                        if title_elem:
                            title_text = title_elem.get_text(strip=True)
                            if title_text and len(title_text) > 5:  # Reasonable title length
                                print(f"   ✅ {title_sel}: '{title_text[:60]}...'")
                    except:
                        pass
        
        print()
        print("💡 Recommendations:")
        print("-" * 20)
        print("1. Use the selector with the most elements found above")
        print("2. For titles, try: h1, h2, h3, a, or .title")
        print("3. For dates, look for: .date, .event-date, time, or [class*='date']")
        print("4. For locations, try: .location, .venue, .address, or [class*='location']")
        print("5. Test the configuration in the web scraper interface")
        
        # Save results to file
        results = {
            'url': url,
            'best_selectors': best_selectors[:5],
            'recommendations': {
                'event_container': best_selectors[0]['selector'] if best_selectors else '.event',
                'title': 'h1, h2, h3, a, .title',
                'date': '.date, .event-date, time',
                'location': '.location, .venue, .address',
                'description': '.description, .event-description, p'
            }
        }
        
        with open('washingtonian_selectors.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: washingtonian_selectors.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your internet connection")
        print("2. The website might be blocking automated requests")
        print("3. Try using a different User-Agent or adding delays")
        print("4. The page might be JavaScript-heavy (try Selenium instead)")

if __name__ == "__main__":
    test_washingtonian_selectors()
