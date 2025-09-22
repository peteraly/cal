#!/usr/bin/env python3
"""
Washington Post Events Parser
Parses events from the Washington Post events text file format
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import dateparser
from dataclasses import dataclass


@dataclass
class WPEvent:
    """Washington Post Event data structure"""
    title: str
    location_name: str
    address: str
    price: str
    date: str
    time: str
    end_time: Optional[str] = None
    description: str = ""
    url: str = ""
    tags: str = ""


class WashingtonPostParser:
    """Parser for Washington Post events text format"""
    
    def __init__(self):
        self.events = []
        
    def parse_file(self, file_path: str) -> List[WPEvent]:
        """Parse the Washington Post events file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return self.parse_content(content)
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return []
        except Exception as e:
            print(f"Error reading file: {e}")
            return []
    
    def parse_content(self, content: str) -> List[WPEvent]:
        """Parse events from content string"""
        # Split content into individual events
        events_text = self._split_into_events(content)
        
        for event_text in events_text:
            if self._is_valid_event(event_text):
                event = self._parse_single_event(event_text)
                if event:
                    self.events.append(event)
        
        return self.events
    
    def _split_into_events(self, content: str) -> List[str]:
        """Split content into individual event blocks"""
        # Events are separated by lines of underscores
        events = re.split(r'_{10,}', content)
        
        # Filter out empty events and the URL line at the top
        valid_events = []
        for event in events:
            event = event.strip()
            if event and not event.startswith('https://') and len(event) > 50:
                valid_events.append(event)
        
        return valid_events
    
    def _is_valid_event(self, event_text: str) -> bool:
        """Check if the text block contains a valid event"""
        # Must have title, location, and date/time
        has_title = any(line.strip() for line in event_text.split('\n')[:5])
        has_location = 'Library' in event_text or 'Bookstore' in event_text or 'Center' in event_text or 'Theatre' in event_text
        has_date = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d+', event_text)
        
        return has_title and has_location and has_date
    
    def _parse_single_event(self, event_text: str) -> Optional[WPEvent]:
        """Parse a single event from text"""
        try:
            lines = [line.strip() for line in event_text.split('\n') if line.strip()]
            
            # Extract title (usually first non-empty line)
            title = self._extract_title(lines)
            
            # Extract location
            location_name, address = self._extract_location(lines)
            
            # Extract price
            price = self._extract_price(lines)
            
            # Extract date and time
            date, time, end_time = self._extract_datetime(lines)
            
            # Extract description
            description = self._extract_description(event_text, title)
            
            # Extract URL if present
            url = self._extract_url(event_text)
            
            # Generate tags
            tags = self._generate_tags(title, description)
            
            return WPEvent(
                title=title,
                location_name=location_name,
                address=address,
                price=price,
                date=date,
                time=time,
                end_time=end_time,
                description=description,
                url=url,
                tags=tags
            )
            
        except Exception as e:
            print(f"Error parsing event: {e}")
            return None
    
    def _extract_title(self, lines: List[str]) -> str:
        """Extract event title from lines"""
        # Look for title in first few lines, excluding obvious non-titles
        for i, line in enumerate(lines[:5]):
            if (len(line) > 10 and 
                not line.startswith('$') and 
                not re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+\w+\s+\d+', line) and
                not line.startswith('FULL DESCRIPTION') and
                not line.startswith('About the') and
                not line.startswith('Ages') and
                not line.startswith('RSVP')):
                return line
        
        return "Event Title"
    
    def _extract_location(self, lines: List[str]) -> Tuple[str, str]:
        """Extract location name and address"""
        location_name = ""
        address = ""
        
        # Look for location patterns
        for line in lines:
            # Common venue patterns
            if any(venue in line for venue in ['Library', 'Bookstore', 'Center', 'Theatre', 'Museum', 'Gallery', 'Hall']):
                if not location_name:
                    location_name = line
            # Address patterns
            elif re.search(r'\d+\s+\w+.*(?:Street|Avenue|Road|Boulevard|NW|NE|SW|SE)', line):
                address = line
            # Simple venue names
            elif len(line) < 50 and not location_name and not re.match(r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)', line):
                location_name = line
        
        return location_name or "Location TBD", address
    
    def _extract_price(self, lines: List[str]) -> str:
        """Extract price information"""
        for line in lines:
            # Look for price patterns
            if re.search(r'\$\d+', line):
                return line
            elif 'Free' in line:
                return 'Free'
            elif re.search(r'\d+\s*-\s*\d+', line) and ('$' in line or 'Free' in line):
                return line
        
        return "Price TBD"
    
    def _extract_datetime(self, lines: List[str]) -> Tuple[str, str, Optional[str]]:
        """Extract date and time information"""
        date = ""
        time = ""
        end_time = None
        
        for line in lines:
            # Date pattern: "Tue, Sep 16" or "Mon, Sep 16"
            date_match = re.search(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(\w+)\s+(\d+)', line)
            if date_match and not date:
                day, month, day_num = date_match.groups()
                # Convert to full date (assuming current year)
                current_year = datetime.now().year
                date_str = f"{month} {day_num}, {current_year}"
                parsed_date = dateparser.parse(date_str)
                if parsed_date:
                    date = parsed_date.strftime('%Y-%m-%d')
            
            # Time patterns
            time_match = re.search(r'(\d{1,2}:\d{2}(?:am|pm)?)\s*(?:-|to)\s*(\d{1,2}:\d{2}(?:am|pm)?)', line, re.IGNORECASE)
            if time_match:
                time = time_match.group(1)
                end_time = time_match.group(2)
            else:
                time_match = re.search(r'(\d{1,2}:\d{2}(?:am|pm)?)', line, re.IGNORECASE)
                if time_match and not time:
                    time = time_match.group(1)
        
        return date or datetime.now().strftime('%Y-%m-%d'), time or "7:00pm", end_time
    
    def _extract_description(self, event_text: str, title: str) -> str:
        """Extract event description"""
        # Find the description section
        desc_start = event_text.find('FULL DESCRIPTION')
        if desc_start != -1:
            description = event_text[desc_start + len('FULL DESCRIPTION'):].strip()
            # Clean up the description
            description = re.sub(r'^[\s\n]+', '', description)
            description = re.sub(r'[\s\n]+$', '', description)
            # Remove the title from description if it appears
            if title in description:
                description = description.replace(title, '').strip()
            return description[:500]  # Limit length
        
        return ""
    
    def _extract_url(self, event_text: str) -> str:
        """Extract URL if present"""
        url_match = re.search(r'https?://[^\s]+', event_text)
        return url_match.group(0) if url_match else ""
    
    def _generate_tags(self, title: str, description: str) -> str:
        """Generate tags based on title and description"""
        tags = []
        text = (title + " " + description).lower()
        
        # Book-related tags
        if any(word in text for word in ['book', 'author', 'discuss', 'reading', 'poetry']):
            tags.append('books')
        
        # Event type tags
        if 'free' in text:
            tags.append('free')
        if 'library' in text:
            tags.append('library')
        if 'bookstore' in text:
            tags.append('bookstore')
        if 'poetry' in text:
            tags.append('poetry')
        if 'children' in text or 'kids' in text:
            tags.append('children')
        
        return ', '.join(tags)
    
    def to_dict_list(self) -> List[Dict]:
        """Convert events to dictionary list for API"""
        return [
            {
                'title': event.title,
                'location_name': event.location_name,
                'address': event.address,
                'price_info': event.price,
                'start_datetime': self._format_datetime(event.date, event.time),
                'end_datetime': self._format_datetime(event.date, event.end_time) if event.end_time else None,
                'description': event.description,
                'url': event.url,
                'tags': event.tags,
                'category': 'Literature'  # Default category for WP events
            }
            for event in self.events
        ]
    
    def _format_datetime(self, date: str, time: str) -> Optional[str]:
        """Format date and time into ISO format"""
        if not date or not time:
            return None
        
        try:
            # Parse time and convert to 24-hour format
            time_clean = re.sub(r'[^\d:apm]', '', time.lower())
            if 'pm' in time_clean and ':' in time_clean:
                hour, minute = time_clean.replace('pm', '').split(':')
                hour = int(hour)
                if hour != 12:
                    hour += 12
                time_24 = f"{hour:02d}:{minute}:00"
            elif 'am' in time_clean and ':' in time_clean:
                hour, minute = time_clean.replace('am', '').split(':')
                hour = int(hour)
                if hour == 12:
                    hour = 0
                time_24 = f"{hour:02d}:{minute}:00"
            else:
                time_24 = f"{time_clean}:00"
            
            return f"{date} {time_24}"
        except:
            return f"{date} 19:00:00"  # Default to 7 PM


def main():
    """Test the parser"""
    parser = WashingtonPostParser()
    
    # Test with sample content
    sample_content = """
Jennifer Closes' "The Hopefuls" is discussed during Read & Run on the Road book club
 The Exchange Saloon
$10 - $25
Tue, Sep 16
6:00pm - 8:00pm
Jennifer Closes' "The Hopefuls" is discussed during Read & Run on the Road book club
FULL DESCRIPTION
On this 3.3 mile, easy-paced book club run, we'll see DC through the eyes of a New Yorker who's reluctantly moved to Dupont Circle/Kalorama.
This 3.3 mile, easy-paced book club run, is for anyone who's moved to DC, perhaps reluctantly, or who'd like to poke some fun at the things that can make this city an odd place to live.
The Hopefuls is about a young married couple that moves from NYC to DC because it's the husband's lifelong dream to run for office. The narrator (the wife) was reluctant to move and has a lot of complaints about DC: the constant politicking, the weather, and the metro—to name a few. Let's talk about big transitions in life and how the circumstances of those moves can impact how we see our new city in this lighthearted book.
On the route for this Read & Run on the Road event, created and led by me (Chelsey Stone), we'll stop at several locations to visit significant places throughout the story.
Learn more on my website: chelseygrassfield.com
(P.S. I'd like to eliminate fees for you and me, so if you happen to mosey on over to my webpage above, there's info on how to venmo and register via google forms.)
PREPARE: As this event is a book club run, it focuses on the plot, characters, and story. Attendees are strongly encouraged to read the book ahead of time to have the best experience. There is runner participation in the stops and opportunities for discussion, thoughts, and questions—similar to a traditional book club.
Physical and digital copies of the book are available at the DC Public Library.
INCLEMENT WEATHER PLAN: If weather creates unsafe conditions, we will hold the discussion at The Exchange Saloon (1719 G St NW) at 6 p.m. I will inform you no later than Tuesday, September 16 by noon if an alternate event will take place.
+
-
The Exchange Saloon
1719 G Street Northwest, Washington, DC 20006
________________
"""
    
    events = parser.parse_content(sample_content)
    print(f"Parsed {len(events)} events")
    
    for event in events:
        print(f"\nTitle: {event.title}")
        print(f"Location: {event.location_name}")
        print(f"Address: {event.address}")
        print(f"Date: {event.date}")
        print(f"Time: {event.time}")
        print(f"Price: {event.price}")
        print(f"Tags: {event.tags}")


if __name__ == "__main__":
    main()








