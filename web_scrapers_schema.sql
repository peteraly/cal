-- Web Scrapers Database Schema
-- This schema supports web scraping management with scheduling and history tracking

-- Web scrapers table
CREATE TABLE IF NOT EXISTS web_scrapers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT DEFAULT 'events',
    selector_config TEXT, -- JSON config for CSS selectors
    update_interval INTEGER DEFAULT 60, -- minutes
    is_active BOOLEAN DEFAULT 1,
    last_run DATETIME,
    next_run DATETIME,
    consecutive_failures INTEGER DEFAULT 0,
    total_events INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Web scraper logs table
CREATE TABLE IF NOT EXISTS web_scraper_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_id INTEGER,
    run_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT, -- 'success', 'error', 'warning'
    events_found INTEGER DEFAULT 0,
    events_added INTEGER DEFAULT 0,
    events_updated INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    error_message TEXT,
    FOREIGN KEY (scraper_id) REFERENCES web_scrapers (id)
);

-- Web scraper events table (for tracking scraped events)
CREATE TABLE IF NOT EXISTS web_scraper_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_id INTEGER,
    event_id INTEGER, -- Links to main events table
    source_url TEXT,
    source_selector TEXT, -- Which selector found this event
    scraped_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1, -- False if event no longer found on source
    FOREIGN KEY (scraper_id) REFERENCES web_scrapers (id),
    FOREIGN KEY (event_id) REFERENCES events (id)
);

-- Web scraper categories table
CREATE TABLE IF NOT EXISTS web_scraper_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    color TEXT DEFAULT '#3B82F6'
);

-- Insert default categories
INSERT OR IGNORE INTO web_scraper_categories (name, description, color) VALUES
('events', 'General Events', '#3B82F6'),
('sports', 'Sports Events', '#10B981'),
('concerts', 'Concerts & Music', '#8B5CF6'),
('food', 'Food & Dining', '#F59E0B'),
('arts', 'Arts & Culture', '#EF4444'),
('business', 'Business Events', '#6B7280');

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_web_scrapers_active ON web_scrapers(is_active);
CREATE INDEX IF NOT EXISTS idx_web_scrapers_next_run ON web_scrapers(next_run);
CREATE INDEX IF NOT EXISTS idx_web_scraper_logs_scraper_id ON web_scraper_logs(scraper_id);
CREATE INDEX IF NOT EXISTS idx_web_scraper_logs_run_time ON web_scraper_logs(run_time);
CREATE INDEX IF NOT EXISTS idx_web_scraper_events_scraper_id ON web_scraper_events(scraper_id);
CREATE INDEX IF NOT EXISTS idx_web_scraper_events_event_id ON web_scraper_events(event_id);
CREATE INDEX IF NOT EXISTS idx_web_scraper_events_active ON web_scraper_events(is_active);
