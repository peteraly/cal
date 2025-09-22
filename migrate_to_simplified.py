#!/usr/bin/env python3
"""
Migration script to simplify the calendar database schema
This script safely migrates from the complex 15+ table schema to a simplified 3-table schema
"""

import sqlite3
import json
import shutil
from datetime import datetime

def backup_database(db_path):
    """Create a backup of the current database"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"✅ Database backed up to: {backup_path}")
    return backup_path

def migrate_to_simplified(db_path):
    """Migrate the database to simplified schema"""
    
    # Create backup first
    backup_path = backup_database(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Starting database migration...")
        
        # Step 1: Create new simplified tables
        print("📋 Creating simplified schema...")
        
        # Categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL
            )
        ''')
        
        # Events table (consolidated)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                start_datetime TEXT NOT NULL,
                end_datetime TEXT,
                description TEXT,
                location TEXT,
                location_name TEXT,
                address TEXT,
                price_info TEXT,
                url TEXT,
                tags TEXT,
                category_id INTEGER,
                source TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories_new (id)
            )
        ''')
        
        # RSS feeds table (simplified)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rss_feeds_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                description TEXT,
                enabled BOOLEAN DEFAULT 1,
                last_checked TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Step 2: Migrate categories
        print("📂 Migrating categories...")
        cursor.execute('SELECT * FROM categories')
        categories = cursor.fetchall()
        
        for cat in categories:
            cursor.execute('''
                INSERT OR IGNORE INTO categories_new (id, name, color)
                VALUES (?, ?, ?)
            ''', cat)
        
        # Step 3: Migrate events (consolidate from multiple sources)
        print("📅 Migrating events...")
        
        # Get events from main events table
        cursor.execute('SELECT * FROM events')
        events = cursor.fetchall()
        
        for event in events:
            # Extract event data (adjust indices based on your current schema)
            event_id = event[0]
            title = event[1]
            start_datetime = event[2]
            end_datetime = event[3] if len(event) > 3 else None
            description = event[4] if len(event) > 4 else None
            location = event[5] if len(event) > 5 else None
            location_name = event[6] if len(event) > 6 else None
            address = event[7] if len(event) > 7 else None
            category_id = event[8] if len(event) > 8 else None
            tags = event[9] if len(event) > 9 else None
            price_info = event[10] if len(event) > 10 else None
            url = event[11] if len(event) > 11 else None
            
            cursor.execute('''
                INSERT INTO events_new (
                    id, title, start_datetime, end_datetime, description,
                    location, location_name, address, price_info, url,
                    tags, category_id, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'manual', CURRENT_TIMESTAMP)
            ''', (event_id, title, start_datetime, end_datetime, description,
                  location, location_name, address, price_info, url,
                  tags, category_id))
        
        # Step 4: Migrate RSS feeds (if they exist)
        print("📡 Migrating RSS feeds...")
        try:
            cursor.execute('SELECT * FROM rss_feeds')
            rss_feeds = cursor.fetchall()
            
            for feed in rss_feeds:
                cursor.execute('''
                    INSERT INTO rss_feeds_new (id, name, url, description, enabled, last_checked, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', feed)
        except sqlite3.OperationalError:
            print("ℹ️  No RSS feeds table found, skipping...")
        
        # Step 5: Replace old tables with new ones
        print("🔄 Replacing old tables...")
        
        # Drop old tables
        old_tables = [
            'categories', 'events', 'rss_feeds',
            'monitored_urls', 'scraper_logs', 'scraped_events',
            'web_scrapers', 'web_scraper_logs', 'web_scraper_events',
            'web_scraper_categories', 'rss_feed_logs', 'event_sources',
            'manual_overrides', 'sync_logs', 'sync_conflicts'
        ]
        
        for table in old_tables:
            try:
                cursor.execute(f'DROP TABLE IF EXISTS {table}')
            except sqlite3.OperationalError:
                pass  # Table doesn't exist
        
        # Rename new tables
        cursor.execute('ALTER TABLE categories_new RENAME TO categories')
        cursor.execute('ALTER TABLE events_new RENAME TO events')
        cursor.execute('ALTER TABLE rss_feeds_new RENAME TO rss_feeds')
        
        # Step 6: Create indexes for performance
        print("⚡ Creating indexes...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_start_datetime ON events(start_datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_category_id ON events(category_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)')
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        
        # Show migration summary
        cursor.execute('SELECT COUNT(*) FROM events')
        event_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM categories')
        category_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM rss_feeds')
        rss_count = cursor.fetchone()[0]
        
        print(f"\n📊 Migration Summary:")
        print(f"   Events: {event_count}")
        print(f"   Categories: {category_count}")
        print(f"   RSS Feeds: {rss_count}")
        print(f"   Backup: {backup_path}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(f"🔄 Restoring from backup: {backup_path}")
        shutil.copy2(backup_path, db_path)
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    db_path = "calendar.db"
    migrate_to_simplified(db_path)
