#!/usr/bin/env python3
"""
QA Testing Script for Load More Button Logic
Tests the enhanced web scraper's ability to handle "Load More" buttons and pull all events
"""

import sys
import os
import time
import logging
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_web_scraper import EnhancedWebScraper

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoadMoreQATester:
    def __init__(self):
        self.scraper = EnhancedWebScraper()
        self.test_results = []
    
    def test_website(self, url: str, expected_min_events: int = 1, description: str = ""):
        """Test a single website and record results"""
        print(f"\n{'='*80}")
        print(f"🧪 TESTING: {description}")
        print(f"🌐 URL: {url}")
        print(f"📊 Expected Min Events: {expected_min_events}")
        print(f"{'='*80}")
        
        start_time = time.time()
        
        try:
            # Test the scraper
            result = self.scraper.test_scraper(url)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            # Analyze results
            success = result['success']
            events_found = result['events_found']
            strategy_used = result['strategy_used']
            sample_events = result['sample_events']
            
            # Determine if test passed
            test_passed = success and events_found >= expected_min_events
            
            # Print results
            status_emoji = "✅ PASS" if test_passed else "❌ FAIL"
            print(f"\n{status_emoji} Test Result:")
            print(f"   Success: {success}")
            print(f"   Events Found: {events_found}")
            print(f"   Strategy Used: {strategy_used}")
            print(f"   Response Time: {response_time:.2f}s")
            print(f"   Expected Min: {expected_min_events}")
            
            if sample_events:
                print(f"\n📋 Sample Events Found:")
                for i, event in enumerate(sample_events[:3], 1):
                    print(f"   {i}. {event['title']}")
                    if event['date']:
                        print(f"      📅 Date: {event['date']}")
                    if event['location']:
                        print(f"      📍 Location: {event['location']}")
                    if event['price']:
                        print(f"      💰 Price: {event['price']}")
                    print()
            
            # Record test result
            test_result = {
                'url': url,
                'description': description,
                'success': success,
                'events_found': events_found,
                'strategy_used': strategy_used,
                'response_time': response_time,
                'expected_min': expected_min_events,
                'test_passed': test_passed,
                'sample_events': sample_events,
                'timestamp': datetime.now().isoformat()
            }
            
            self.test_results.append(test_result)
            
            return test_result
            
        except Exception as e:
            print(f"\n❌ ERROR: {str(e)}")
            error_result = {
                'url': url,
                'description': description,
                'success': False,
                'events_found': 0,
                'strategy_used': 'error',
                'response_time': time.time() - start_time,
                'expected_min': expected_min_events,
                'test_passed': False,
                'sample_events': [],
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            self.test_results.append(error_result)
            return error_result
    
    def test_load_more_strategies(self):
        """Test different types of Load More implementations"""
        print("🚀 STARTING LOAD MORE QA TESTING")
        print("="*80)
        
        # Test cases for different Load More scenarios
        test_cases = [
            {
                'url': 'https://www.aspeninstitute.org/our-work/events/',
                'expected_min': 20,
                'description': 'Aspen Institute - JavaScript Heavy with Load More (URL Pattern Discovery)'
            },
            {
                'url': 'https://www.wharfdc.com/upcoming-events',
                'expected_min': 1,
                'description': 'Wharf DC - Static HTML Events'
            },
            {
                'url': 'https://www.washingtonian.com/calendar-2/',
                'expected_min': 1,
                'description': 'Washingtonian - JavaScript Heavy Calendar'
            },
            {
                'url': 'https://www.kennedy-center.org/events/',
                'expected_min': 5,
                'description': 'Kennedy Center - Traditional Event Site'
            },
            {
                'url': 'https://www.politics-prose.com/events',
                'expected_min': 1,
                'description': 'Politics & Prose - Bookstore Events'
            }
        ]
        
        # Run all tests
        for test_case in test_cases:
            self.test_website(
                test_case['url'],
                test_case['expected_min'],
                test_case['description']
            )
            time.sleep(2)  # Be respectful between tests
    
    def test_url_pattern_discovery(self):
        """Test the URL pattern discovery logic specifically"""
        print("\n🔍 TESTING URL PATTERN DISCOVERY")
        print("="*80)
        
        # Test Aspen Institute URL patterns
        aspen_url = 'https://www.aspeninstitute.org/our-work/events/'
        
        print(f"Testing URL pattern discovery for: {aspen_url}")
        
        # Test different URL patterns
        test_patterns = [
            aspen_url,
            aspen_url + '?all=true',
            aspen_url + '?limit=1000',
            aspen_url + '?view=all',
            aspen_url + '?show=all',
            aspen_url + '?display=all'
        ]
        
        pattern_results = []
        
        for pattern_url in test_patterns:
            print(f"\n🧪 Testing pattern: {pattern_url}")
            try:
                response = self.scraper.session.get(pattern_url, timeout=30)
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    event_containers = soup.find_all(['article', 'div'], 
                                                   class_=lambda x: x and any(word in x.lower() 
                                                   for word in ['event', 'card', 'item']))
                    
                    print(f"   📊 Found {len(event_containers)} event containers")
                    pattern_results.append({
                        'url': pattern_url,
                        'containers': len(event_containers),
                        'success': True
                    })
                else:
                    print(f"   ❌ HTTP {response.status_code}")
                    pattern_results.append({
                        'url': pattern_url,
                        'containers': 0,
                        'success': False
                    })
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                pattern_results.append({
                    'url': pattern_url,
                    'containers': 0,
                    'success': False,
                    'error': str(e)
                })
        
        # Find best pattern
        best_pattern = max(pattern_results, key=lambda x: x['containers'])
        print(f"\n🏆 Best URL Pattern: {best_pattern['url']}")
        print(f"   📊 Containers Found: {best_pattern['containers']}")
    
    def test_strategy_detection(self):
        """Test the strategy detection logic"""
        print("\n🎯 TESTING STRATEGY DETECTION")
        print("="*80)
        
        test_urls = [
            'https://www.aspeninstitute.org/our-work/events/',
            'https://www.wharfdc.com/upcoming-events',
            'https://www.washingtonian.com/calendar-2/',
            'https://www.kennedy-center.org/events/'
        ]
        
        for url in test_urls:
            print(f"\n🔍 Testing strategy detection for: {url}")
            try:
                response = self.scraper.session.get(url, timeout=30)
                if response.status_code == 200:
                    strategy = self.scraper.detect_scraping_strategy(url, response.text)
                    print(f"   🎯 Detected Strategy: {strategy}")
                else:
                    print(f"   ❌ HTTP {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        print("\n📊 GENERATING QA TEST REPORT")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['test_passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"📈 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print(f"\n📋 Detailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status = "✅ PASS" if result['test_passed'] else "❌ FAIL"
            print(f"   {i}. {status} - {result['description']}")
            print(f"      Events: {result['events_found']}/{result['expected_min']}")
            print(f"      Strategy: {result['strategy_used']}")
            print(f"      Time: {result['response_time']:.2f}s")
            if 'error' in result:
                print(f"      Error: {result['error']}")
            print()
        
        # Strategy analysis
        strategies_used = {}
        for result in self.test_results:
            strategy = result['strategy_used']
            if strategy not in strategies_used:
                strategies_used[strategy] = {'count': 0, 'success': 0}
            strategies_used[strategy]['count'] += 1
            if result['test_passed']:
                strategies_used[strategy]['success'] += 1
        
        print(f"🎯 Strategy Analysis:")
        for strategy, stats in strategies_used.items():
            success_rate = (stats['success']/stats['count'])*100
            print(f"   {strategy}: {stats['count']} tests, {success_rate:.1f}% success rate")
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests/total_tests)*100,
            'strategies_used': strategies_used,
            'detailed_results': self.test_results
        }

def main():
    """Main QA testing function"""
    print("🧪 LOAD MORE BUTTON QA TESTING SUITE")
    print("="*80)
    print("This script tests the enhanced web scraper's ability to handle")
    print("'Load More' buttons and pull all events from websites.")
    print("="*80)
    
    tester = LoadMoreQATester()
    
    # Run all tests
    tester.test_load_more_strategies()
    tester.test_url_pattern_discovery()
    tester.test_strategy_detection()
    
    # Generate report
    report = tester.generate_report()
    
    print(f"\n🎉 QA Testing Complete!")
    print(f"Success Rate: {report['success_rate']:.1f}%")
    
    if report['success_rate'] >= 80:
        print("✅ Overall Result: PASS - Load More logic is working well")
    elif report['success_rate'] >= 60:
        print("⚠️  Overall Result: PARTIAL - Some issues detected")
    else:
        print("❌ Overall Result: FAIL - Significant issues detected")

if __name__ == "__main__":
    main()
