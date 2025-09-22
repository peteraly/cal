-- Simplified Calendar Database Schema
-- Reduced from 15+ tables to 3 core tables

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL
);

-- Events table (consolidated from multiple tables)
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
    tags TEXT, -- JSON array of tags
    category_id INTEGER,
    source TEXT DEFAULT 'manual', -- 'manual', 'rss', 'import'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

-- RSS feeds table (simplified)
CREATE TABLE IF NOT EXISTS rss_feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    enabled BOOLEAN DEFAULT 1,
    last_checked TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Insert default categories
INSERT OR IGNORE INTO categories (name, color) VALUES
    ('Work', '#3B82F6'),
    ('Personal', '#10B981'),
    ('Health', '#F59E0B'),
    ('Travel', '#8B5CF6'),
    ('Social', '#EF4444'),
    ('Other', '#6B7280');
