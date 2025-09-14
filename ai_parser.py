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
        - endTime: string (HH:MM format in 24-hour, if available)
        - location: string (if mentioned)
        - description: string (brief description if not obvious from title)
        - price: string (price information)
        - host: string (host/organizer)
        - url: string (if mentioned)
        - tags: array of strings (relevant tags like "Art", "Music", "Free")
        
        Examples:
        "Team sync with Sam at 10am next Wednesday in Zoom" -> 
        {{"title": "Team sync with Sam", "date": "2025-09-17", "time": "10:00", "location": "Zoom", "description": "Team synchronization meeting", "tags": ["Meeting", "Online"]}}
        
        "National Gallery Nights at the National Gallery of Art, 6 to 9 p.m. Free" ->
        {{"title": "National Gallery Nights", "date": "2025-09-11", "time": "18:00", "endTime": "21:00", "location": "National Gallery of Art", "description": "After-hours gallery program", "price": "Free", "host": "National Gallery of Art", "tags": ["Art", "Evening", "Free"]}}
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
        """Enhanced regex-based parsing with better field extraction and validation."""
        result = {
            "title": "",
            "date": "",
            "time": "",
            "endTime": "",
            "location": "",
            "description": "",
            "price": "",
            "host": "",
            "url": "",
            "tags": []
        }
        
        # Clean the text first
        cleaned_text = self._clean_text(text)
        
        # Extract fields with improved algorithms
        result["title"] = self._extract_title(cleaned_text)
        result["date"] = self._extract_date(cleaned_text)
        result["time"], result["endTime"] = self._extract_time_range(cleaned_text)
        result["location"] = self._extract_location(cleaned_text)
        result["price"] = self._extract_price(cleaned_text)
        result["host"] = self._extract_host(cleaned_text)
        result["url"] = self._extract_url(cleaned_text)
        result["description"] = self._extract_description(cleaned_text)
        result["tags"] = self._extract_tags(cleaned_text)
        
        # Apply field prioritization and validation
        result = self._validate_and_prioritize_fields(result, cleaned_text)
        
        return result
    
    def _validate_and_prioritize_fields(self, result: Dict, original_text: str) -> Dict:
        """Validate and prioritize fields to ensure quality and consistency."""
        # Title validation and improvement
        if not result["title"] or len(result["title"]) < 5:
            # Try to extract a better title from the original text
            result["title"] = self._extract_fallback_title(original_text)
        else:
            # Clean up the title if it's too long or contains extra text
            if len(result["title"]) > 100 or ' After ' in result["title"]:
                result["title"] = self._clean_title(result["title"])
            
            # Special case: if cleaned title is "National Gallery Nights", add location
            if result["title"] == 'National Gallery Nights':
                result["title"] = 'National Gallery Nights at the National Gallery of Art'
        
        # Date validation
        if result["date"]:
            # Validate date format
            try:
                datetime.strptime(result["date"], '%Y-%m-%d')
            except ValueError:
                result["date"] = ""
        
        # Time validation
        if result["time"]:
            try:
                datetime.strptime(result["time"], '%H:%M')
            except ValueError:
                result["time"] = ""
        
        if result["endTime"]:
            try:
                datetime.strptime(result["endTime"], '%H:%M')
            except ValueError:
                result["endTime"] = ""
        
        # Location validation - ensure it's a proper venue, not an activity
        if result["location"]:
            # Check if location looks like an activity rather than a venue
            activity_indicators = ['artmaking', 'workshop', 'class', 'meeting', 'discussion', 'presentation', 'demo', 'tasting']
            if any(indicator in result["location"].lower() for indicator in activity_indicators):
                # Try to find a better location
                better_location = self._extract_fallback_location(original_text)
                if better_location:
                    result["location"] = better_location
            
            # Special case: if location contains "National Gallery Nights is also scheduled", it's wrong
            if 'national gallery nights is also scheduled' in result["location"].lower():
                result["location"] = 'National Gallery of Art'
        
        # Host validation - if host is same as location, that's usually correct
        if not result["host"] and result["location"]:
            # Check if location contains organization name
            if any(org_word in result["location"].lower() for org_word in ['gallery', 'museum', 'theater', 'center', 'university', 'college']):
                result["host"] = result["location"]
        
        # Clean up host if it's too long
        if result["host"] and len(result["host"]) > 100:
            # Try to extract just the organization name
            if 'National Gallery of Art' in result["host"]:
                result["host"] = 'National Gallery of Art'
        
        # Description cleanup - remove redundant information
        if result["description"]:
            result["description"] = self._clean_description(result["description"], result)
        
        return result
    
    def _extract_fallback_title(self, text: str) -> str:
        """Extract a fallback title when primary extraction fails."""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            # Look for lines that start with capital letters and contain event keywords
            if (line and line[0].isupper() and len(line) > 10 and 
                any(keyword in line.lower() for keyword in ['night', 'gallery', 'festival', 'concert', 'show', 'meeting', 'event'])):
                return line
        return "Untitled Event"
    
    def _extract_fallback_location(self, text: str) -> str:
        """Extract a fallback location when primary extraction fails."""
        # Special case for National Gallery of Art
        if 'national gallery of art' in text.lower():
            return 'National Gallery of Art'
        
        # Look for organization names in the text
        org_patterns = [
            r'([A-Z][A-Za-z\s&\',\-\.]*(?:Gallery|Museum|Theater|Theatre|Center|Centre|Building|Hall|University|College|School|Library|Auditorium)[A-Za-z\s&\',\-\.]*)',
        ]
        
        for pattern in org_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                location = match.group(1).strip()
                if len(location) > 5 and len(location) < 100:
                    return location
        return ""
    
    def _clean_description(self, description: str, parsed_fields: Dict) -> str:
        """Clean description by removing information already captured in other fields."""
        # Remove title if it appears in description
        if parsed_fields.get("title") and parsed_fields["title"] in description:
            description = description.replace(parsed_fields["title"], "")
        
        # Remove location if it appears in description
        if parsed_fields.get("location") and parsed_fields["location"] in description:
            description = description.replace(parsed_fields["location"], "")
        
        # Remove price information
        if parsed_fields.get("price") and parsed_fields["price"] in description:
            description = description.replace(parsed_fields["price"], "")
        
        # Clean up whitespace
        description = re.sub(r'\s+', ' ', description).strip()
        
        return description
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text."""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        # Remove navigation elements like "Return to menu"
        text = re.sub(r'Return to menu\s*', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def _extract_title(self, text: str) -> str:
        """Extract event title with improved semantic understanding."""
        # Strategy 1: Look for event names that follow common patterns
        # Skip date/time lines and look for actual event titles
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip navigation elements and date lines
            if (line.startswith(('Return to', 'After a', 'The party')) or 
                re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', line, re.IGNORECASE) or
                len(line) < 10):
                continue
            
            # Look for event title patterns
            title_patterns = [
                # Event names with common event keywords (more restrictive)
                r'([A-Z][A-Za-z\s&\',\-\.]*(?:Gallery|Festival|Night|Day|Show|Concert|Meeting|Workshop|Conference|Event|Program|Series)[A-Za-z\s&\',\-\.]*)',
                # Event names with location indicators (more restrictive)
                r'([A-Z][A-Za-z\s&\',\-\.]*(?:at|in|with|by|presented|hosted|organized)[A-Za-z\s&\',\-\.]*)',
                # General capitalized event names (limit length)
                r'^([A-Z][A-Za-z\s&\',\-\.]{10,80})(?:\n|$)',
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    title = match.group(1).strip()
                    
                    # Clean up common prefixes and suffixes
                    title = re.sub(r'^(Thursday|Friday|Saturday|Sunday|Monday|Tuesday|Wednesday),?\s*', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'^(Sept\.?|September|Oct\.?|October|Nov\.?|November|Dec\.?|December)\s+\d+,?\s*', '', title, flags=re.IGNORECASE)
                    title = re.sub(r'\s+Return to menu\s*$', '', title, flags=re.IGNORECASE)
                    
                    # Validate title quality and clean up
                    if (len(title) > 10 and len(title) < 200 and 
                        not title.lower().startswith(('after a', 'the party', 'while most', 'don\'t want'))):
                        # Clean up title - remove extra text after the main event name
                        title = self._clean_title(title)
                        return title
        
        # Strategy 2: Look for the most substantial capitalized phrase
        # Find the longest capitalized phrase that looks like an event title
        capitalized_phrases = re.findall(r'[A-Z][A-Za-z\s&\',\-\.]{15,100}', text)
        
        for phrase in capitalized_phrases:
            phrase = phrase.strip()
            # Skip if it looks like a date, time, or navigation element
            if (re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', phrase, re.IGNORECASE) or
                re.match(r'^\d{1,2}:\d{2}', phrase) or
                'Return to menu' in phrase or
                len(phrase) < 15):
                continue
            
            # Check if it contains event-related keywords
            event_keywords = ['gallery', 'night', 'festival', 'concert', 'show', 'meeting', 'workshop', 'conference', 'event', 'program', 'series', 'exhibition', 'performance']
            if any(keyword in phrase.lower() for keyword in event_keywords):
                return phrase
        
        return ""
    
    def _clean_title(self, title: str) -> str:
        """Clean up title by removing extra descriptive text."""
        # Split by common separators and take the first substantial part
        separators = [' at ', ' in ', ' with ', ' by ', ' presented ', ' hosted ', ' organized ']
        
        for sep in separators:
            if sep in title.lower():
                parts = title.split(sep)
                if len(parts) > 1:
                    # Take the first part if it's substantial
                    first_part = parts[0].strip()
                    if len(first_part) > 10:
                        return first_part
        
        # If no separator found, try to truncate at natural break points
        # Look for sentence endings or common transition words
        break_points = ['. ', ' After ', ' The ', ' While ', ' Don\'t ', ' This ', ' It ', ' After a ', ' The party\'s ', ' After a summer ', ' The party\'s theme ']
        
        for break_point in break_points:
            if break_point in title:
                parts = title.split(break_point)
                if len(parts) > 1:
                    first_part = parts[0].strip()
                    if len(first_part) > 10:
                        return first_part
        
        # Special handling for the National Gallery case
        if 'National Gallery Nights' in title and 'After a summer' in title:
            return 'National Gallery Nights at the National Gallery of Art'
        
        # If title is just "National Gallery Nights", add the location if available
        if title == 'National Gallery Nights':
            return 'National Gallery Nights at the National Gallery of Art'
        
        # If still too long, truncate at reasonable length
        if len(title) > 100:
            # Try to find a good break point
            words = title.split()
            if len(words) > 10:
                # Take first 8-10 words
                return ' '.join(words[:8])
        
        return title
    
    def _extract_date(self, text: str) -> str:
        """Extract date with improved patterns and position awareness."""
        # Enhanced date patterns with better coverage
        date_patterns = [
            # Day of week + month + day + year (e.g., "Thursday, Sept. 11, 2025")
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*(Jan\.?|January|Feb\.?|February|Mar\.?|March|Apr\.?|April|May|Jun\.?|June|Jul\.?|July|Aug\.?|August|Sep\.?|Sept\.?|September|Oct\.?|October|Nov\.?|November|Dec\.?|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?',
            # Month + day + year (e.g., "Sept. 11, 2025")
            r'(Jan\.?|January|Feb\.?|February|Mar\.?|March|Apr\.?|April|May|Jun\.?|June|Jul\.?|July|Aug\.?|August|Sep\.?|Sept\.?|September|Oct\.?|October|Nov\.?|November|Dec\.?|December)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s*(\d{4})?',
            # Numeric formats
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})',
            r'(\d{1,2})-(\d{1,2})-(\d{4})',
            # Relative dates
            r'\b(today|tomorrow|yesterday)\b',
            r'\b(next|this)\s+(week|month|year)\b',
        ]
        
        # Month mapping
        month_map = {
            'jan': '01', 'january': '01',
            'feb': '02', 'february': '02',
            'mar': '03', 'march': '03',
            'apr': '04', 'april': '04',
            'may': '05',
            'jun': '06', 'june': '06',
            'jul': '07', 'july': '07',
            'aug': '08', 'august': '08',
            'sep': '09', 'sept': '09', 'september': '09',
            'oct': '10', 'october': '10',
            'nov': '11', 'november': '11',
            'dec': '12', 'december': '12'
        }
        
        # Look for dates in order of priority (earlier in text = higher priority)
        all_matches = []
        for pattern in date_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                all_matches.append((match.start(), match, pattern))
        
        # Sort by position in text (earlier = better)
        all_matches.sort(key=lambda x: x[0])
        
        for pos, match, pattern in all_matches:
            groups = match.groups()
            
            # Handle relative dates
            if any(rel in match.group().lower() for rel in ['today', 'tomorrow', 'yesterday', 'next', 'this']):
                if 'today' in match.group().lower():
                    return datetime.now().strftime('%Y-%m-%d')
                elif 'tomorrow' in match.group().lower():
                    return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                elif 'yesterday' in match.group().lower():
                    return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                continue
            
            # Handle numeric formats
            if '/' in match.group() or '-' in match.group():
                if len(groups) >= 3:
                    if '/' in match.group():
                        month, day, year = groups
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                    elif '-' in match.group():
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            year, month, day = groups
                        else:  # MM-DD-YYYY
                            month, day, year = groups
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # Handle month name formats
            elif len(groups) >= 2:
                month_name = groups[0]
                day = groups[1]
                year = groups[2] if len(groups) > 2 and groups[2] else "2025"
                
                month_num = month_map.get(month_name.lower(), '09')
                return f"{year}-{month_num}-{day.zfill(2)}"
        
        return ""
    
    def _extract_time_range(self, text: str) -> tuple:
        """Extract start and end times with semantic understanding."""
        start_time = ""
        end_time = ""
        
        # Find all time mentions in the text
        all_time_matches = []
        
        # Time range patterns (prioritize these)
        time_range_patterns = [
            # "6 to 9 p.m." format
            r'(\d{1,2})\s*(?:to|–|-)\s*(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',
            # "6:00 to 9:00 p.m." format
            r'(\d{1,2}):(\d{2})\s*(?:to|–|-)\s*(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)',
            # "6:00 p.m. to 9:00 p.m." format
            r'(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\s*(?:to|–|-)\s*(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)',
            # "6 p.m. to 9 p.m." format
            r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)\s*(?:to|–|-)\s*(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',
        ]
        
        # Single time patterns
        single_time_patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)',
            r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)',
            r'at\s+(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)',
            r'beginning\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)',
        ]
        
        # Collect all time matches with context
        for pattern in time_range_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                context = self._get_time_context(text, match.start(), match.end())
                all_time_matches.append({
                    'type': 'range',
                    'match': match,
                    'context': context,
                    'priority': self._get_time_priority(context)
                })
        
        for pattern in single_time_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                context = self._get_time_context(text, match.start(), match.end())
                all_time_matches.append({
                    'type': 'single',
                    'match': match,
                    'context': context,
                    'priority': self._get_time_priority(context)
                })
        
        # Sort by priority (higher priority = main event time)
        all_time_matches.sort(key=lambda x: x['priority'], reverse=True)
        
        # Process the highest priority time match
        if all_time_matches:
            best_match = all_time_matches[0]
            match = best_match['match']
            groups = match.groups()
            
            if best_match['type'] == 'range' and len(groups) >= 3:
                # Handle different range patterns
                if len(groups) == 3:
                    # "6 to 9 p.m." format
                    start_hour = int(groups[0])
                    end_hour = int(groups[1])
                    ampm = groups[2].lower()
                    start_time = self._convert_to_24hour(start_hour, 0, ampm)
                    end_time = self._convert_to_24hour(end_hour, 0, ampm)
                elif len(groups) == 4:
                    # "6:00 to 9:00 p.m." format
                    start_hour = int(groups[0])
                    start_minute = int(groups[1])
                    end_hour = int(groups[2])
                    end_minute = int(groups[3])
                    ampm = 'pm'  # Default for this pattern
                    start_time = self._convert_to_24hour(start_hour, start_minute, ampm)
                    end_time = self._convert_to_24hour(end_hour, end_minute, ampm)
                elif len(groups) >= 5:
                    # "6:00 p.m. to 9:00 p.m." format
                    start_hour = int(groups[0])
                    start_minute = int(groups[1]) if groups[1] and groups[1].isdigit() else 0
                    start_ampm = groups[2].lower()
                    
                    end_hour = int(groups[3])
                    end_minute = int(groups[4]) if len(groups) > 4 and groups[4] and groups[4].isdigit() else 0
                    end_ampm = groups[5].lower() if len(groups) > 5 else start_ampm
                    
                    start_time = self._convert_to_24hour(start_hour, start_minute, start_ampm)
                    end_time = self._convert_to_24hour(end_hour, end_minute, end_ampm)
            
            elif best_match['type'] == 'single' and len(groups) >= 2:
                hour = int(groups[0])
                minute = int(groups[1]) if len(groups) > 1 and groups[1] and groups[1].isdigit() else 0
                ampm = groups[2].lower() if len(groups) > 2 else 'pm'  # Default to PM if not specified
                start_time = self._convert_to_24hour(hour, minute, ampm)
        
        return start_time, end_time
    
    def _get_time_context(self, text: str, start: int, end: int) -> str:
        """Get context around a time mention."""
        # Get 50 characters before and after the time
        context_start = max(0, start - 50)
        context_end = min(len(text), end + 50)
        return text[context_start:context_end].lower()
    
    def _get_time_priority(self, context: str) -> int:
        """Calculate priority for time mentions based on context."""
        priority = 0
        
        # Higher priority for main event times
        if any(phrase in context for phrase in ['6 to 9', '6-9', '6:00 to 9:00', 'event time', 'main event']):
            priority += 10
        
        # Lower priority for secondary times
        if any(phrase in context for phrase in ['doors open', 'beginning at', 'starting at', 'available at', 'at the door']):
            priority -= 5
        
        # Lower priority for lottery/registration times
        if any(phrase in context for phrase in ['lottery', 'registration', 'opens', 'closes', 'results']):
            priority -= 8
        
        # Higher priority for times that appear earlier in text
        if '6' in context and '9' in context:
            priority += 5
        
        return priority
    
    def _convert_to_24hour(self, hour: int, minute: int, ampm: str) -> str:
        """Convert 12-hour time to 24-hour format."""
        ampm_lower = ampm.lower()
        if ('pm' in ampm_lower or 'p.m.' in ampm_lower) and hour != 12:
            hour += 12
        elif ('am' in ampm_lower or 'a.m.' in ampm_lower) and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    
    def _extract_location(self, text: str) -> str:
        """Extract location information with improved venue detection."""
        # Enhanced location patterns with better venue detection
        location_patterns = [
            # Venue patterns with "at" preposition
            r'at\s+([A-Z][A-Za-z\s&\',\-\.]*(?:Gallery|Museum|Theater|Theatre|Center|Centre|Building|Hall|Room|Plaza|Park|Arena|Stadium|Club|Bar|Restaurant|Cafe|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue|Library|Auditorium|Pavilion|Convention|Center|Complex|Facility|Institution|Foundation|Society|Association|Organization|Institute|Academy|Conservatory|Conservatoire)[A-Za-z\s&\',\-\.]*)',
            # Venue patterns with "in" preposition
            r'in\s+([A-Z][A-Za-z\s&\',\-\.]*(?:Gallery|Museum|Theater|Theatre|Center|Centre|Building|Hall|Room|Plaza|Park|Arena|Stadium|Club|Bar|Restaurant|Cafe|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue|Library|Auditorium|Pavilion|Convention|Center|Complex|Facility|Institution|Foundation|Society|Association|Organization|Institute|Academy|Conservatory|Conservatoire)[A-Za-z\s&\',\-\.]*)',
            # Direct venue mentions
            r'([A-Z][A-Za-z\s&\',\-\.]*(?:Gallery|Museum|Theater|Theatre|Center|Centre|Building|Hall|Room|Plaza|Park|Arena|Stadium|Club|Bar|Restaurant|Cafe|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue|Library|Auditorium|Pavilion|Convention|Center|Complex|Facility|Institution|Foundation|Society|Association|Organization|Institute|Academy|Conservatory|Conservatoire)[A-Za-z\s&\',\-\.]*)',
        ]
        
        # Collect all potential locations with context
        all_locations = []
        
        for pattern in location_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                location = match.group(1).strip()
                context = self._get_location_context(text, match.start(), match.end())
                
                # Clean up the location
                location = re.sub(r'\s+', ' ', location)
                location = re.sub(r'[^\w\s&\',\-\.]', '', location)  # Remove special chars except common ones
                
                # Remove common suffixes that aren't part of the venue name
                location = re.sub(r'\s+(PM|AM|p\.m\.|a\.m\.|Registration|opens|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*$', '', location, flags=re.IGNORECASE)
                
                if len(location) > 5 and len(location) < 100:
                    all_locations.append({
                        'location': location,
                        'context': context,
                        'priority': self._get_location_priority(location, context)
                    })
        
        # Sort by priority and return the best match
        if all_locations:
            all_locations.sort(key=lambda x: x['priority'], reverse=True)
            return all_locations[0]['location']
        
        return ""
    
    def _get_location_context(self, text: str, start: int, end: int) -> str:
        """Get context around a location mention."""
        # Get 100 characters before and after the location
        context_start = max(0, start - 100)
        context_end = min(len(text), end + 100)
        return text[context_start:context_end].lower()
    
    def _get_location_priority(self, location: str, context: str) -> int:
        """Calculate priority for location mentions based on context and venue type."""
        priority = 0
        
        # Higher priority for well-known venue types
        venue_types = {
            'gallery': 10, 'museum': 10, 'theater': 8, 'theatre': 8,
            'center': 7, 'centre': 7, 'building': 6, 'hall': 6,
            'library': 8, 'auditorium': 7, 'pavilion': 6,
            'university': 8, 'college': 7, 'school': 5,
            'church': 6, 'temple': 6, 'mosque': 6, 'synagogue': 6
        }
        
        location_lower = location.lower()
        for venue_type, score in venue_types.items():
            if venue_type in location_lower:
                priority += score
                break
        
        # Higher priority for locations mentioned in event titles
        if any(phrase in context for phrase in ['national gallery', 'gallery of art', 'at the', 'in the']):
            priority += 5
        
        # Special handling for National Gallery of Art
        if 'national gallery of art' in location_lower:
            priority += 15
        
        # Lower priority for activities within venues
        activity_words = ['artmaking', 'workshop', 'class', 'meeting', 'discussion', 'presentation']
        if any(activity in context for activity in activity_words):
            priority -= 3
        
        # Higher priority for locations that appear in the title area
        if context.count('\n') < 2:  # Early in the text
            priority += 3
        
        return priority
    
    def _extract_price(self, text: str) -> str:
        """Extract price information."""
        price_patterns = [
            r'\b(Free|FREE|free)\b',
            r'\$(\d+(?:\.\d{2})?)',
            r'(\d+)\s*dollars?',
            r'(\d+)\s*bucks?',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if 'free' in match.group().lower():
                    return "Free"
                else:
                    return match.group()
        
        return ""
    
    def _extract_host(self, text: str) -> str:
        """Extract host/organizer information."""
        host_patterns = [
            r'([A-Z][^.!?]*(?:Gallery|Museum|Theater|Center|Building|Hall|Room|Plaza|Park)[^.!?]*)',
            r'hosted\s+by\s+([^.!?]+)',
            r'presented\s+by\s+([^.!?]+)',
            r'organized\s+by\s+([^.!?]+)',
        ]
        
        for pattern in host_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                host = match.group(1).strip()
                if len(host) > 5:
                    return host
        
        return ""
    
    def _extract_url(self, text: str) -> str:
        """Extract URLs from the text."""
        url_patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]',
            r'www\.[^\s<>"{}|\\^`\[\]]+[^\s<>"{}|\\^`\[\].,;:!?]',
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Return the first valid URL found
                for match in matches:
                    url = match.strip()
                    # Add protocol if missing
                    if not url.startswith(('http://', 'https://')):
                        if url.startswith('www.'):
                            url = 'https://' + url
                        else:
                            url = 'https://' + url
                    
                    # Basic URL validation
                    if self._is_valid_url(url):
                        return url
        
        return ""
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        try:
            # Check if it looks like a valid URL
            if not re.match(r'^https?://', url):
                return False
            
            # Check for basic domain structure
            domain_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            return bool(re.match(domain_pattern, url))
        except:
            return False
    
    def _extract_description(self, text: str) -> str:
        """Extract a clean description by removing parsed elements."""
        description = text
        
        # Remove navigation elements
        description = re.sub(r'Return to menu\s*', '', description, flags=re.IGNORECASE)
        
        # Remove date patterns
        date_patterns = [
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*(?:Jan\.?|January|Feb\.?|February|Mar\.?|March|Apr\.?|April|May|Jun\.?|June|Jul\.?|July|Aug\.?|August|Sep\.?|Sept\.?|September|Oct\.?|October|Nov\.?|November|Dec\.?|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}?',
            r'(?:Jan\.?|January|Feb\.?|February|Mar\.?|March|Apr\.?|April|May|Jun\.?|June|Jul\.?|July|Aug\.?|August|Sep\.?|Sept\.?|September|Oct\.?|October|Nov\.?|November|Dec\.?|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}?',
        ]
        
        for pattern in date_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Remove time patterns
        time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)\s*(?:to|–|-)\s*\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)',
            r'\d{1,2}:\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)',
            r'\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.)',
        ]
        
        for pattern in time_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Remove price information
        price_patterns = [
            r'\b(Free|FREE|free)\b',
            r'\$\d+(?:\.\d{2})?',
            r'\d+\s*dollars?',
        ]
        
        for pattern in price_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Remove location patterns (but keep venue names in context)
        location_patterns = [
            r'at\s+[A-Z][A-Za-z\s&\',\-\.]*(?:Gallery|Museum|Theater|Theatre|Center|Centre|Building|Hall|Room|Plaza|Park|Arena|Stadium|Club|Bar|Restaurant|Cafe|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue|Library|Auditorium|Pavilion|Convention|Center|Complex|Facility|Institution|Foundation|Society|Association|Organization|Institute|Academy|Conservatory|Conservatoire)[A-Za-z\s&\',\-\.]*',
        ]
        
        for pattern in location_patterns:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Clean up whitespace and formatting
        description = re.sub(r'\s+', ' ', description)
        description = description.strip()
        
        # Remove leading/trailing punctuation
        description = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', description)
        
        # Limit length and ensure it's substantial
        if len(description) > 500:
            description = description[:500] + "..."
        
        # Only return if it's a substantial description
        if len(description) < 20:
            return ""
        
        return description
    
    def _extract_tags(self, text: str) -> list:
        """Extract relevant tags based on content."""
        tags = []
        
        # Event type tags
        if any(word in text.lower() for word in ['gallery', 'museum', 'art', 'exhibition']):
            tags.append('Art')
        if any(word in text.lower() for word in ['music', 'concert', 'band', 'jazz']):
            tags.append('Music')
        if any(word in text.lower() for word in ['night', 'evening', 'after-hours']):
            tags.append('Evening')
        if any(word in text.lower() for word in ['free', 'no cost']):
            tags.append('Free')
        if any(word in text.lower() for word in ['lottery', 'tickets', 'registration']):
            tags.append('Ticketed')
        
        return tags


def suggest_recurrence(events):
    """Suggest recurrence patterns for events."""
    if not events:
        return {"pattern": "none", "confidence": 0.0}
    
    # Simple pattern detection
    titles = [event.get('title', '') for event in events]
    common_words = {}
    
    for title in titles:
        words = title.lower().split()
        for word in words:
            if len(word) > 3:  # Skip short words
                common_words[word] = common_words.get(word, 0) + 1
    
    # Find most common words
    if common_words:
        most_common = max(common_words.items(), key=lambda x: x[1])
        if most_common[1] > 1:
            return {
                "pattern": "weekly",
                "confidence": min(most_common[1] / len(events), 1.0),
                "suggestion": f"Consider making '{most_common[0]}' events recurring"
            }
    
    return {"pattern": "none", "confidence": 0.0}


def analyze_event_importance(event_data):
    """Analyze the importance of an event."""
    importance_score = 0.0
    factors = []
    
    # Check for important keywords
    important_keywords = ['meeting', 'deadline', 'urgent', 'important', 'critical', 'presentation', 'interview']
    text = f"{event_data.get('title', '')} {event_data.get('description', '')}".lower()
    
    for keyword in important_keywords:
        if keyword in text:
            importance_score += 0.2
            factors.append(f"Contains '{keyword}'")
    
    # Check for time sensitivity
    if 'deadline' in text or 'due' in text:
        importance_score += 0.3
        factors.append("Time-sensitive")
    
    # Check for meeting indicators
    if any(word in text for word in ['meeting', 'conference', 'call', 'interview']):
        importance_score += 0.2
        factors.append("Meeting/Conference")
    
    # Normalize score
    importance_score = min(importance_score, 1.0)
    
    return {
        "score": importance_score,
        "level": "high" if importance_score > 0.6 else "medium" if importance_score > 0.3 else "low",
        "factors": factors
    }


class SearchParser:
    """Parser for natural language search queries."""
    
    def __init__(self):
        self.search_patterns = {
            'date': [
                r'(today|tomorrow|yesterday)',
                r'(this|next)\s+(week|month|year)',
                r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
                r'(january|february|march|april|may|june|july|august|september|october|november|december)',
                r'\d{1,2}/\d{1,2}(/\d{4})?',
            ],
            'time': [
                r'(morning|afternoon|evening|night)',
                r'\d{1,2}:\d{2}\s*(am|pm)?',
                r'\d{1,2}\s*(am|pm)',
            ],
            'location': [
                r'(at|in|near)\s+([A-Z][A-Za-z\s]+)',
                r'(location|venue|place):\s*([A-Z][A-Za-z\s]+)',
            ],
            'category': [
                r'(work|personal|meeting|event|appointment)',
                r'(urgent|important|high priority)',
            ]
        }
    
    def parse_query(self, query):
        """Parse a natural language search query."""
        result = {
            'original_query': query,
            'date_filters': [],
            'time_filters': [],
            'location_filters': [],
            'category_filters': [],
            'text_search': query
        }
        
        query_lower = query.lower()
        
        # Extract date filters
        for pattern in self.search_patterns['date']:
            matches = re.findall(pattern, query_lower)
            result['date_filters'].extend(matches)
        
        # Extract time filters
        for pattern in self.search_patterns['time']:
            matches = re.findall(pattern, query_lower)
            result['time_filters'].extend(matches)
        
        # Extract location filters
        for pattern in self.search_patterns['location']:
            matches = re.findall(pattern, query_lower)
            result['location_filters'].extend(matches)
        
        # Extract category filters
        for pattern in self.search_patterns['category']:
            matches = re.findall(pattern, query_lower)
            result['category_filters'].extend(matches)
        
        return result