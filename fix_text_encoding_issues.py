"""
Emergency Text Encoding & Data Quality Fix
Cleans up HTML entities, malformed titles, and duplicate events
"""

import sqlite3
import html
import re
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

def clean_event_text(text):
    """Clean and normalize event text"""
    if not text:
        return text
    
    # Step 1: Decode HTML entities
    text = html.unescape(text)
    
    # Step 2: Remove/clean HTML tags
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    
    # Step 3: Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Step 4: Fix specific encoding issues
    replacements = {
        '&#8217;': "'",
        '&#8216;': "'", 
        '&#8220;': '"',
        '&#8221;': '"',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&nbsp;': ' ',
        '&quot;': '"'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text

def validate_event_title(title):
    """Validate if text is a proper event title"""
    if not title or len(title.strip()) < 5:
        return False
    
    title_lower = title.lower().strip()
    
    # Exclude generic/metadata terms
    bad_titles = [
        'event date', 'event type', 'event series', 'events',
        'online only', 'main navigation', 'view details',
        'register now', 'more info', 'event category'
    ]
    
    if title_lower in bad_titles:
        return False
    
    # Check for HTML artifacts
    if '<' in title or '&lt;' in title or '&gt;' in title:
        return False
    
    # Check for obvious location-only titles (without event context)
    location_only_patterns = [
        r'^\d+\w*\s+floor\s*,',  # "1st Floor, ..."
        r'^ground floor\s*,',     # "Ground Floor, ..."
        r'^\w+\s+hall\s*$',      # "Theatre Hall"
        r'^\w+\s+building\s*$'   # "Main Building"
    ]
    
    for pattern in location_only_patterns:
        if re.match(pattern, title_lower):
            return False
    
    return True

def is_similar_title(title1, title2, threshold=0.85):
    """Check if two titles are too similar (potential duplicates)"""
    # Normalize for comparison
    norm1 = re.sub(r'[^\w\s]', '', title1.lower())
    norm2 = re.sub(r'[^\w\s]', '', title2.lower())
    norm1 = re.sub(r'\s+', ' ', norm1).strip()
    norm2 = re.sub(r'\s+', ' ', norm2).strip()
    
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    return similarity >= threshold

def analyze_current_issues():
    """Analyze current text encoding and quality issues"""
    print('🔍 ANALYZING CURRENT TEXT ENCODING ISSUES')
    print('=' * 60)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Check for HTML entity issues
    cursor.execute('''
        SELECT COUNT(*), title 
        FROM events 
        WHERE title LIKE '%&#%' OR title LIKE '%&lt;%' OR title LIKE '%&gt;%'
        GROUP BY title
        ORDER BY COUNT(*) DESC
        LIMIT 10
    ''')
    
    html_issues = cursor.fetchall()
    
    print(f'📊 HTML ENTITY ISSUES FOUND:')
    total_html_issues = 0
    for count, title in html_issues:
        total_html_issues += count
        print(f'   {count:2d}x "{title[:80]}..."')
    
    print(f'   Total events with HTML entities: {total_html_issues}')
    
    # Check for generic titles
    cursor.execute('''
        SELECT COUNT(*) as count, title
        FROM events 
        WHERE title IN ('Event Date', 'Event Type', 'Event Series', 'Events', 'Online Only')
        GROUP BY title
    ''')
    
    generic_issues = cursor.fetchall()
    
    print(f'\n📋 GENERIC TITLE ISSUES:')
    total_generic = 0
    for count, title in generic_issues:
        total_generic += count
        print(f'   {count:2d}x "{title}"')
    
    print(f'   Total generic titles: {total_generic}')
    
    # Check for potential duplicates
    cursor.execute('''
        SELECT title, COUNT(*) as count
        FROM events 
        WHERE approval_status = 'pending'
        GROUP BY title
        HAVING count > 1
        ORDER BY count DESC
        LIMIT 10
    ''')
    
    duplicates = cursor.fetchall()
    
    print(f'\n🔄 EXACT DUPLICATE TITLES:')
    total_duplicate_events = 0
    for title, count in duplicates:
        total_duplicate_events += count - 1  # Count extras
        print(f'   {count:2d}x "{title[:60]}..."')
    
    print(f'   Total duplicate events: {total_duplicate_events}')
    
    conn.close()
    
    return {
        'html_issues': total_html_issues,
        'generic_titles': total_generic,
        'exact_duplicates': total_duplicate_events
    }

def fix_html_entities():
    """Fix HTML entity encoding issues"""
    print('\n🔧 FIXING HTML ENTITY ENCODING')
    print('=' * 40)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Get events with HTML entities
    cursor.execute('''
        SELECT id, title, description 
        FROM events 
        WHERE title LIKE '%&#%' 
        OR title LIKE '%&lt;%'
        OR title LIKE '%&gt;%'
        OR title LIKE '%&amp;%'
        OR description LIKE '%&#%'
        OR description LIKE '%&lt;%'
    ''')
    
    events_to_fix = cursor.fetchall()
    
    fixed_count = 0
    for event_id, title, description in events_to_fix:
        # Clean title and description
        clean_title = clean_event_text(title)
        clean_desc = clean_event_text(description) if description else description
        
        # Validate cleaned title
        if not validate_event_title(clean_title):
            print(f'   ⚠️  Skipping invalid title: "{clean_title}"')
            continue
        
        # Update event
        cursor.execute('''
            UPDATE events 
            SET title = ?, description = ? 
            WHERE id = ?
        ''', (clean_title, clean_desc, event_id))
        
        if title != clean_title:
            print(f'   ✅ Fixed: "{title}" → "{clean_title}"')
            fixed_count += 1
    
    conn.commit()
    conn.close()
    
    print(f'   Total HTML entities fixed: {fixed_count}')
    return fixed_count

def remove_bad_titles():
    """Remove events with obviously bad titles"""
    print('\n🗑️  REMOVING BAD TITLES')
    print('=' * 30)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Delete events with generic/metadata titles
    bad_titles = [
        'Event Date', 'Event Type', 'Event Series', 'Events', 
        'Online Only', 'main navigation', 'Event Category'
    ]
    
    deleted_count = 0
    for bad_title in bad_titles:
        cursor.execute('SELECT COUNT(*) FROM events WHERE title = ?', (bad_title,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute('DELETE FROM events WHERE title = ?', (bad_title,))
            print(f'   🗑️  Deleted {count} events with title: "{bad_title}"')
            deleted_count += count
    
    # Delete events with truncated titles ending in "..."
    cursor.execute('SELECT COUNT(*) FROM events WHERE title LIKE "%..." AND LENGTH(title) < 80')
    truncated_count = cursor.fetchone()[0]
    
    if truncated_count > 0:
        cursor.execute('DELETE FROM events WHERE title LIKE "%..." AND LENGTH(title) < 80')
        print(f'   ✂️  Deleted {truncated_count} truncated events')
        deleted_count += truncated_count
    
    conn.commit()
    conn.close()
    
    print(f'   Total bad events deleted: {deleted_count}')
    return deleted_count

def remove_exact_duplicates():
    """Remove exact duplicate events"""
    print('\n🔄 REMOVING EXACT DUPLICATES')
    print('=' * 35)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Find groups of exact duplicate titles
    cursor.execute('''
        SELECT title, COUNT(*) as count, MIN(id) as keep_id
        FROM events 
        WHERE approval_status = 'pending'
        GROUP BY title
        HAVING count > 1
    ''')
    
    duplicates = cursor.fetchall()
    
    deleted_count = 0
    for title, count, keep_id in duplicates:
        # Delete all but the oldest (lowest ID)
        cursor.execute('''
            DELETE FROM events 
            WHERE title = ? 
            AND approval_status = 'pending'
            AND id > ?
        ''', (title, keep_id))
        
        duplicates_removed = count - 1
        deleted_count += duplicates_removed
        print(f'   🔄 Kept 1, deleted {duplicates_removed} duplicates of: "{title[:50]}..."')
    
    conn.commit()
    conn.close()
    
    print(f'   Total duplicate events removed: {deleted_count}')
    return deleted_count

def analyze_improvement():
    """Analyze improvement after cleanup"""
    print('\n📈 ANALYZING IMPROVEMENT')
    print('=' * 30)
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    # Count remaining issues
    cursor.execute('SELECT COUNT(*) FROM events WHERE title LIKE "%&#%" OR title LIKE "%&lt;%"')
    remaining_html = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM events WHERE title IN ("Event Date", "Event Type", "Events")')
    remaining_generic = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) FROM (
            SELECT title, COUNT(*) as count
            FROM events 
            WHERE approval_status = 'pending'
            GROUP BY title
            HAVING count > 1
        )
    ''')
    remaining_duplicates = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM events WHERE approval_status = "pending"')
    total_pending = cursor.fetchone()[0]
    
    print(f'   Remaining HTML entity issues: {remaining_html}')
    print(f'   Remaining generic titles: {remaining_generic}')
    print(f'   Remaining duplicate groups: {remaining_duplicates}')
    print(f'   Total pending events: {total_pending}')
    
    # Show sample of cleaned titles
    cursor.execute('''
        SELECT title 
        FROM events 
        WHERE approval_status = 'pending'
        AND title NOT LIKE '%&#%'
        AND title NOT IN ('Event Date', 'Event Type')
        ORDER BY created_at DESC
        LIMIT 10
    ''')
    
    clean_samples = cursor.fetchall()
    
    print(f'\n✅ SAMPLE OF CLEAN TITLES:')
    for i, (title,) in enumerate(clean_samples, 1):
        display_title = title[:70] + '...' if len(title) > 70 else title
        print(f'   {i:2d}. "{display_title}"')
    
    conn.close()

def main():
    """Main cleanup process"""
    print('🚀 EMERGENCY TEXT ENCODING & DATA QUALITY FIX')
    print('=' * 60)
    
    # Step 1: Analyze current issues
    issues = analyze_current_issues()
    
    if sum(issues.values()) == 0:
        print('\n✅ No issues found - database is clean!')
        return
    
    # Step 2: Fix HTML entities
    html_fixed = fix_html_entities()
    
    # Step 3: Remove bad titles
    bad_deleted = remove_bad_titles()
    
    # Step 4: Remove exact duplicates
    duplicates_removed = remove_exact_duplicates()
    
    # Step 5: Analyze improvement
    analyze_improvement()
    
    # Summary
    print(f'\n🎯 CLEANUP COMPLETE')
    print(f'=' * 25)
    print(f'   HTML entities fixed: {html_fixed}')
    print(f'   Bad titles removed: {bad_deleted}')
    print(f'   Duplicates removed: {duplicates_removed}')
    print(f'   Total improvements: {html_fixed + bad_deleted + duplicates_removed}')
    
    print(f'\n🔗 Next Steps:')
    print(f'   1. Refresh admin approval page: http://localhost:5001/admin/approval')
    print(f'   2. Review cleaned event titles')
    print(f'   3. Update scrapers to prevent future issues')

if __name__ == '__main__':
    main()
