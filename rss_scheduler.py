#!/usr/bin/env python3
"""
RSS Feed Scheduler
Background service to automatically update RSS feeds at configured intervals
"""

import time
import schedule
import threading
from datetime import datetime
from rss_manager import RSSManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rss_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RSSScheduler:
    def __init__(self, db_path: str = 'calendar.db'):
        self.rss_manager = RSSManager(db_path)
        self.running = False
        self.thread = None
    
    def process_feeds_job(self):
        """Job to process all active RSS feeds"""
        logger.info("Starting scheduled RSS feed processing...")
        
        try:
            results = self.rss_manager.process_all_feeds()
            logger.info(f"RSS processing completed: {results}")
        except Exception as e:
            logger.error(f"Error in scheduled RSS processing: {str(e)}")
    
    def start_scheduler(self):
        """Start the RSS feed scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        # Schedule the job to run every 15 minutes
        schedule.every(15).minutes.do(self.process_feeds_job)
        
        # Also run immediately on startup
        self.process_feeds_job()
        
        logger.info("RSS Scheduler started - checking feeds every 15 minutes")
        
        # Run scheduler in a separate thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
    
    def stop_scheduler(self):
        """Stop the RSS feed scheduler"""
        self.running = False
        schedule.clear()
        logger.info("RSS Scheduler stopped")
    
    def _run_scheduler(self):
        """Internal method to run the scheduler loop"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying
    
    def get_status(self):
        """Get scheduler status"""
        return {
            'running': self.running,
            'next_run': str(schedule.next_run()) if schedule.jobs else None,
            'jobs_count': len(schedule.jobs)
        }

# Global scheduler instance
scheduler = RSSScheduler()

def start_rss_scheduler():
    """Start the RSS scheduler (called from Flask app)"""
    scheduler.start_scheduler()

def stop_rss_scheduler():
    """Stop the RSS scheduler"""
    scheduler.stop_scheduler()

def get_scheduler_status():
    """Get scheduler status"""
    return scheduler.get_status()

if __name__ == "__main__":
    # Run scheduler standalone
    scheduler = RSSScheduler()
    
    try:
        scheduler.start_scheduler()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down RSS scheduler...")
        scheduler.stop_scheduler()

