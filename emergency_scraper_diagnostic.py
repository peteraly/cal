"""
Emergency Web Scraper Diagnostic Script
Identifies and reports critical issues with the scraper system
"""

import sqlite3
import json
from datetime import datetime, timedelta
import traceback

def check_database_consistency():
    """Check for inconsistencies between database and dashboard"""
    print('🔍 CHECKING DATABASE CONSISTENCY')
    print('=' * 50)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get scraper stats from database
    cursor.execute('''
        SELECT name, url, total_events, consecutive_failures, 
               last_run, is_active, update_interval
        FROM web_scrapers 
        ORDER BY consecutive_failures DESC
    ''')
    
    scrapers = cursor.fetchall()
    
    print('📊 CURRENT SCRAPER STATUS:')
    working_count = 0
    failing_count = 0
    never_run_count = 0
    
    for name, url, total_events, failures, last_run, active, interval in scrapers:
        status = '🟢' if failures < 10 else '🟡' if failures < 50 else '🔴'
        
        if failures >= 50:
            failing_count += 1
        elif last_run is None:
            never_run_count += 1
        else:
            working_count += 1
        
        print(f'   {status} {name}')
        print(f'      Events: {total_events or 0}, Failures: {failures}')
        print(f'      Last run: {last_run or "Never"}')
        print(f'      Active: {active}, Interval: {interval}')
        print()
    
    # Calculate real health score
    total_scrapers = len(scrapers)
    real_health = ((working_count / total_scrapers) * 100) if total_scrapers > 0 else 0
    
    print(f'📈 REAL HEALTH ANALYSIS:')
    print(f'   Total scrapers: {total_scrapers}')
    print(f'   Working (< 10 failures): {working_count}')
    print(f'   Struggling (10-50 failures): {failing_count}')
    print(f'   Broken (50+ failures): {failing_count}')
    print(f'   Never run: {never_run_count}')
    print(f'   Real health score: {real_health:.1f}% (dashboard shows 100%)')
    
    conn.close()
    return {
        'total_scrapers': total_scrapers,
        'working_count': working_count,
        'failing_count': failing_count,
        'never_run_count': never_run_count,
        'real_health': real_health
    }

def test_scheduler_status():
    """Test if the background scheduler is actually running"""
    print('\n🔄 TESTING BACKGROUND SCHEDULER')
    print('=' * 50)
    
    try:
        # Try to import scheduler functions
        from scraper_scheduler import get_scheduler_status
        status = get_scheduler_status()
        
        print(f'✅ Scheduler module imported successfully')
        print(f'   Running: {status.get("running", False)}')
        print(f'   Jobs: {len(status.get("jobs", []))}')
        print(f'   Last run: {status.get("last_run", "Never")}')
        
        return True
    except ImportError as e:
        print(f'❌ Scheduler import failed: {e}')
        return False
    except Exception as e:
        print(f'❌ Scheduler error: {e}')
        return False

def test_individual_scrapers():
    """Test each scraper individually to see what's working"""
    print('\n🕷️ TESTING INDIVIDUAL SCRAPERS')
    print('=' * 50)
    
    try:
        from enhanced_scraper import EnhancedWebScraper
        scraper = EnhancedWebScraper()
        
        conn = sqlite3.connect('calendar.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, url FROM web_scrapers WHERE is_active = 1 LIMIT 5')
        test_scrapers = cursor.fetchall()
        
        results = []
        
        for name, url in test_scrapers:
            print(f'   Testing: {name}')
            print(f'   URL: {url}')
            
            try:
                events = scraper.scrape_events(url)
                event_count = len(events)
                
                if event_count > 0:
                    print(f'   ✅ SUCCESS: Found {event_count} events')
                    results.append({'name': name, 'status': 'working', 'events': event_count})
                else:
                    print(f'   ⚠️  NO EVENTS: Scraper ran but found 0 events')
                    results.append({'name': name, 'status': 'empty', 'events': 0})
                    
            except Exception as e:
                print(f'   ❌ FAILED: {str(e)[:100]}...')
                results.append({'name': name, 'status': 'failed', 'error': str(e)})
            
            print()
        
        conn.close()
        return results
        
    except ImportError as e:
        print(f'❌ Enhanced scraper import failed: {e}')
        return []
    except Exception as e:
        print(f'❌ Scraper testing failed: {e}')
        return []

def check_recent_events():
    """Check if any events were actually added recently"""
    print('\n📅 CHECKING RECENT EVENT ADDITIONS')
    print('=' * 50)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Check events added in last 24 hours
    cursor.execute('''
        SELECT source, COUNT(*) as count, MAX(created_at) as latest
        FROM events 
        WHERE created_at > datetime('now', '-24 hours')
        AND source = 'scraper'
        GROUP BY source
    ''')
    
    recent_events = cursor.fetchall()
    
    if recent_events:
        print('✅ RECENT SCRAPER EVENTS FOUND:')
        for source, count, latest in recent_events:
            print(f'   {source}: {count} events (latest: {latest})')
    else:
        print('❌ NO RECENT SCRAPER EVENTS')
        print('   No events added by scrapers in last 24 hours')
        
        # Check if any events exist from scrapers at all
        cursor.execute('SELECT COUNT(*) FROM events WHERE source = "scraper"')
        total_scraper_events = cursor.fetchone()[0]
        print(f'   Total scraper events ever: {total_scraper_events}')
    
    conn.close()
    return len(recent_events) > 0

def generate_fix_recommendations(db_stats, scheduler_working, scraper_results, recent_events):
    """Generate specific recommendations based on diagnostic results"""
    print('\n🎯 DIAGNOSTIC SUMMARY & RECOMMENDATIONS')
    print('=' * 60)
    
    recommendations = []
    
    # Health score issue
    if db_stats['real_health'] < 50:
        recommendations.append({
            'priority': 'CRITICAL',
            'issue': f'Real health is {db_stats["real_health"]:.1f}% not 100%',
            'action': 'Fix health score calculation in dashboard'
        })
    
    # Scheduler issues
    if not scheduler_working:
        recommendations.append({
            'priority': 'CRITICAL', 
            'issue': 'Background scheduler not running',
            'action': 'Restart scraper_scheduler.py process'
        })
    
    # Never run scrapers
    if db_stats['never_run_count'] > 0:
        recommendations.append({
            'priority': 'HIGH',
            'issue': f'{db_stats["never_run_count"]} scrapers never executed',
            'action': 'Check scheduler configuration and start jobs'
        })
    
    # Excessive failures
    if db_stats['failing_count'] > 5:
        recommendations.append({
            'priority': 'HIGH',
            'issue': f'{db_stats["failing_count"]} scrapers have 50+ failures',
            'action': 'Reset failure counts and implement circuit breaker'
        })
    
    # No recent events
    if not recent_events:
        recommendations.append({
            'priority': 'HIGH',
            'issue': 'No events scraped in last 24 hours',
            'action': 'Check network connectivity and scraper logic'
        })
    
    # Working scrapers
    working_scrapers = [r for r in scraper_results if r.get('status') == 'working']
    if len(working_scrapers) < 3:
        recommendations.append({
            'priority': 'MEDIUM',
            'issue': f'Only {len(working_scrapers)} scrapers working',
            'action': 'Fix failing scrapers or add new reliable sources'
        })
    
    # Display recommendations
    for i, rec in enumerate(recommendations, 1):
        priority_emoji = {'CRITICAL': '🚨', 'HIGH': '⚠️', 'MEDIUM': '📝'}.get(rec['priority'], '📝')
        print(f'{i:2d}. {priority_emoji} {rec["priority"]}: {rec["issue"]}')
        print(f'    → {rec["action"]}')
        print()
    
    return recommendations

def main():
    """Run complete diagnostic of scraper system"""
    print('🚨 EMERGENCY WEB SCRAPER DIAGNOSTIC')
    print('=' * 60)
    print(f'Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print()
    
    # Run all diagnostic tests
    db_stats = check_database_consistency()
    scheduler_working = test_scheduler_status()
    scraper_results = test_individual_scrapers()
    recent_events = check_recent_events()
    
    # Generate recommendations
    recommendations = generate_fix_recommendations(
        db_stats, scheduler_working, scraper_results, recent_events
    )
    
    # Summary
    print('🏁 DIAGNOSTIC COMPLETE')
    print('=' * 30)
    print(f'Issues found: {len(recommendations)}')
    print(f'Critical issues: {len([r for r in recommendations if r["priority"] == "CRITICAL"])}')
    print(f'Action required: {"YES" if len(recommendations) > 0 else "NO"}')
    
    if len(recommendations) == 0:
        print('✅ All systems working correctly!')
    else:
        print(f'❌ Multiple issues detected - see recommendations above')
        print(f'   Next step: Run quick_scraper_fix.py to apply emergency fixes')

if __name__ == '__main__':
    main()
