"""
Production Scraper Scheduler
Automatically scrapes all sources every 10 minutes with enhanced error handling
"""

import schedule
import time
import threading
import sqlite3
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from enhanced_scraper import EnhancedWebScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ProductionScraperScheduler:
    """Production scheduler that runs all scrapers every 10 minutes"""
    
    def __init__(self):
        self.scraper = EnhancedWebScraper()
        self.executor = ThreadPoolExecutor(max_workers=6)  # One per scraper
        self.is_running = False
        self.scheduler_thread = None
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'total_events_found': 0,
            'total_events_added': 0,
            'last_run': None
        }
    
    def start_scheduler(self):
        """Start the automated scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("🚀 Starting Production Scraper Scheduler")
        logger.info("📊 Schedule: Every 10 minutes")
        logger.info("🎯 Target: All active web scrapers")
        
        # Schedule scraping every 10 minutes
        schedule.every(10).minutes.do(self._run_all_scrapers)
        
        # Schedule health reporting every hour
        schedule.every(1).hours.do(self._report_health_stats)
        
        # Schedule daily cleanup
        schedule.every(1).days.do(self._cleanup_old_data)
        
        self.is_running = True
        
        # Run initial scrape immediately
        logger.info("🔄 Running initial scrape...")
        self._run_all_scrapers()
        
        # Start scheduler in separate thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("✅ Scheduler started successfully")
        logger.info("🔗 Monitor at: http://localhost:5001/admin/web-scrapers")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        logger.info("🛑 Stopping scheduler...")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _run_all_scrapers(self):
        """Run all active scrapers in parallel"""
        start_time = time.time()
        logger.info("🕷️ Starting scheduled scrape run")
        
        # Get all active scrapers
        scrapers = self._get_active_scrapers()
        if not scrapers:
            logger.warning("No active scrapers found")
            return
        
        logger.info(f"📋 Found {len(scrapers)} active scrapers")
        
        # Submit all scraping jobs
        futures = {}
        for scraper_data in scrapers:
            future = self.executor.submit(self._scrape_single_source, scraper_data)
            futures[future] = scraper_data
        
        # Collect results
        results = []
        for future in as_completed(futures, timeout=300):  # 5 minute timeout
            scraper_data = futures[future]
            try:
                result = future.result()
                results.append(result)
                
                if result['success']:
                    logger.info(f"✅ {result['name']}: {result['events_added']} events added")
                else:
                    logger.warning(f"❌ {result['name']}: {result['error']}")
                    
            except Exception as e:
                logger.error(f"❌ {scraper_data['name']}: Unexpected error: {e}")
                results.append({
                    'scraper_id': scraper_data['id'],
                    'name': scraper_data['name'],
                    'success': False,
                    'error': str(e),
                    'events_found': 0,
                    'events_added': 0
                })
        
        # Update statistics
        self._update_run_stats(results, time.time() - start_time)
        
        # Log summary
        successful = sum(1 for r in results if r['success'])
        total_events = sum(r['events_added'] for r in results)
        
        logger.info(f"📊 Scrape run complete: {successful}/{len(results)} successful, {total_events} events added")
    
    def _scrape_single_source(self, scraper_data):
        """Scrape a single source with enhanced error handling"""
        scraper_id = scraper_data['id']
        name = scraper_data['name']
        url = scraper_data['url']
        selector_config = scraper_data['selector_config']
        
        result = {
            'scraper_id': scraper_id,
            'name': name,
            'success': False,
            'error': None,
            'events_found': 0,
            'events_added': 0,
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            # Scrape events with timeout
            events = self.scraper.scrape_events(url, selector_config)
            result['events_found'] = len(events)
            
            if events:
                # Filter high-confidence events
                good_events = [e for e in events if e.get('confidence_score', 0) >= 60]
                
                # Add events to database
                events_added = self._add_events_to_db(scraper_id, good_events, url)
                result['events_added'] = events_added
                result['success'] = True
                
                # Update scraper stats
                self._update_scraper_stats(scraper_id, True, events_added)
                
            else:
                # No events found - still successful but no results
                result['success'] = True
                self._update_scraper_stats(scraper_id, True, 0)
                
        except Exception as e:
            result['error'] = str(e)
            result['success'] = False
            
            # Update failure count
            self._update_scraper_stats(scraper_id, False, 0)
            
        finally:
            result['execution_time'] = time.time() - start_time
        
        return result
    
    def _get_active_scrapers(self):
        """Get all active scrapers from database"""
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, url, selector_config 
            FROM web_scrapers 
            WHERE is_active = 1
            ORDER BY name
        ''')
        
        scrapers = []
        for row in cursor.fetchall():
            scrapers.append({
                'id': row[0],
                'name': row[1],
                'url': row[2],
                'selector_config': json.loads(row[3]) if row[3] else {}
            })
        
        conn.close()
        return scrapers
    
    def _add_events_to_db(self, scraper_id, events, source_url):
        """Add validated events to database"""
        if not events:
            return 0
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        events_added = 0
        
        for event in events:
            try:
                title = event.get('title', '').strip()
                description = event.get('description', '').strip()[:2000]  # Limit length
                start_date = event.get('start_date', '').strip()
                location = event.get('location', '').strip()
                price = event.get('price_info', '').strip()
                event_url = event.get('url', source_url)
                
                if not title or len(title) < 3:
                    continue
                
                # Handle date validation more leniently
                if not start_date:
                    start_date = datetime.now().isoformat()
                else:
                    # Try to parse the date, but don't fail if it's malformed
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(start_date, fuzzy=True)
                        start_date = parsed_date.isoformat()
                    except:
                        # If date parsing fails, use tomorrow as a safe default
                        from datetime import timedelta
                        start_date = (datetime.now() + timedelta(days=1)).isoformat()
                
                # Check for duplicates (title + approximate date)
                cursor.execute('''
                    SELECT id FROM events 
                    WHERE title = ? AND (
                        start_datetime = ? OR 
                        start_datetime LIKE ? OR
                        (start_datetime LIKE ? AND source = 'scraper')
                    )
                ''', (title, start_date, f'%{start_date[:10]}%', f'%{title[:20]}%'))
                
                if not cursor.fetchone():
                    # Add new event to approval queue
                    cursor.execute('''
                        INSERT INTO events (
                            title, description, start_datetime, location_name, 
                            price_info, url, source, approval_status, created_at, category_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        title, description, start_date, location, price, 
                        event_url, 'scraper', 'pending', datetime.now().isoformat(), 1
                    ))
                    events_added += 1
                    
            except Exception as e:
                logger.error(f"Error adding event '{title}': {e}")
                continue
        
        conn.commit()
        conn.close()
        return events_added
    
    def _update_scraper_stats(self, scraper_id, success, events_added):
        """Update scraper statistics"""
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        if success:
            cursor.execute('''
                UPDATE web_scrapers 
                SET last_run = CURRENT_TIMESTAMP,
                    total_events = total_events + ?,
                    consecutive_failures = 0
                WHERE id = ?
            ''', (events_added, scraper_id))
        else:
            cursor.execute('''
                UPDATE web_scrapers 
                SET last_run = CURRENT_TIMESTAMP,
                    consecutive_failures = consecutive_failures + 1
                WHERE id = ?
            ''', (scraper_id,))
        
        conn.commit()
        conn.close()
    
    def _update_run_stats(self, results, execution_time):
        """Update overall run statistics"""
        self.stats['total_runs'] += 1
        self.stats['successful_runs'] += sum(1 for r in results if r['success'])
        self.stats['total_events_found'] += sum(r['events_found'] for r in results)
        self.stats['total_events_added'] += sum(r['events_added'] for r in results)
        self.stats['last_run'] = datetime.now().isoformat()
        self.stats['last_execution_time'] = execution_time
    
    def _report_health_stats(self):
        """Report hourly health statistics"""
        success_rate = (self.stats['successful_runs'] / self.stats['total_runs'] * 100) if self.stats['total_runs'] > 0 else 0
        
        logger.info("📊 HOURLY HEALTH REPORT")
        logger.info(f"   Total runs: {self.stats['total_runs']}")
        logger.info(f"   Success rate: {success_rate:.1f}%")
        logger.info(f"   Events found: {self.stats['total_events_found']}")
        logger.info(f"   Events added: {self.stats['total_events_added']}")
        logger.info(f"   Last run: {self.stats.get('last_run', 'Never')}")
    
    def _cleanup_old_data(self):
        """Daily cleanup of old data"""
        logger.info("🧹 Running daily cleanup...")
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        # Remove old rejected events (older than 30 days)
        cursor.execute('''
            DELETE FROM events 
            WHERE approval_status = 'rejected' 
            AND created_at < datetime('now', '-30 days')
        ''')
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        logger.info(f"🗑️ Cleaned up {deleted_count} old rejected events")
    
    def get_status(self):
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'stats': self.stats
        }

# Global scheduler instance
_scheduler = None

def start_background_scheduler():
    """Start the background scheduler"""
    global _scheduler
    
    if _scheduler and _scheduler.is_running:
        logger.info("Scheduler already running")
        return _scheduler
    
    _scheduler = ProductionScraperScheduler()
    _scheduler.start_scheduler()
    return _scheduler

def stop_background_scheduler():
    """Stop the background scheduler"""
    global _scheduler
    
    if _scheduler:
        _scheduler.stop_scheduler()
        _scheduler = None

def get_scheduler_status():
    """Get scheduler status"""
    global _scheduler
    
    if _scheduler:
        return _scheduler.get_status()
    else:
        return {'is_running': False, 'stats': {}}

if __name__ == "__main__":
    # Run scheduler directly
    scheduler = ProductionScraperScheduler()
    scheduler.start_scheduler()
    
    try:
        # Keep running
        while True:
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        scheduler.stop_scheduler()
        logger.info("Scheduler stopped")
