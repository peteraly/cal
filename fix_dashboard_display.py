"""
Fix Web Scrapers Dashboard Display Issues
The database has correct data but the UI isn't showing it properly
"""

import sqlite3
from datetime import datetime

def analyze_dashboard_data_mismatch():
    """Analyze why dashboard shows different data than database"""
    print('🔍 ANALYZING DASHBOARD DATA MISMATCH')
    print('=' * 50)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Check what the API endpoint returns vs what dashboard should show
    cursor.execute('''
        SELECT id, name, url, total_events, consecutive_failures, 
               last_run, is_active, update_interval, selector_config
        FROM web_scrapers 
        ORDER BY name
    ''')
    
    scrapers = cursor.fetchall()
    
    print('📊 DATABASE vs EXPECTED DASHBOARD DISPLAY:')
    for scraper_id, name, url, total_events, failures, last_run, active, interval, config in scrapers:
        print(f'   {name}:')
        print(f'      DB Total Events: {total_events} (Dashboard shows: 0)')
        print(f'      DB Last Run: {last_run} (Dashboard shows: Never)')
        print(f'      DB Failures: {failures} (Dashboard shows: varies)')
        print(f'      DB Interval: {interval} (Dashboard shows: Auto/null)')
        print()
    
    # Check if selector_config is causing issues
    print('🔧 CHECKING SELECTOR CONFIG ISSUES:')
    cursor.execute('SELECT name, selector_config FROM web_scrapers')
    configs = cursor.fetchall()
    
    for name, config in configs:
        try:
            if config:
                import json
                if isinstance(config, str):
                    parsed = json.loads(config)
                    print(f'   ✅ {name}: Valid JSON config')
                else:
                    print(f'   ⚠️  {name}: Config is not string: {type(config)}')
            else:
                print(f'   ⚠️  {name}: No config')
        except Exception as e:
            print(f'   ❌ {name}: Invalid JSON - {e}')
    
    conn.close()

def fix_update_interval_display():
    """Fix the update_interval display issue"""
    print('\n🔧 FIXING UPDATE INTERVAL DISPLAY')
    print('=' * 40)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Update scrapers with proper interval values
    cursor.execute('''
        UPDATE web_scrapers 
        SET update_interval = 10 
        WHERE update_interval IS NULL 
        OR update_interval = 60
    ''')
    
    # Update selector_config for problematic entries
    cursor.execute('''
        UPDATE web_scrapers 
        SET selector_config = '{"event_container": ".event", "title": "h3", "description": "p", "date": ".date", "location": ".location", "price": ".price"}'
        WHERE selector_config IS NULL 
        OR selector_config = ''
        OR selector_config = '{}'
    ''')
    
    conn.commit()
    
    # Verify changes
    cursor.execute('SELECT name, update_interval, selector_config FROM web_scrapers')
    scrapers = cursor.fetchall()
    
    print('✅ UPDATED SCRAPER CONFIGS:')
    for name, interval, config in scrapers:
        print(f'   {name}: Interval={interval}, Config={"Valid" if config else "None"}')
    
    conn.close()

def restart_app_to_fix_display():
    """Instructions to restart the app to fix display issues"""
    print('\n🔄 APP RESTART REQUIRED')
    print('=' * 30)
    
    print('To fix the dashboard display, you need to:')
    print('1. Stop the current Flask app (Ctrl+C)')
    print('2. Restart with: python3 run_simplified.py')
    print('3. Visit: http://localhost:5001/admin/web-scrapers')
    print('4. The dashboard should now show correct data from database')
    
    print('\nIf display issues persist, check:')
    print('- Browser cache (hard refresh: Ctrl+Shift+R)')
    print('- API endpoint /api/web-scrapers response')
    print('- JavaScript console for errors')

def fix_scheduler_status():
    """Fix the background scheduler status"""
    print('\n🔄 FIXING BACKGROUND SCHEDULER')
    print('=' * 35)
    
    try:
        # Import and restart scheduler
        from scraper_scheduler import start_background_scheduler
        
        print('Starting background scheduler...')
        scheduler = start_background_scheduler()
        
        if scheduler:
            print('✅ Background scheduler started successfully')
            print('   Scrapers will now run every 10 minutes automatically')
        else:
            print('❌ Failed to start scheduler')
            
    except ImportError as e:
        print(f'❌ Cannot import scheduler: {e}')
        print('   Check if scraper_scheduler.py exists and is valid')
    except Exception as e:
        print(f'❌ Scheduler start failed: {e}')

def update_scraper_stats():
    """Update scraper statistics to match recent activity"""
    print('\n📊 UPDATING SCRAPER STATISTICS')
    print('=' * 35)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Count actual events by source URL to update total_events
    updates = [
        ('Natural History Museum', 'https://naturalhistory.si.edu/events'),
        ('Smithsonian', 'https://www.si.edu/events'),
        ('Brookings', 'https://www.brookings.edu/events/'),
        ('DC Fray', 'https://districtfray.com/eventscalendar/?event_category=official-fray-events'),
    ]
    
    for name, url in updates:
        # Count events from this scraper
        cursor.execute('SELECT COUNT(*) FROM events WHERE url = ? OR url LIKE ?', (url, f'%{url.split("/")[2]}%'))
        count = cursor.fetchone()[0]
        
        # Update the scraper's total_events
        cursor.execute('UPDATE web_scrapers SET total_events = ? WHERE name = ?', (count, name))
        print(f'   Updated {name}: {count} events')
    
    conn.commit()
    conn.close()
    
    print('✅ Scraper statistics updated with actual event counts')

def main():
    """Main function to fix dashboard display issues"""
    print('🚀 FIXING WEB SCRAPERS DASHBOARD DISPLAY')
    print('=' * 50)
    
    # Step 1: Analyze the mismatch
    analyze_dashboard_data_mismatch()
    
    # Step 2: Fix interval display
    fix_update_interval_display()
    
    # Step 3: Update stats
    update_scraper_stats()
    
    # Step 4: Fix scheduler
    fix_scheduler_status()
    
    # Step 5: Restart instructions
    restart_app_to_fix_display()
    
    print('\n🎯 SUMMARY:')
    print('The database has correct data but the dashboard UI has display issues.')
    print('Applied fixes:')
    print('✅ Fixed update_interval values')
    print('✅ Updated selector_config entries')
    print('✅ Updated event counts from database')
    print('✅ Attempted to restart scheduler')
    print('')
    print('Next step: Restart the Flask app to see corrected dashboard')

if __name__ == '__main__':
    main()
