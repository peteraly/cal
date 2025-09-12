"""
AI-powered event parsing module for the calendar app.
Handles natural language input and converts it to structured event data.
"""

import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# Try to import optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from dateparser import parse as parse_date
    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False


class EventParser:
    """Main class for parsing natural language into event data."""
    
    def __init__(self):
        self.openai_client = None
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.openai_client = openai
    
    def parse_natural_language(self, text: str) -> Dict:
        """
        Parse natural language text into structured event data.
        
        Args:
            text: Natural language description of an event
            
        Returns:
            Dict with parsed event fields
        """
        # Try OpenAI first if available
        if self.openai_client:
            try:
                return self._parse_with_openai(text)
            except Exception as e:
                print(f"OpenAI parsing failed: {e}, falling back to regex")
        
        # Fallback to regex-based parsing
        return self._parse_with_regex(text)
    
    def _parse_with_openai(self, text: str) -> Dict:
        """Parse using OpenAI API."""
        prompt = f"""
        Parse this natural language event description into structured data:
        "{text}"
        
        Return a JSON object with these fields:
        - title: string (event title)
        - date: string (YYYY-MM-DD format)
        - time: string (HH:MM format in 24-hour)
        - location: string (if mentioned)
        - description: string (brief description if not obvious from title)
        - tags: array of strings (relevant tags like "Meeting", "Online", "Workshop")
        
        Examples:
        "Team sync with Sam at 10am next Wednesday in Zoom" -> 
        {{"title": "Team sync with Sam", "date": "2025-09-17", "time": "10:00", "location": "Zoom", "description": "Team synchronization meeting", "tags": ["Meeting", "Online"]}}
        
        "Lunch with John tomorrow at 12:30pm" ->
        {{"title": "Lunch with John", "date": "2025-09-12", "time": "12:30", "location": "", "description": "Lunch meeting", "tags": ["Personal", "Meeting"]}}
        """
        
        response = self.openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # If JSON parsing fails, fall back to regex
            return self._parse_with_regex(text)
    
    def _parse_with_regex(self, text: str) -> Dict:
        """Fallback regex-based parsing."""
        result = {
            "title": "",
            "date": "",
            "time": "",
            "location": "",
            "description": "",
            "tags": []
        }
        
        # Extract title from the first line or before the first period
        title_match = re.search(r'^([^.\n]+)', text.strip())
        if title_match:
            result["title"] = title_match.group(1).strip()
        
        # Extract time patterns - look for specific times mentioned
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)',
            r'at\s+(\d{1,2}):(\d{2})',
            r'at\s+(\d{1,2})',
            r'(\d{1,2}):(\d{2})\s*p\.m\.',
            r'(\d{1,2}):(\d{2})\s*a\.m\.',
            r'(\d{1,2})\s*p\.m\.',
            r'(\d{1,2})\s*a\.m\.',
            r'from\s+(\d{1,2})\s*to\s+(\d{1,2})',
            r'(\d{1,2})\s*to\s+(\d{1,2})\s*p\.m\.',
            r'(\d{1,2})\s*to\s+(\d{1,2})\s*pm',
            r'(\d{1,2})\s*p\.m\.',  # Simple p.m. pattern
            r'(\d{1,2})\s*pm'       # Simple pm pattern
        ]
        
        time_match = None
        for pattern in time_patterns:
            time_match = re.search(pattern, text, re.IGNORECASE)
            if time_match:
                break
        
        if time_match:
            groups = time_match.groups()
            if len(groups) >= 1:
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) > 1 and groups[1] and groups[1].isdigit() else 0
                ampm = groups[-1].lower() if groups[-1] in ['am', 'pm', 'a.m.', 'p.m.'] else None
                
                # Handle time ranges (e.g., "2 to 6 p.m.")
                if 'to' in time_match.group().lower():
                    # Use the start time for the event
                    pass
                
                if ampm and ('pm' in ampm or 'p.m.' in ampm) and hour != 12:
                    hour += 12
                elif ampm and ('am' in ampm or 'a.m.' in ampm) and hour == 12:
                    hour = 0
                
                result["time"] = f"{hour:02d}:{minute:02d}"
        
        # Extract date patterns - look for specific dates or relative dates
        date_patterns = [
            r'tomorrow',
            r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'this\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'in\s+(\d+)\s+days?',
            r'(\d{1,2})/(\d{1,2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})'
        ]
        
        date_match = None
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                break
        
        if date_match:
            result["date"] = self._parse_date_expression(date_match.group(), text)
        
        # Extract location patterns - look for specific venues or places
        location_patterns = [
            r'at\s+([A-Za-z\s]+?)(?:\s|,|\.|$)',
            r'in\s+([A-Za-z\s]+?)(?:\s|,|\.|$)',
            r'via\s+([A-Za-z\s]+?)(?:\s|,|\.|$)',
            r'on\s+([A-Za-z\s]+?)(?:\s|,|\.|$)',
            r'([A-Za-z\s]+?)\s+Park',
            r'([A-Za-z\s]+?)\s+Center',
            r'([A-Za-z\s]+?)\s+Street'
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, text, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
                # Filter out common words that aren't locations
                if location.lower() not in ['the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'includes', 'that', 'this', 'with', 'for', 'from', 'to']:
                    result["location"] = location
                    break
        
        # If no specific location found, look for venue names
        if not result["location"]:
            venue_patterns = [
                r'([A-Za-z\s]+?)\s+Park',
                r'([A-Za-z\s]+?)\s+Center',
                r'([A-Za-z\s]+?)\s+Street',
                r'([A-Za-z\s]+?)\s+Recreation\s+Center',
                r'Petworth\s+Park',
                r'Upshur\s+Street',
                r'Petworth\s+Recreation\s+Center'
            ]
            
            for pattern in venue_patterns:
                venue_match = re.search(pattern, text, re.IGNORECASE)
                if venue_match:
                    result["location"] = venue_match.group(0).strip()
                    break
        
        # Use the full text as description if no specific description found
        if not result["description"]:
            result["description"] = text.strip()
        
        # Auto-generate tags based on content
        result["tags"] = self._generate_tags(text, result)
        
        return result
    
    def _parse_date_expression(self, expression: str, full_text: str) -> str:
        """Parse date expressions into YYYY-MM-DD format."""
        today = datetime.now()
        
        if 'tomorrow' in expression.lower():
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime('%Y-%m-%d')
        
        if 'next' in expression.lower():
            # Simple weekday parsing
            weekdays = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            for day, day_num in weekdays.items():
                if day in expression.lower():
                    days_ahead = day_num - today.weekday()
                    if days_ahead <= 0:
                        days_ahead += 7
                    target_date = today + timedelta(days=days_ahead)
                    return target_date.strftime('%Y-%m-%d')
        
        if 'in' in expression.lower() and 'days' in expression.lower():
            # Extract number of days
            days_match = re.search(r'in\s+(\d+)', expression)
            if days_match:
                days = int(days_match.group(1))
                target_date = today + timedelta(days=days)
                return target_date.strftime('%Y-%m-%d')
        
        # Try to parse month names
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        for month_name, month_num in months.items():
            if month_name in expression.lower():
                # Look for day number
                day_match = re.search(r'(\d{1,2})', expression)
                if day_match:
                    day = int(day_match.group(1))
                    year = today.year
                    # If the month has passed this year, use next year
                    if month_num < today.month or (month_num == today.month and day < today.day):
                        year += 1
                    try:
                        target_date = datetime(year, month_num, day)
                        return target_date.strftime('%Y-%m-%d')
                    except ValueError:
                        pass
        
        # Try dateparser if available
        if DATEPARSER_AVAILABLE:
            try:
                parsed_date = parse_date(full_text)
                if parsed_date:
                    return parsed_date.strftime('%Y-%m-%d')
            except:
                pass
        
        # Default to today if no date found
        return today.strftime('%Y-%m-%d')
    
    def _generate_tags(self, text: str, parsed_data: Dict) -> List[str]:
        """Generate relevant tags based on content."""
        tags = []
        text_lower = text.lower()
        
        # Meeting-related tags
        if any(word in text_lower for word in ['meeting', 'sync', 'standup', 'review', 'call']):
            tags.append('Meeting')
        
        # Online/remote tags
        if any(word in text_lower for word in ['zoom', 'teams', 'google meet', 'online', 'remote', 'virtual']):
            tags.append('Online')
        
        # Work-related tags
        if any(word in text_lower for word in ['team', 'work', 'project', 'client', 'business']):
            tags.append('Work')
        
        # Personal tags
        if any(word in text_lower for word in ['lunch', 'dinner', 'coffee', 'personal', 'family']):
            tags.append('Personal')
        
        # Event type tags
        if any(word in text_lower for word in ['workshop', 'training', 'seminar', 'conference']):
            tags.append('Workshop')
        
        if any(word in text_lower for word in ['launch', 'release', 'demo', 'presentation']):
            tags.append('Important')
        
        return tags
    
    def _generate_description(self, title: str) -> str:
        """Generate a brief description based on the title."""
        title_lower = title.lower()
        
        if 'meeting' in title_lower or 'sync' in title_lower:
            return "Scheduled meeting"
        elif 'lunch' in title_lower or 'dinner' in title_lower:
            return "Meal meeting"
        elif 'call' in title_lower:
            return "Phone or video call"
        elif 'workshop' in title_lower or 'training' in title_lower:
            return "Educational session"
        else:
            return "Scheduled event"


def suggest_recurrence(events: List[Dict]) -> Optional[Dict]:
    """
    Analyze events to suggest recurrence patterns.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        Dict with recurrence suggestion or None
    """
    if len(events) < 2:
        return None
    
    # Simple pattern detection
    recent_events = sorted(events, key=lambda x: x.get('start_datetime', ''))[-5:]
    
    # Check for weekly patterns
    for i in range(len(recent_events) - 1):
        current = datetime.fromisoformat(recent_events[i]['start_datetime'].replace('T', ' '))
        next_event = datetime.fromisoformat(recent_events[i + 1]['start_datetime'].replace('T', ' '))
        
        # Check if events are roughly 7 days apart and similar times
        time_diff = (next_event - current).days
        if 6 <= time_diff <= 8:  # Weekly pattern
            time_diff_minutes = abs((next_event.hour * 60 + next_event.minute) - 
                                  (current.hour * 60 + current.minute))
            if time_diff_minutes <= 30:  # Similar time
                return {
                    'type': 'weekly',
                    'interval': 1,
                    'count': 4,
                    'message': f"This looks like a recurring event. Want to repeat weekly for 4 weeks?"
                }
    
    return None


def analyze_event_importance(event: Dict) -> Dict:
    """
    Analyze event importance for highlighting.
    
    Args:
        event: Event dictionary
        
    Returns:
        Dict with importance level and reason
    """
    importance = 'normal'
    reason = ''
    
    title_lower = event.get('title', '').lower()
    tags = event.get('tags', [])
    
    # High importance indicators
    high_importance_words = ['launch', 'keynote', 'deadline', 'urgent', 'critical', 'important']
    if any(word in title_lower for word in high_importance_words):
        importance = 'high'
        reason = 'Contains high-priority keywords'
    
    # Check tags
    if 'Important' in tags or 'Launch' in tags:
        importance = 'high'
        reason = 'Marked as important'
    
    # Meeting with multiple people
    if 'meeting' in title_lower and any(word in title_lower for word in ['team', 'all', 'group']):
        importance = 'medium'
        reason = 'Group meeting'
    
    return {
        'level': importance,
        'reason': reason
    }


class SearchParser:
    """Parse natural language search queries into structured filters."""
    
    def __init__(self):
        self.openai_client = None
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.openai_client = openai
    
    def parse_search_query(self, query: str) -> Dict:
        """
        Parse natural language search query into structured filters.
        
        Args:
            query: Natural language search query
            
        Returns:
            Dict with search filters
        """
        if not query.strip():
            return {}
        
        # Try OpenAI first if available
        if self.openai_client:
            try:
                return self._parse_with_openai(query)
            except Exception as e:
                print(f"OpenAI search parsing failed: {e}, falling back to regex")
        
        # Fallback to regex-based parsing
        return self._parse_with_regex(query)
    
    def _parse_with_openai(self, query: str) -> Dict:
        """Parse search query using OpenAI API."""
        prompt = f"""
        Parse this natural language search query into structured filters:
        "{query}"
        
        Return a JSON object with these possible fields:
        - keywords: array of strings (search terms)
        - tags: array of strings (event tags to filter by)
        - date_range: object with "start" and "end" dates (YYYY-MM-DD format)
        - time_range: object with "start" and "end" times (HH:MM format)
        - location: string (location to filter by)
        - category: string (category name to filter by)
        
        Examples:
        "events next week" -> {{"date_range": {{"start": "2025-09-15", "end": "2025-09-21"}}}}
        "workshops in October" -> {{"tags": ["Workshop"], "date_range": {{"start": "2025-10-01", "end": "2025-10-31"}}}}
        "zoom calls on Friday" -> {{"tags": ["Online"], "keywords": ["zoom"], "day_of_week": 5}}
        "meetings next Monday" -> {{"tags": ["Meeting"], "date_range": {{"start": "2025-09-15", "end": "2025-09-15"}}}}
        "work events" -> {{"tags": ["Work"]}}
        "lunch meetings" -> {{"tags": ["Meeting"], "keywords": ["lunch"]}}
        """
        
        response = self.openai_client.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # If JSON parsing fails, fall back to regex
            return self._parse_with_regex(query)
    
    def _parse_with_regex(self, query: str) -> Dict:
        """Fallback regex-based search parsing."""
        filters = {}
        query_lower = query.lower()
        
        # Extract keywords (remove common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        words = re.findall(r'\b\w+\b', query_lower)
        keywords = [word for word in words if word not in common_words and len(word) > 2]
        if keywords:
            filters['keywords'] = keywords
        
        # Extract tags
        tag_mappings = {
            'meeting': ['Meeting'],
            'meetings': ['Meeting'],
            'workshop': ['Workshop'],
            'workshops': ['Workshop'],
            'training': ['Workshop'],
            'online': ['Online'],
            'zoom': ['Online'],
            'remote': ['Online'],
            'virtual': ['Online'],
            'work': ['Work'],
            'personal': ['Personal'],
            'lunch': ['Personal'],
            'dinner': ['Personal'],
            'social': ['Social'],
            'health': ['Health'],
            'travel': ['Travel'],
            'important': ['Important'],
            'urgent': ['Important'],
            'deadline': ['Important']
        }
        
        tags = []
        for word, tag_list in tag_mappings.items():
            if word in query_lower:
                tags.extend(tag_list)
        
        if tags:
            filters['tags'] = list(set(tags))  # Remove duplicates
        
        # Extract date ranges
        date_filters = self._extract_date_filters(query)
        if date_filters:
            filters.update(date_filters)
        
        # Extract time ranges
        time_filters = self._extract_time_filters(query)
        if time_filters:
            filters.update(time_filters)
        
        # Extract location
        location_patterns = [
            r'in\s+([A-Za-z\s]+?)(?:\s|$)',
            r'at\s+([A-Za-z\s]+?)(?:\s|$)',
            r'via\s+([A-Za-z\s]+?)(?:\s|$)',
            r'on\s+([A-Za-z\s]+?)(?:\s|$)'
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, query, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
                if location.lower() not in ['the', 'a', 'an', 'and', 'or', 'but']:
                    filters['location'] = location
                    break
        
        return filters
    
    def _extract_date_filters(self, query: str) -> Dict:
        """Extract date range filters from query."""
        filters = {}
        query_lower = query.lower()
        today = datetime.now()
        
        # Next week
        if 'next week' in query_lower:
            start_date = today + timedelta(days=(7 - today.weekday()))
            end_date = start_date + timedelta(days=6)
            filters['date_range'] = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        
        # This week
        elif 'this week' in query_lower:
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            filters['date_range'] = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        
        # Next month
        elif 'next month' in query_lower:
            if today.month == 12:
                start_date = today.replace(year=today.year + 1, month=1, day=1)
            else:
                start_date = today.replace(month=today.month + 1, day=1)
            if start_date.month == 12:
                end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
            filters['date_range'] = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
        
        # Specific months
        months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        for month_name, month_num in months.items():
            if month_name in query_lower:
                year = today.year
                if month_num < today.month:
                    year += 1
                
                start_date = datetime(year, month_num, 1)
                if month_num == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)
                
                filters['date_range'] = {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                }
                break
        
        # Specific weekdays
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in weekdays.items():
            if day_name in query_lower:
                # Find next occurrence of this weekday
                days_ahead = day_num - today.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = today + timedelta(days=days_ahead)
                filters['date_range'] = {
                    'start': target_date.strftime('%Y-%m-%d'),
                    'end': target_date.strftime('%Y-%m-%d')
                }
                break
        
        return filters
    
    def _extract_time_filters(self, query: str) -> Dict:
        """Extract time range filters from query."""
        filters = {}
        query_lower = query.lower()
        
        # Morning
        if 'morning' in query_lower:
            filters['time_range'] = {'start': '06:00', 'end': '12:00'}
        
        # Afternoon
        elif 'afternoon' in query_lower:
            filters['time_range'] = {'start': '12:00', 'end': '18:00'}
        
        # Evening
        elif 'evening' in query_lower:
            filters['time_range'] = {'start': '18:00', 'end': '23:59'}
        
        return filters
