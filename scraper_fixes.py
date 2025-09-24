"""
Specific fixes for problematic scrapers
Addresses JavaScript-heavy sites and bot detection
"""

import requests
import time
import random
from bs4 import BeautifulSoup
# Selenium imports (optional - install with: pip install selenium)
# from selenium import webdriver
import sqlite3
import json
from datetime import datetime, timedelta

class ScraperFixes:
    """Fix specific scraper issues"""
    
    def __init__(self):
        self.session = requests.Session()
        self.setup_session()
    
    def setup_session(self):
        """Setup session with better headers"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
    
    def fix_cato_institute(self):
        """Fix Cato Institute scraper - likely bot detection"""
        print("🔧 Fixing Cato Institute...")
        
        # Try alternative endpoints
        alternative_urls = [
            'https://www.cato.org/events',  # Remove /upcoming
            'https://www.cato.org/multimedia/events',
            'https://www.cato.org/events/upcoming'
        ]
        
        for url in alternative_urls:
            try:
                print(f"   Trying: {url}")
                time.sleep(random.uniform(2, 4))  # Random delay
                
                response = self.session.get(url, timeout=15)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200 and len(response.text) > 1000:
                    print(f"   ✅ Success! Content size: {len(response.text)}")
                    return self._update_scraper_url('Cato', url)
                    
            except Exception as e:
                print(f"   Failed: {e}")
                
        return False
    
    def fix_volo_sports(self):
        """Fix Volo Sports - JavaScript heavy site"""
        print("🔧 Fixing Volo Sports...")
        
        # Try the main events page instead
        alternative_urls = [
            'https://www.volosports.com/events',
            'https://www.volosports.com/leagues',
            'https://www.volosports.com/discover/washington-dc'
        ]
        
        for url in alternative_urls:
            try:
                print(f"   Trying: {url}")
                time.sleep(random.uniform(2, 4))
                
                response = self.session.get(url, timeout=15)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Check for actual content
                    soup = BeautifulSoup(response.content, 'html.parser')
                    text_content = soup.get_text()
                    
                    if len(text_content) > 500 and 'enable JavaScript' not in text_content:
                        print(f"   ✅ Found content! Size: {len(text_content)}")
                        return self._update_scraper_url('Volo', url)
                        
            except Exception as e:
                print(f"   Failed: {e}")
        
        return False
    
    def fix_smithsonian(self):
        """Fix Smithsonian - try different event endpoints"""
        print("🔧 Fixing Smithsonian...")
        
        alternative_urls = [
            'https://www.si.edu/events/upcoming',
            'https://naturalhistory.si.edu/events',
            'https://americanhistory.si.edu/events',
            'https://airandspace.si.edu/events'
        ]
        
        for url in alternative_urls:
            try:
                print(f"   Trying: {url}")
                time.sleep(random.uniform(2, 4))
                
                response = self.session.get(url, timeout=15)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for event indicators
                    events = soup.find_all(['article', 'div'], class_=lambda x: x and 'event' in x.lower())
                    if len(events) > 0:
                        print(f"   ✅ Found {len(events)} potential events!")
                        return self._update_scraper_url('Smithsonian', url)
                        
            except Exception as e:
                print(f"   Failed: {e}")
        
        return False
    
    def fix_pacers_running(self):
        """Fix Pacers Running - try different approach"""
        print("🔧 Fixing Pacers Running...")
        
        # Try different event URLs
        alternative_urls = [
            'https://runpacers.com/events',
            'https://runpacers.com/calendar',
            'https://runpacers.com/training',
            'https://runpacers.com/pages/events'  # Original
        ]
        
        for url in alternative_urls:
            try:
                print(f"   Trying: {url}")
                time.sleep(random.uniform(2, 4))
                
                response = self.session.get(url, timeout=15)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for running/fitness related content
                    content_indicators = [
                        soup.find_all(string=lambda text: text and any(word in text.lower() for word in ['run', 'training', 'race', 'marathon', 'fitness'])),
                        soup.find_all(['div', 'article'], class_=lambda x: x and any(word in x.lower() for word in ['event', 'training', 'run']))
                    ]
                    
                    total_matches = sum(len(indicator) for indicator in content_indicators)
                    if total_matches > 5:
                        print(f"   ✅ Found running content! Matches: {total_matches}")
                        return self._update_scraper_url('Pacers Running', url)
                        
            except Exception as e:
                print(f"   Failed: {e}")
        
        return False
    
    def _update_scraper_url(self, scraper_name, new_url):
        """Update scraper URL in database"""
        try:
            conn = sqlite3.connect('calendar.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE web_scrapers 
                SET url = ?, consecutive_failures = 0, last_run = NULL
                WHERE name = ?
            ''', (new_url, scraper_name))
            
            if cursor.rowcount > 0:
                conn.commit()
                print(f"   ✅ Updated {scraper_name} URL to: {new_url}")
                conn.close()
                return True
            else:
                print(f"   ❌ Scraper {scraper_name} not found in database")
                conn.close()
                return False
                
        except Exception as e:
            print(f"   ❌ Database error: {e}")
            return False
    
    def add_working_scrapers(self):
        """Add some known working event sources"""
        print("🔧 Adding reliable event sources...")
        
        working_sources = [
            {
                'name': 'Eventbrite DC',
                'url': 'https://www.eventbrite.com/d/dc--washington/events/',
                'description': 'Eventbrite events in DC area'
            },
            {
                'name': 'Facebook Events DC',
                'url': 'https://www.facebook.com/events/search/?q=washington%20dc',
                'description': 'Facebook events in Washington DC'
            },
            {
                'name': 'Meetup DC',
                'url': 'https://www.meetup.com/find/?location=us--dc--washington&source=EVENTS',
                'description': 'Meetup events in Washington DC'
            }
        ]
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        added_count = 0
        for source in working_sources:
            try:
                # Check if already exists
                cursor.execute('SELECT id FROM web_scrapers WHERE name = ?', (source['name'],))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO web_scrapers (name, url, description, category, update_interval, is_active, selector_config)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        source['name'], source['url'], source['description'],
                        'events', 10, True, None
                    ))
                    added_count += 1
                    print(f"   ✅ Added: {source['name']}")
                else:
                    print(f"   ⚠️  Already exists: {source['name']}")
                    
            except Exception as e:
                print(f"   ❌ Error adding {source['name']}: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ Added {added_count} new reliable sources")
        return added_count > 0

def main():
    """Run all scraper fixes"""
    print("🚀 RUNNING SCRAPER FIXES")
    print("=" * 50)
    
    fixes = ScraperFixes()
    
    # Try to fix each problematic scraper
    results = {
        'Cato Institute': fixes.fix_cato_institute(),
        'Volo Sports': fixes.fix_volo_sports(),
        'Smithsonian': fixes.fix_smithsonian(),
        'Pacers Running': fixes.fix_pacers_running()
    }
    
    print("\n📊 FIX RESULTS:")
    for scraper, success in results.items():
        status = "✅ Fixed" if success else "❌ Still problematic"
        print(f"   {scraper}: {status}")
    
    # Add working sources
    print("\n🔧 Adding reliable sources...")
    fixes.add_working_scrapers()
    
    print("\n🎯 RECOMMENDATIONS:")
    print("   1. Consider Selenium for JavaScript-heavy sites")
    print("   2. Use proxy rotation for bot-protected sites")
    print("   3. Add more reliable event sources (Eventbrite, Meetup)")
    print("   4. Focus on RSS feeds where available")
    
    fixed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n📈 SUMMARY: {fixed_count}/{total_count} scrapers improved")

if __name__ == "__main__":
    main()
