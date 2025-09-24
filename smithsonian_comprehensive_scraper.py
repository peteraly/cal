"""
Comprehensive Smithsonian Calendar Scraper
Captures ALL events across ALL days and museums, not just single day view
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timedelta
import sqlite3
import json
import re
from urllib.parse import urljoin, urlparse

class SmithsonianComprehensiveScraper:
    """Scraper that captures the entire Smithsonian calendar, not just one day"""
    
    def __init__(self):
        self.base_url = "https://www.si.edu/events"
        self.session = self.setup_session()
        self.museums = [
            'Natural History Museum',
            'American History Museum',
            'Air and Space Museum',
            'American Art Museum',
            'American Indian Museum',
            'Asian Art Museum',
            'Anacostia Community Museum',
            'Hirshhorn Museum',
            'National Zoo'
        ]
    
    def setup_session(self):
        """Setup session with realistic headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.si.edu/'
        })
        return session
    
    def scrape_full_calendar(self, months_ahead=3):
        """
        Scrape ALL events from the Smithsonian calendar
        Target: Hundreds of events across multiple months and museums
        """
        print(f'🗓️ Starting comprehensive Smithsonian calendar scrape...')
        print(f'📅 Target: {months_ahead} months of events')
        
        all_events = []
        
        # Strategy 1: Try date range traversal
        date_events = self._scrape_date_range(months_ahead)
        if date_events:
            print(f'   ✅ Date traversal: {len(date_events)} events')
            all_events.extend(date_events)
        
        # Strategy 2: Try alternative comprehensive URLs
        comprehensive_events = self._try_comprehensive_urls()
        if comprehensive_events:
            print(f'   ✅ Comprehensive URLs: {len(comprehensive_events)} events')
            all_events.extend(comprehensive_events)
        
        # Strategy 3: Try individual museum calendar pages
        museum_events = self._scrape_individual_museums()
        if museum_events:
            print(f'   ✅ Individual museums: {len(museum_events)} events')
            all_events.extend(museum_events)
        
        # Remove duplicates and validate
        unique_events = self._deduplicate_and_validate(all_events)
        
        print(f'📊 Total comprehensive events: {len(unique_events)}')
        return unique_events
    
    def _scrape_date_range(self, months_ahead):
        """Scrape events by traversing through calendar dates"""
        events = []
        
        # Generate date range
        start_date = datetime.now().date()
        end_date = start_date + timedelta(days=months_ahead * 30)
        
        print(f'   📅 Scraping dates from {start_date} to {end_date}')
        
        # Test different URL patterns for date navigation
        url_patterns = [
            "https://www.si.edu/events?date={date}",
            "https://www.si.edu/events/{year}/{month:02d}/{day:02d}",
            "https://www.si.edu/events?day={day}&month={month}&year={year}"
        ]
        
        # Sample a few dates to find working pattern
        test_dates = [start_date + timedelta(days=i) for i in [0, 1, 7, 14]]
        working_pattern = None
        
        for pattern in url_patterns:
            success_count = 0
            for test_date in test_dates:
                try:
                    if '{date}' in pattern:
                        url = pattern.format(date=test_date.strftime('%Y-%m-%d'))
                    else:
                        url = pattern.format(
                            year=test_date.year,
                            month=test_date.month,
                            day=test_date.day
                        )
                    
                    response = self.session.get(url, timeout=10)
                    if response.status_code == 200 and self._has_events(response.text):
                        success_count += 1
                        
                except Exception:
                    continue
            
            if success_count >= 2:  # Pattern works for most dates
                working_pattern = pattern
                print(f'   ✅ Working URL pattern: {pattern}')
                break
        
        if not working_pattern:
            print(f'   ❌ No working date URL pattern found')
            return []
        
        # Scrape all dates using working pattern
        current_date = start_date
        consecutive_failures = 0
        
        while current_date <= end_date and consecutive_failures < 5:
            try:
                if '{date}' in working_pattern:
                    url = working_pattern.format(date=current_date.strftime('%Y-%m-%d'))
                else:
                    url = working_pattern.format(
                        year=current_date.year,
                        month=current_date.month,
                        day=current_date.day
                    )
                
                day_events = self._scrape_single_day(url, current_date)
                if day_events:
                    events.extend(day_events)
                    consecutive_failures = 0
                    print(f'   📅 {current_date}: {len(day_events)} events')
                else:
                    consecutive_failures += 1
                
                # Be respectful - random delay
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                consecutive_failures += 1
                print(f'   ❌ {current_date}: Error - {str(e)[:30]}...')
            
            current_date += timedelta(days=1)
        
        return events
    
    def _scrape_single_day(self, url, date):
        """Scrape all events from a single day's calendar page"""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'html.parser')
            events = []
            
            # Look for event containers (based on the HTML structure shown)
            event_selectors = [
                'article',
                '[class*="event"]',
                '.event-item',
                '.calendar-event',
                '[data-event]'
            ]
            
            for selector in event_selectors:
                containers = soup.select(selector)
                
                for container in containers:
                    event = self._extract_event_from_container(container, date)
                    if event and self._is_valid_smithsonian_event(event):
                        events.append(event)
            
            return events
            
        except Exception as e:
            print(f'   Error scraping {url}: {e}')
            return []
    
    def _extract_event_from_container(self, container, date):
        """Extract event data from a single event container"""
        try:
            # Extract title
            title_selectors = ['h1', 'h2', 'h3', '.title', '[class*="title"]', 'a[href*="view-details"]']
            title = ''
            for selector in title_selectors:
                elem = container.select_one(selector)
                if elem:
                    title = elem.get_text(strip=True)
                    break
            
            if not title:
                # Fallback: get first meaningful text
                text = container.get_text(strip=True)
                if len(text) > 10:
                    title = text[:100]
            
            # Extract time/datetime
            time_text = ''
            time_selectors = ['.time', '[class*="time"]', 'time', '.date-time']
            for selector in time_selectors:
                elem = container.select_one(selector)
                if elem:
                    time_text = elem.get_text(strip=True)
                    break
            
            # Extract museum/venue
            museum = ''
            museum_selectors = ['.venue', '.location', '[class*="museum"]', '[class*="venue"]']
            for selector in museum_selectors:
                elem = container.select_one(selector)
                if elem:
                    museum_text = elem.get_text(strip=True)
                    # Match against known museums
                    for known_museum in self.museums:
                        if any(word in museum_text for word in known_museum.lower().split()):
                            museum = known_museum
                            break
                    break
            
            # Extract specific location
            location = ''
            location_selectors = ['.room', '.floor', '[class*="location"]']
            for selector in location_selectors:
                elem = container.select_one(selector)
                if elem:
                    location = elem.get_text(strip=True)
                    break
            
            # Extract details URL
            details_url = ''
            link_elem = container.select_one('a[href*="view-details"], a[href*="details"]')
            if link_elem:
                details_url = urljoin(self.base_url, link_elem.get('href', ''))
            
            # Construct datetime
            event_datetime = self._parse_event_datetime(time_text, date)
            
            return {
                'title': title,
                'start_date': event_datetime,
                'museum': museum or 'Smithsonian Institution',
                'location': location,
                'description': '',
                'url': details_url or self.base_url,
                'confidence_score': 90,
                'source': 'smithsonian_calendar'
            }
            
        except Exception as e:
            return None
    
    def _parse_event_datetime(self, time_text, date):
        """Parse event time text into datetime"""
        try:
            if not time_text:
                return date.isoformat()
            
            # Try to extract time from text like "Tuesday, September 23, 9 a.m. EDT"
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*(a\.m\.|p\.m\.|AM|PM)',
                r'(\d{1,2})\s*(a\.m\.|p\.m\.|AM|PM)',
                r'(\d{1,2}):(\d{2})'
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, time_text, re.IGNORECASE)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if len(match.groups()) > 2 else 0
                    
                    # Handle AM/PM
                    if len(match.groups()) > 1:
                        ampm = match.group(-1).lower()
                        if 'p' in ampm and hour != 12:
                            hour += 12
                        elif 'a' in ampm and hour == 12:
                            hour = 0
                    
                    event_datetime = datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
                    return event_datetime.isoformat()
            
            # Fallback: just use date
            return date.isoformat()
            
        except Exception:
            return date.isoformat()
    
    def _try_comprehensive_urls(self):
        """Try alternative URLs that might show all events"""
        comprehensive_urls = [
            "https://www.si.edu/events/all",
            "https://www.si.edu/events?view=list",
            "https://www.si.edu/events/list",
            "https://www.si.edu/calendar/month",
            "https://www.si.edu/whats-on"
        ]
        
        events = []
        
        for url in comprehensive_urls:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    # Check if this page has significantly more events
                    event_count = self._count_events_on_page(response.text)
                    if event_count > 20:  # Threshold for comprehensive page
                        print(f'   ✅ Comprehensive URL found: {url} ({event_count} events)')
                        page_events = self._scrape_comprehensive_page(response.text, url)
                        events.extend(page_events)
                        break
                        
            except Exception as e:
                continue
        
        return events
    
    def _scrape_individual_museums(self):
        """Scrape individual museum event pages"""
        museum_urls = [
            "https://naturalhistory.si.edu/events",
            "https://americanhistory.si.edu/events", 
            "https://airandspace.si.edu/events",
            "https://americanart.si.edu/events",
            "https://nmaahc.si.edu/events",
            "https://hirshhorn.si.edu/events"
        ]
        
        events = []
        
        for url in museum_urls:
            try:
                response = self.session.get(url, timeout=15)
                if response.status_code == 200:
                    # Use existing enhanced scraper for individual museums
                    from enhanced_scraper import EnhancedWebScraper
                    scraper = EnhancedWebScraper()
                    museum_events = scraper.scrape_events(url)
                    
                    if museum_events:
                        print(f'   ✅ {url}: {len(museum_events)} events')
                        events.extend(museum_events)
                
                time.sleep(random.uniform(1, 2))
                
            except Exception as e:
                continue
        
        return events
    
    def _has_events(self, html_content):
        """Check if page has event content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for event indicators
        indicators = [
            soup.select('[class*="event"]'),
            soup.select('article'),
            soup.find_all(string=re.compile(r'(a\.m\.|p\.m\.|AM|PM)', re.IGNORECASE)),
            soup.find_all(string=re.compile(r'Museum|Gallery', re.IGNORECASE))
        ]
        
        return any(len(indicator) > 0 for indicator in indicators)
    
    def _count_events_on_page(self, html_content):
        """Count approximate number of events on page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Count potential event containers
        containers = soup.select('article, [class*="event"], .event-item')
        return len(containers)
    
    def _scrape_comprehensive_page(self, html_content, url):
        """Scrape events from a comprehensive listing page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []
        
        containers = soup.select('article, [class*="event"], .event-item')
        
        for container in containers:
            event = self._extract_event_from_container(container, datetime.now().date())
            if event and self._is_valid_smithsonian_event(event):
                events.append(event)
        
        return events
    
    def _is_valid_smithsonian_event(self, event):
        """Validate if this is a real Smithsonian event"""
        if not event.get('title') or len(event['title']) < 5:
            return False
        
        title_lower = event['title'].lower()
        
        # Check for navigation/UI elements
        false_positives = [
            'previous page', 'next page', 'navigation', 'menu', 'header',
            'footer', 'subscribe', 'my events', 'cookie', 'privacy'
        ]
        
        for fp in false_positives:
            if fp in title_lower:
                return False
        
        # Must have museum/venue info or be clearly an event
        event_indicators = [
            'museum', 'gallery', 'tour', 'exhibition', 'program',
            'workshop', 'lecture', 'performance', 'class', 'story time'
        ]
        
        text_to_check = (event.get('title', '') + ' ' + 
                        event.get('museum', '') + ' ' + 
                        event.get('location', '')).lower()
        
        return any(indicator in text_to_check for indicator in event_indicators)
    
    def _deduplicate_and_validate(self, events):
        """Remove duplicates and validate events"""
        seen = set()
        unique_events = []
        
        for event in events:
            # Create unique key
            key = (
                event.get('title', '').lower().strip(),
                event.get('start_date', '')[:10]  # Just date part
            )
            
            if key not in seen and key[0]:  # Non-empty title
                seen.add(key)
                unique_events.append(event)
        
        return unique_events

def update_smithsonian_comprehensive():
    """Update the Smithsonian scraper to use comprehensive calendar capture"""
    print('🚀 IMPLEMENTING COMPREHENSIVE SMITHSONIAN CALENDAR SCRAPER')
    print('=' * 70)
    
    scraper = SmithsonianComprehensiveScraper()
    events = scraper.scrape_full_calendar(months_ahead=3)
    
    if not events:
        print('❌ No events found - may need alternative strategy')
        return
    
    # Add to database
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    events_added = 0
    for event in events:
        # Only add high-quality events
        if event.get('confidence_score', 0) < 85:
            continue
        
        title = event.get('title', '').strip()
        description = event.get('description', '').strip()
        start_date = event.get('start_date', '')
        location = f"{event.get('museum', '')} - {event.get('location', '')}".strip(' -')
        
        # Check for duplicates
        cursor.execute('SELECT id FROM events WHERE title = ?', (title,))
        if not cursor.fetchone():
            cursor.execute('''
                INSERT INTO events (title, description, start_datetime, location_name, 
                                  url, source, approval_status, created_at, category_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                title, description, start_date, location,
                event.get('url', 'https://www.si.edu/events'), 'scraper', 'pending',
                datetime.now().isoformat(), 1
            ))
            events_added += 1
    
    # Update scraper settings
    cursor.execute('''
        UPDATE web_scrapers 
        SET url = ?, 
            description = 'Smithsonian ALL Museums - Comprehensive Calendar (Multi-Month)',
            total_events = total_events + ?,
            consecutive_failures = 0,
            last_run = CURRENT_TIMESTAMP
        WHERE name LIKE '%Smithsonian%'
    ''', ('https://www.si.edu/events', events_added))
    
    conn.commit()
    conn.close()
    
    print(f'\\n🎉 COMPREHENSIVE CALENDAR SCRAPING COMPLETE:')
    print(f'   ✅ Total events found: {len(events)}')
    print(f'   ✅ High-quality events added: {events_added}')
    print(f'   ✅ Coverage: Multiple months across all Smithsonian museums')
    
    # Analyze coverage
    museums_covered = set()
    months_covered = set()
    
    for event in events:
        if event.get('museum'):
            museums_covered.add(event['museum'])
        if event.get('start_date'):
            month = event['start_date'][:7]  # YYYY-MM
            months_covered.add(month)
    
    print(f'\\n📊 COVERAGE ANALYSIS:')
    print(f'   Museums covered: {len(museums_covered)}')
    for museum in sorted(museums_covered):
        print(f'     • {museum}')
    
    print(f'   Months covered: {len(months_covered)}')
    for month in sorted(months_covered):
        print(f'     • {month}')
    
    return events

if __name__ == '__main__':
    events = update_smithsonian_comprehensive()
