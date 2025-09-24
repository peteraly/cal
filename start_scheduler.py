#!/usr/bin/env python3
"""
Start the background scheduler to scrape all sources every 10 minutes
Run this script to begin automated event collection
"""

import time
import signal
import sys
from scraper_scheduler import ProductionScraperScheduler

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\n🛑 Stopping scheduler...')
    if scheduler:
        scheduler.stop_scheduler()
    print('✅ Scheduler stopped')
    sys.exit(0)

if __name__ == "__main__":
    print("🚀 STARTING AUTOMATED EVENT SCRAPER")
    print("=" * 50)
    print("📊 Schedule: Every 10 minutes")
    print("🎯 Target: All active web scrapers")
    print("🔗 Monitor at: http://localhost:5001/admin/web-scrapers")
    print("📋 Review events at: http://localhost:5001/admin/approval")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create and start scheduler
    scheduler = ProductionScraperScheduler()
    scheduler.start_scheduler()
    
    try:
        # Keep the script running
        while True:
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        signal_handler(None, None)
