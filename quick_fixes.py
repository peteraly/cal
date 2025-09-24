"""
Quick fixes to implement bulletproof scraper improvements immediately
"""

import sqlite3
import json
import time
import random
import requests
from datetime import datetime
from enhanced_scraper import EnhancedWebScraper

class QuickScraperFixes:
    """Immediate improvements to prevent scraper failures"""
    
    def __init__(self):
        self.enhanced_scraper = EnhancedWebScraper()
    
    def reset_failing_scrapers(self):
        """Reset consecutive failures for scrapers"""
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Reset all failure counts
        cursor.execute('UPDATE web_scrapers SET consecutive_failures = 0')
        
        # Update last run times to enable fresh attempts
        cursor.execute('''
            UPDATE web_scrapers 
            SET last_run = datetime('now', '-2 hours')
            WHERE last_run IS NULL OR last_run < datetime('now', '-24 hours')
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Reset all scraper failure counts")
    
    def test_all_scrapers_safely(self):
        """Test all scrapers with enhanced error handling"""
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, url FROM web_scrapers WHERE is_active = 1')
        scrapers = cursor.fetchall()
        conn.close()
        
        results = {}
        
        for scraper_id, name, url in scrapers:
            print(f"\n🧪 Testing {name} ({url})")
            
            try:
                # Use enhanced scraper with better error handling
                events = self.enhanced_scraper.scrape_events(url)
                
                if events:
                    # Filter high-confidence events
                    good_events = [e for e in events if e.get('confidence_score', 0) >= 60]
                    
                    print(f"   ✅ Found {len(events)} events ({len(good_events)} high confidence)")
                    
                    # Sample best event
                    if good_events:
                        best_event = max(good_events, key=lambda x: x.get('confidence_score', 0))
                        print(f"   📅 Best event: {best_event.get('title', 'Unknown')[:50]}")
                        print(f"   📊 Confidence: {best_event.get('confidence_score', 0)}%")
                    
                    results[scraper_id] = {
                        'status': 'success',
                        'events_found': len(events),
                        'high_confidence_events': len(good_events),
                        'best_score': max(e.get('confidence_score', 0) for e in events) if events else 0
                    }
                else:
                    print(f"   ❌ No events found")
                    results[scraper_id] = {
                        'status': 'no_events',
                        'events_found': 0,
                        'high_confidence_events': 0,
                        'best_score': 0
                    }
                
                # Add delay to be respectful
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:100]}")
                results[scraper_id] = {
                    'status': 'error',
                    'error': str(e),
                    'events_found': 0,
                    'high_confidence_events': 0,
                    'best_score': 0
                }
        
        return results
    
    def update_scraper_health(self, test_results):
        """Update scraper health based on test results"""
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        for scraper_id, result in test_results.items():
            if result['status'] == 'success' and result['high_confidence_events'] > 0:
                # Success - reset failures and update last run
                cursor.execute('''
                    UPDATE web_scrapers 
                    SET consecutive_failures = 0, 
                        last_run = CURRENT_TIMESTAMP,
                        total_events = total_events + ?
                    WHERE id = ?
                ''', (result['high_confidence_events'], scraper_id))
                
            elif result['status'] == 'error':
                # Error - increment failures but cap at reasonable number
                cursor.execute('''
                    UPDATE web_scrapers 
                    SET consecutive_failures = MIN(consecutive_failures + 1, 10),
                        last_run = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (scraper_id,))
            
            else:
                # No events but no error - mild failure
                cursor.execute('''
                    UPDATE web_scrapers 
                    SET consecutive_failures = MIN(consecutive_failures + 1, 5),
                        last_run = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (scraper_id,))
        
        conn.commit()
        conn.close()
        print("\n✅ Updated scraper health metrics")
    
    def run_safe_scraping_for_best_scrapers(self, test_results):
        """Actually scrape and add events from the best performing scrapers"""
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Find scrapers that had success with high confidence events
        good_scrapers = [
            scraper_id for scraper_id, result in test_results.items()
            if result['status'] == 'success' and result['high_confidence_events'] > 0
        ]
        
        total_added = 0
        
        for scraper_id in good_scrapers:
            try:
                # Get scraper details
                cursor.execute('SELECT name, url FROM web_scrapers WHERE id = ?', (scraper_id,))
                row = cursor.fetchone()
                if not row:
                    continue
                
                name, url = row
                print(f"\n📥 Adding events from {name}")
                
                # Scrape events
                events = self.enhanced_scraper.scrape_events(url)
                high_conf_events = [e for e in events if e.get('confidence_score', 0) >= 60]
                
                events_added = 0
                for event in high_conf_events[:5]:  # Limit to 5 best events per scraper
                    title = event.get('title', '').strip()
                    description = event.get('description', '').strip()
                    start_date = event.get('start_date', '').strip() or datetime.now().isoformat()
                    location = event.get('location', '').strip()
                    price = event.get('price_info', '').strip()
                    event_url = event.get('url', url)
                    
                    if not title:
                        continue
                    
                    # Check if event already exists
                    cursor.execute('''
                        SELECT id FROM events WHERE title = ? AND start_datetime LIKE ?
                    ''', (title, f'%{start_date[:10]}%' if start_date else '%'))
                    
                    if not cursor.fetchone():
                        # Add to approval queue
                        cursor.execute('''
                            INSERT INTO events (title, description, start_datetime, location_name, 
                                              price_info, url, source, approval_status, created_at, category_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            title, description, start_date, location, price, event_url,
                            'scraper', 'pending', datetime.now().isoformat(), 1
                        ))
                        events_added += 1
                
                print(f"   ✅ Added {events_added} events to approval queue")
                total_added += events_added
                
                # Update scraper stats
                cursor.execute('''
                    UPDATE web_scrapers 
                    SET total_events = total_events + ?,
                        consecutive_failures = 0,
                        last_run = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (events_added, scraper_id))
                
            except Exception as e:
                print(f"   ❌ Error adding events: {str(e)}")
        
        conn.commit()
        conn.close()
        
        print(f"\n🎉 Total events added to approval queue: {total_added}")
        return total_added

def main():
    """Run immediate fixes and improvements"""
    print("🚀 Running Quick Scraper Fixes")
    print("=" * 50)
    
    fixer = QuickScraperFixes()
    
    # Step 1: Reset failing scrapers
    print("\n1️⃣ Resetting scraper failure counts...")
    fixer.reset_failing_scrapers()
    
    # Step 2: Test all scrapers safely
    print("\n2️⃣ Testing all scrapers with enhanced logic...")
    test_results = fixer.test_all_scrapers_safely()
    
    # Step 3: Update health metrics
    print("\n3️⃣ Updating health metrics...")
    fixer.update_scraper_health(test_results)
    
    # Step 4: Add events from successful scrapers
    print("\n4️⃣ Adding events from successful scrapers...")
    total_added = fixer.run_safe_scraping_for_best_scrapers(test_results)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    
    successful_scrapers = sum(1 for r in test_results.values() if r['status'] == 'success')
    total_scrapers = len(test_results)
    
    print(f"✅ Successful scrapers: {successful_scrapers}/{total_scrapers}")
    print(f"📅 Events added to approval queue: {total_added}")
    print(f"🎯 Success rate: {successful_scrapers/total_scrapers*100:.1f}%")
    
    if total_added > 0:
        print(f"\n🔗 Check new events at: http://localhost:5001/admin/approval")
    
    print("\n🎉 Quick fixes complete!")

if __name__ == "__main__":
    main()
