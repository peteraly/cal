#!/usr/bin/env python3
"""
RSS Integration for Approval System
Adds new RSS events to the main events table with pending approval status
"""

import feedparser
import requests
import sqlite3
from datetime import datetime
import re

def clean_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    # Remove HTML tags
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()

def parse_rss_date(date_str):
    """Parse RSS date string to ISO format"""
    try:
        # Parse the date string
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except:
        # Fallback to current time
        return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def add_rss_events_to_approval_queue():
    """Add new RSS events to the approval queue"""
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get RSS feeds
    cursor.execute('SELECT id, name, url FROM rss_feeds WHERE url IS NOT NULL')
    feeds = cursor.fetchall()
    
    total_added = 0
    
    for feed_id, feed_name, feed_url in feeds:
        print(f"Processing RSS feed: {feed_name}")
        
        try:
            # Fetch RSS feed
            response = requests.get(feed_url, timeout=10)
            if response.status_code != 200:
                print(f"  ❌ Failed to fetch: {response.status_code}")
                continue
                
            feed = feedparser.parse(response.content)
            print(f"  📡 Found {len(feed.entries)} entries")
            
            events_added = 0
            
            for entry in feed.entries:
                title = entry.get('title', '').strip()
                link = entry.get('link', '')
                summary = clean_html(entry.get('summary', ''))
                published = entry.get('published', '')
                
                if not title or not link:
                    continue
                
                # Check if event already exists
                cursor.execute('SELECT id FROM events WHERE url = ?', (link,))
                if cursor.fetchone():
                    continue  # Event already exists
                
                # Parse date
                start_datetime = parse_rss_date(published)
                
                # Add event with pending status
                cursor.execute('''
                    INSERT INTO events (
                        title, start_datetime, description, url, source, 
                        approval_status, created_at, category_id, tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    title,
                    start_datetime,
                    summary,
                    link,
                    'rss',
                    'pending',
                    datetime.now().isoformat(),
                    1,  # Default category
                    f'rss,{feed_name.lower().replace(" ", "_")}'
                ))
                
                events_added += 1
                print(f"    ✅ Added: {title[:50]}...")
            
            print(f"  📊 Added {events_added} new events from {feed_name}")
            total_added += events_added
            
        except Exception as e:
            print(f"  ❌ Error processing {feed_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Total new events added to approval queue: {total_added}")
    return total_added

if __name__ == "__main__":
    print("🚀 Starting RSS Integration for Approval System...")
    added = add_rss_events_to_approval_queue()
    
    if added > 0:
        print(f"\n✅ {added} new events added to approval queue!")
        print("📋 Go to http://localhost:5001/admin/approval to review them")
    else:
        print("\n📭 No new events found - all RSS events are already in the database")
