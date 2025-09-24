"""
Simplified database models for the calendar application
"""

import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime

class Database:
    """Simplified database interface"""
    
    def __init__(self, db_path: str = "calendar.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the simplified database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                color TEXT NOT NULL
            )
        ''')
        
        # Create events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
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
                FOREIGN KEY (category_id) REFERENCES categories (id)
            )
        ''')
        
        # Add source column if it doesn't exist
        try:
            cursor.execute('ALTER TABLE events ADD COLUMN source TEXT DEFAULT "manual"')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create RSS feeds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rss_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL UNIQUE,
                description TEXT,
                enabled BOOLEAN DEFAULT 1,
                last_checked TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert default categories
        default_categories = [
            ('Work', '#3B82F6'),
            ('Personal', '#10B981'),
            ('Health', '#F59E0B'),
            ('Travel', '#8B5CF6'),
            ('Social', '#EF4444'),
            ('Other', '#6B7280')
        ]
        
        for name, color in default_categories:
            cursor.execute('INSERT OR IGNORE INTO categories (name, color) VALUES (?, ?)', (name, color))
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_start_datetime ON events(start_datetime)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_category_id ON events(category_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)')
        
        conn.commit()
        conn.close()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

class EventModel:
    """Event model for database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all_events(self, approved_only: bool = True) -> List[Dict]:
        """Get all events with category information"""
        conn = self.db.get_connection()
        
        # Build approval filter
        approval_filter = "WHERE e.approval_status = 'approved'" if approved_only else ""
        
        cursor = conn.execute(f'''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            {approval_filter}
            ORDER BY e.start_datetime
        ''')
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return events
    
    def get_events_by_date(self, date: str, approved_only: bool = True) -> List[Dict]:
        """Get events for a specific date"""
        conn = self.db.get_connection()
        
        # Build approval filter
        approval_filter = "AND e.approval_status = 'approved'" if approved_only else ""
        
        # Try to match the date in various formats
        cursor = conn.execute(f'''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            WHERE (DATE(e.start_datetime) = ? 
               OR e.start_datetime LIKE ?
               OR e.start_datetime LIKE ?)
            {approval_filter}
            ORDER BY e.start_datetime
        ''', (date, f'%{date}%', f'%{date.replace("-", "/")}%'))
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return events
    
    def get_events_by_month(self, month: str, year: str, approved_only: bool = True) -> List[Dict]:
        """Get events for a specific month"""
        conn = self.db.get_connection()
        
        # Build approval filter
        approval_filter = "AND e.approval_status = 'approved'" if approved_only else ""
        
        # Try to match the month/year in various formats
        month_padded = month.zfill(2)
        cursor = conn.execute(f'''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            WHERE ((strftime("%m", e.start_datetime) = ? AND strftime("%Y", e.start_datetime) = ?)
               OR e.start_datetime LIKE ?
               OR e.start_datetime LIKE ?)
            {approval_filter}
            ORDER BY e.start_datetime
        ''', (month_padded, year, f'%{year}-{month_padded}%', f'%{year}/{month_padded}%'))
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return events
    
    def search_events(self, query: str) -> List[Dict]:
        """Search events by title, description, or location"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            WHERE e.title LIKE ? OR e.description LIKE ? OR e.location LIKE ? OR e.location_name LIKE ?
            ORDER BY e.start_datetime
        ''', (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return events
    
    def create_event(self, event_data: Dict) -> int:
        """Create a new event"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            INSERT INTO events (
                title, start_datetime, end_datetime, description,
                location, location_name, address, price_info, url,
                tags, category_id, source, approval_status, event_type, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (
            event_data['title'],
            event_data['start_datetime'],
            event_data.get('end_datetime', ''),
            event_data.get('description', ''),
            event_data.get('location', ''),
            event_data.get('location_name', ''),
            event_data.get('address', ''),
            event_data.get('price_info', ''),
            event_data.get('url', ''),
            event_data.get('tags', ''),
            event_data.get('category_id'),
            event_data.get('source', 'manual'),
            event_data.get('approval_status', 'pending'),
            event_data.get('event_type', 'unknown')
        ))
        event_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return event_id
    
    def update_event(self, event_id: int, event_data: Dict) -> bool:
        """Update an existing event"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            UPDATE events SET 
                title = ?, start_datetime = ?, end_datetime = ?, description = ?,
                location = ?, location_name = ?, address = ?, price_info = ?, url = ?,
                tags = ?, category_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            event_data['title'],
            event_data['start_datetime'],
            event_data.get('end_datetime', ''),
            event_data.get('description', ''),
            event_data.get('location', ''),
            event_data.get('location_name', ''),
            event_data.get('address', ''),
            event_data.get('price_info', ''),
            event_data.get('url', ''),
            event_data.get('tags', ''),
            event_data.get('category_id'),
            event_id
        ))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_event(self, event_id: int) -> bool:
        """Delete an event"""
        conn = self.db.get_connection()
        cursor = conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    # Event Approval Methods
    def get_pending_events(self) -> List[Dict]:
        """Get all events pending approval"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            SELECT e.*, c.name as category_name, c.color as category_color 
            FROM events e 
            LEFT JOIN categories c ON e.category_id = c.id 
            WHERE e.approval_status = 'pending'
            ORDER BY e.created_at DESC
        ''')
        events = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return events
    
    def approve_event(self, event_id: int, admin_user_id: int) -> bool:
        """Approve a specific event"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            UPDATE events 
            SET approval_status = 'approved', 
                approved_by = ?, 
                approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (admin_user_id, event_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def reject_event(self, event_id: int, reason: str, admin_user_id: int) -> bool:
        """Reject a specific event"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            UPDATE events 
            SET approval_status = 'rejected', 
                approved_by = ?, 
                approved_at = CURRENT_TIMESTAMP,
                rejection_reason = ?
            WHERE id = ?
        ''', (admin_user_id, reason, event_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def bulk_delete_events(self, event_ids: List[int]) -> int:
        """Delete multiple events"""
        if not event_ids:
            return 0
        
        conn = self.db.get_connection()
        placeholders = ','.join(['?'] * len(event_ids))
        cursor = conn.execute(f'DELETE FROM events WHERE id IN ({placeholders})', event_ids)
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count

class CategoryModel:
    """Category model for database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all_categories(self) -> List[Dict]:
        """Get all categories"""
        conn = self.db.get_connection()
        cursor = conn.execute('SELECT * FROM categories ORDER BY name')
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return categories
    
    def create_category(self, name: str, color: str) -> int:
        """Create a new category"""
        conn = self.db.get_connection()
        cursor = conn.execute('INSERT INTO categories (name, color) VALUES (?, ?)', (name, color))
        category_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return category_id

class RSSFeedModel:
    """RSS feed model for database operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def get_all_feeds(self) -> List[Dict]:
        """Get all RSS feeds"""
        conn = self.db.get_connection()
        cursor = conn.execute('SELECT * FROM rss_feeds ORDER BY created_at DESC')
        feeds = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return feeds
    
    def create_feed(self, name: str, url: str, description: str = "") -> int:
        """Create a new RSS feed"""
        conn = self.db.get_connection()
        cursor = conn.execute('''
            INSERT INTO rss_feeds (name, url, description, is_active, created_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
        ''', (name, url, description))
        feed_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return feed_id
    
    def delete_feed(self, feed_id: int) -> bool:
        """Delete an RSS feed"""
        conn = self.db.get_connection()
        cursor = conn.execute('DELETE FROM rss_feeds WHERE id = ?', (feed_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_feed_status(self, feed_id: int, enabled: bool) -> bool:
        """Update RSS feed enabled status"""
        conn = self.db.get_connection()
        cursor = conn.execute('UPDATE rss_feeds SET is_active = ? WHERE id = ?', (enabled, feed_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
