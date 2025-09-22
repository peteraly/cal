#!/usr/bin/env python3
"""
URL Pattern Discovery Testing
Tests the specific logic that discovers URL patterns to bypass Load More buttons
"""

import sys
import os
import time
import requests
from bs4 import BeautifulSoup

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_url_patterns(url: str, description: str = ""):
    """Test different URL patterns to find the one with most events"""
    print(f"\n🔍 URL Pattern Testing: {description}")
    print(f"🌐 Base URL: {url}")
    print("-" * 80)
    
    # URL patterns to test
    patterns = [
        url,                           # Original URL
        url + '#all-events',          # Hash-based loading
        url + '?all=true',            # Show all parameter
        url + '?limit=100',           # High limit
        url + '?limit=1000',          # Very high limit
        url + '?page=1&limit=100',    # Page with high limit
        url + '?page=2&limit=100',    # Multiple pages
        url + '?offset=0&limit=100',  # Offset-based
        url + '?offset=20&limit=100',
        url + '?offset=40&limit=100',
        url + '?view=all',            # View all parameter
        url + '?show=all',            # Show all parameter
        url + '?display=all',         # Display all parameter
        url + '?format=json',         # JSON format
        url.replace('/events/', '/api/events'), # API endpoint
        url + '/api',                 # API path
        url + '/json'                 # JSON path
    ]
    
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })
    
    results = []
    
    for i, pattern_url in enumerate(patterns, 1):
        print(f"{i:2d}. Testing: {pattern_url}")
        
        try:
            response = session.get(pattern_url, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Count event containers
                event_containers = soup.find_all(['article', 'div'], 
                                               class_=lambda x: x and any(word in x.lower() 
                                               for word in ['event', 'card', 'item']))
                
                # Count potential event elements
                potential_events = soup.find_all(['article', 'div', 'li'], 
                                               class_=lambda x: x and any(word in x.lower() 
                                               for word in ['event', 'card', 'item', 'listing']))
                
                # Try to find event titles
                event_titles = soup.find_all(['h1', 'h2', 'h3', 'h4'], 
                                           class_=lambda x: x and any(word in x.lower() 
                                           for word in ['title', 'event', 'name']))
                
                print(f"    📊 Containers: {len(event_containers)}")
                print(f"    📊 Potential Events: {len(potential_events)}")
                print(f"    📊 Event Titles: {len(event_titles)}")
                
                # Try to parse as JSON
                try:
                    json_data = response.json()
                    if isinstance(json_data, list):
                        print(f"    📊 JSON Array: {len(json_data)} items")
                    elif isinstance(json_data, dict):
                        print(f"    📊 JSON Object: {len(json_data)} keys")
                except:
                    pass
                
                results.append({
                    'url': pattern_url,
                    'status': response.status_code,
                    'containers': len(event_containers),
                    'potential_events': len(potential_events),
                    'event_titles': len(event_titles),
                    'content_length': len(response.text),
                    'success': True
                })
                
            else:
                print(f"    ❌ HTTP {response.status_code}")
                results.append({
                    'url': pattern_url,
                    'status': response.status_code,
                    'containers': 0,
                    'potential_events': 0,
                    'event_titles': 0,
                    'content_length': 0,
                    'success': False
                })
                
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            results.append({
                'url': pattern_url,
                'status': 'error',
                'containers': 0,
                'potential_events': 0,
                'event_titles': 0,
                'content_length': 0,
                'success': False,
                'error': str(e)
            })
        
        time.sleep(0.5)  # Be respectful
    
    # Find the best pattern
    print(f"\n🏆 ANALYSIS")
    print("-" * 80)
    
    # Sort by containers found
    successful_results = [r for r in results if r['success']]
    if successful_results:
        best_by_containers = max(successful_results, key=lambda x: x['containers'])
        best_by_events = max(successful_results, key=lambda x: x['potential_events'])
        best_by_titles = max(successful_results, key=lambda x: x['event_titles'])
        
        print(f"🥇 Best by Containers: {best_by_containers['url']}")
        print(f"   📊 Containers: {best_by_containers['containers']}")
        
        print(f"🥇 Best by Potential Events: {best_by_events['url']}")
        print(f"   📊 Potential Events: {best_by_events['potential_events']}")
        
        print(f"🥇 Best by Event Titles: {best_by_titles['url']}")
        print(f"   📊 Event Titles: {best_by_titles['event_titles']}")
        
        # Overall best
        overall_best = max(successful_results, key=lambda x: x['containers'] + x['potential_events'] + x['event_titles'])
        print(f"\n🏆 OVERALL BEST: {overall_best['url']}")
        print(f"   📊 Total Score: {overall_best['containers'] + overall_best['potential_events'] + overall_best['event_titles']}")
        print(f"   📊 Containers: {overall_best['containers']}")
        print(f"   📊 Potential Events: {overall_best['potential_events']}")
        print(f"   📊 Event Titles: {overall_best['event_titles']}")
    
    return results

def main():
    """Test URL patterns for key websites"""
    print("🔍 URL PATTERN DISCOVERY TESTING")
    print("=" * 80)
    print("This script tests different URL patterns to find the one that")
    print("loads the most events, bypassing Load More buttons.")
    print("=" * 80)
    
    # Test key websites
    test_cases = [
        {
            'url': 'https://www.aspeninstitute.org/our-work/events/',
            'description': 'Aspen Institute Events'
        },
        {
            'url': 'https://www.wharfdc.com/upcoming-events',
            'description': 'Wharf DC Events'
        },
        {
            'url': 'https://www.washingtonian.com/calendar-2/',
            'description': 'Washingtonian Calendar'
        }
    ]
    
    all_results = []
    
    for test_case in test_cases:
        results = test_url_patterns(test_case['url'], test_case['description'])
        all_results.extend(results)
        time.sleep(2)  # Be respectful between tests
    
    # Overall summary
    print(f"\n📊 OVERALL SUMMARY")
    print("=" * 80)
    
    total_tests = len(all_results)
    successful_tests = sum(1 for r in all_results if r['success'])
    total_containers = sum(r['containers'] for r in all_results)
    total_events = sum(r['potential_events'] for r in all_results)
    
    print(f"Total URL Patterns Tested: {total_tests}")
    print(f"Successful Requests: {successful_tests}")
    print(f"Total Event Containers Found: {total_containers}")
    print(f"Total Potential Events Found: {total_events}")
    print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%")
    
    if successful_tests > 0:
        print(f"\n✅ URL Pattern Discovery is working!")
        print(f"Found {total_containers} event containers across all patterns.")
    else:
        print(f"\n❌ No successful URL patterns found.")

if __name__ == "__main__":
    main()
