"""
Advanced Event Parser with Data Validation
Comprehensive parsing tool for event data with NLP and validation
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import dateutil.parser
from urllib.parse import urlparse
import requests
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ParsedEvent:
    """Structured event data model"""
    title: str = ""
    date: str = ""
    time: str = ""
    end_time: str = ""
    location_name: str = ""
    address: str = ""
    description: str = ""
    price: str = ""
    currency: str = "USD"
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    url: str = ""
    url_label: str = "Register"
    coordinates: Optional[Dict[str, float]] = None
    validation_errors: List[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []

class AdvancedEventParser:
    """Advanced event parser with comprehensive validation and geocoding"""
    
    def __init__(self):
        self.date_patterns = [
            # Full date patterns
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
            # Relative dates
            r'(?:today|tomorrow|yesterday)',
            r'(?:next|this)\s+(?:week|month|year)',
            r'(?:in\s+)?(\d+)\s+(?:days?|weeks?|months?)\s+(?:from\s+now)?',
            # ISO dates
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}'
        ]
        
        self.time_patterns = [
            r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)',
            r'\d{1,2}\s*(?:am|pm|AM|PM)',
            r'\d{1,2}:\d{2}',
            r'(?:noon|midnight)',
            r'(?:morning|afternoon|evening|night)'
        ]
        
        self.price_patterns = [
            r'\$\s*\d+(?:\.\d{2})?(?:\s*-\s*\$\s*\d+(?:\.\d{2})?)?',
            r'(?:free|Free|FREE)',
            r'(?:donation|Donation|DONATION)',
            r'(?:suggested\s+donation|Suggested\s+Donation)',
            r'\d+(?:\.\d{2})?\s*(?:dollars?|USD|usd)',
            r'(?:pay\s+what\s+you\s+can|Pay\s+What\s+You\s+Can)'
        ]
        
        self.location_patterns = [
            r'(?:at|@|in)\s+([A-Z][A-Za-z\s&\',\-\.]+(?:Center|Theater|Theatre|Museum|Library|Park|Hall|Arena|Stadium|Club|Bar|Restaurant|Cafe|Gallery|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue|Building|Plaza|Square|Mall|Market|Store|Shop))',
            r'(?:at|@|in)\s+([A-Z][A-Za-z\s&\',\-\.]+)',
            r'(?:venue|location|place):\s*([A-Z][A-Za-z\s&\',\-\.]+)'
        ]
        
        self.address_patterns = [
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct|Circle|Cir|Trail|Trl|Parkway|Pkwy)(?:\s*,\s*[A-Za-z\s]+)*,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?',
            r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Place|Pl|Court|Ct|Circle|Cir|Trail|Trl|Parkway|Pkwy)',
            r'(?:address|Address):\s*([A-Za-z0-9\s,.-]+)'
        ]
    
    def parse_event_text(self, text: str, url: str = "", url_label: str = "Register") -> ParsedEvent:
        """Parse unstructured event text into structured data"""
        logger.info("Starting advanced event parsing")
        
        # Initialize parsed event
        event = ParsedEvent()
        event.url = url
        event.url_label = url_label
        
        # Clean and normalize text
        cleaned_text = self._clean_text(text)
        
        # Extract components
        event.title = self._extract_title(cleaned_text)
        event.date = self._extract_date(cleaned_text)
        event.time, event.end_time = self._extract_time(cleaned_text)
        event.location_name = self._extract_location_name(cleaned_text)
        event.address = self._extract_address(cleaned_text)
        event.description = self._extract_description(cleaned_text)
        event.price, event.currency, event.price_min, event.price_max = self._extract_price(cleaned_text)
        
        # Geocode address if available
        if event.address:
            event.coordinates = self._geocode_address(event.address)
        
        # Validate and calculate confidence
        event.validation_errors = self._validate_event(event)
        event.confidence_score = self._calculate_confidence(event)
        
        logger.info(f"Parsing completed with confidence score: {event.confidence_score}")
        return event
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize input text"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might interfere
        text = re.sub(r'[^\w\s\.,!?@#$%&*()\-+=\[\]{}|\\:";\'<>/]', '', text)
        return text.strip()
    
    def _extract_title(self, text: str) -> str:
        """Extract event title using multiple strategies"""
        # Strategy 1: Look for title patterns
        title_patterns = [
            r'^([A-Z][A-Za-z\s&\',\-\.]{10,100})(?:\n|$)',
            r'(?:Event|Event Title|Title):\s*([A-Z][A-Za-z\s&\',\-\.]{10,100})',
            r'^([A-Z][A-Za-z\s&\',\-\.]+(?:book club|meeting|workshop|conference|seminar|lecture|talk|presentation|demo|tasting|tour|walk|run|race|game|match|performance|play|musical|dance|party|gala|fundraiser|auction|sale|market|fair|carnival|parade|celebration|ceremony|opening|launch|premiere|screening|film|movie|theater|theatre))',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                title = match.group(1).strip()
                if len(title) > 10 and len(title) < 100:
                    return title
        
        # Strategy 2: Use first line if it looks like a title
        first_line = text.split('\n')[0].strip()
        if len(first_line) > 10 and len(first_line) < 100 and first_line[0].isupper():
            return first_line
        
        # Strategy 3: Extract from common patterns
        if 'book club' in text.lower():
            match = re.search(r'([A-Z][A-Za-z\s&\',\-\.]+book club)', text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Untitled Event"
    
    def _extract_date(self, text: str) -> str:
        """Extract and normalize date"""
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                try:
                    # Parse relative dates
                    if 'today' in date_str.lower():
                        return datetime.now().strftime('%Y-%m-%d')
                    elif 'tomorrow' in date_str.lower():
                        return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    elif 'yesterday' in date_str.lower():
                        return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    # Parse absolute dates
                    parsed_date = dateutil.parser.parse(date_str)
                    return parsed_date.strftime('%Y-%m-%d')
                except:
                    continue
        
        return ""
    
    def _extract_time(self, text: str) -> Tuple[str, str]:
        """Extract start and end time"""
        time_matches = []
        for pattern in self.time_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                time_matches.append((match.start(), match.group(0)))
        
        if not time_matches:
            return "", ""
        
        # Sort by position in text
        time_matches.sort(key=lambda x: x[0])
        
        start_time = self._normalize_time(time_matches[0][1])
        end_time = ""
        
        # Look for end time patterns
        if len(time_matches) > 1:
            end_time = self._normalize_time(time_matches[1][1])
        elif ' - ' in text or ' to ' in text:
            # Look for time ranges
            range_pattern = r'(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)\s*(?:-|to)\s*(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)?)'
            match = re.search(range_pattern, text, re.IGNORECASE)
            if match:
                start_time = self._normalize_time(match.group(1))
                end_time = self._normalize_time(match.group(2))
        
        return start_time, end_time
    
    def _normalize_time(self, time_str: str) -> str:
        """Normalize time to 24-hour format"""
        time_str = time_str.strip()
        
        # Handle special cases
        if 'noon' in time_str.lower():
            return '12:00'
        elif 'midnight' in time_str.lower():
            return '00:00'
        
        # Parse standard time formats
        try:
            parsed_time = dateutil.parser.parse(time_str)
            return parsed_time.strftime('%H:%M')
        except:
            return time_str
    
    def _extract_location_name(self, text: str) -> str:
        """Extract location name"""
        for pattern in self.location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if len(location) > 3 and len(location) < 100:
                    return location
        
        return ""
    
    def _extract_address(self, text: str) -> str:
        """Extract full address"""
        for pattern in self.address_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                address = match.group(0).strip()
                if len(address) > 10:
                    return address
        
        return ""
    
    def _extract_description(self, text: str) -> str:
        """Extract event description"""
        # Remove title, date, time, location, and price to get description
        description = text
        
        # Remove common patterns
        patterns_to_remove = [
            r'^[A-Z][A-Za-z\s&\',\-\.]{10,100}(?:\n|$)',
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
            r'\d{1,2}:\d{2}\s*(?:am|pm|AM|PM)(?:\s*-\s*\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))?',
            r'(?:at|@|in)\s+[A-Z][A-Za-z\s&\',\-\.]+(?:Center|Theater|Theatre|Museum|Library|Park|Hall|Arena|Stadium|Club|Bar|Restaurant|Cafe|Gallery|Studio|Academy|School|University|College|Church|Temple|Mosque|Synagogue)',
            r'\$\s*\d+(?:\.\d{2})?(?:\s*-\s*\$\s*\d+(?:\.\d{2})?)?',
            r'(?:free|Free|FREE)',
        ]
        
        for pattern in patterns_to_remove:
            description = re.sub(pattern, '', description, flags=re.IGNORECASE)
        
        # Clean up
        description = re.sub(r'\s+', ' ', description).strip()
        
        # Return description if it's substantial
        if len(description) > 20:
            return description
        
        return ""
    
    def _extract_price(self, text: str) -> Tuple[str, str, Optional[float], Optional[float]]:
        """Extract price information"""
        for pattern in self.price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                price_str = match.group(0)
                
                if 'free' in price_str.lower():
                    return "Free", "USD", 0.0, 0.0
                elif 'donation' in price_str.lower():
                    return "Donation", "USD", None, None
                
                # Extract numeric values
                numbers = re.findall(r'\d+(?:\.\d{2})?', price_str)
                if numbers:
                    if len(numbers) == 1:
                        price = float(numbers[0])
                        return f"${price:.2f}", "USD", price, price
                    elif len(numbers) == 2:
                        price_min = float(numbers[0])
                        price_max = float(numbers[1])
                        return f"${price_min:.2f} - ${price_max:.2f}", "USD", price_min, price_max
        
        return "Free", "USD", 0.0, 0.0
    
    def _geocode_address(self, address: str) -> Optional[Dict[str, float]]:
        """Geocode address to get coordinates"""
        try:
            # Using a free geocoding service (you can replace with Google Maps API)
            response = requests.get(
                f"https://nominatim.openstreetmap.org/search",
                params={
                    'q': address,
                    'format': 'json',
                    'limit': 1
                },
                headers={'User-Agent': 'EventParser/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        'latitude': float(data[0]['lat']),
                        'longitude': float(data[0]['lon'])
                    }
        except Exception as e:
            logger.warning(f"Geocoding failed for address {address}: {str(e)}")
        
        return None
    
    def _validate_event(self, event: ParsedEvent) -> List[str]:
        """Validate parsed event data"""
        errors = []
        
        # Required fields
        if not event.title or len(event.title) < 3:
            errors.append("Event title is required and must be at least 3 characters")
        
        if not event.date:
            errors.append("Event date is required")
        
        if not event.time:
            errors.append("Event time is required")
        
        # URL validation
        if event.url:
            try:
                result = urlparse(event.url)
                if not all([result.scheme, result.netloc]):
                    errors.append("Invalid URL format")
            except:
                errors.append("Invalid URL format")
        
        # Date validation
        if event.date:
            try:
                datetime.strptime(event.date, '%Y-%m-%d')
            except:
                errors.append("Invalid date format")
        
        # Time validation
        if event.time:
            try:
                datetime.strptime(event.time, '%H:%M')
            except:
                errors.append("Invalid time format")
        
        return errors
    
    def _calculate_confidence(self, event: ParsedEvent) -> float:
        """Calculate confidence score for parsed event"""
        score = 0.0
        max_score = 10.0
        
        # Title (2 points)
        if event.title and len(event.title) > 5:
            score += 2.0
        
        # Date (2 points)
        if event.date:
            score += 2.0
        
        # Time (2 points)
        if event.time:
            score += 2.0
        
        # Location (1 point)
        if event.location_name:
            score += 1.0
        
        # Address (1 point)
        if event.address:
            score += 1.0
        
        # Description (1 point)
        if event.description and len(event.description) > 20:
            score += 1.0
        
        # Price (1 point)
        if event.price:
            score += 1.0
        
        return min(score / max_score, 1.0)
    
    def to_dict(self, event: ParsedEvent) -> Dict[str, Any]:
        """Convert ParsedEvent to dictionary"""
        return asdict(event)
    
    def to_json(self, event: ParsedEvent) -> str:
        """Convert ParsedEvent to JSON string"""
        return json.dumps(self.to_dict(event), indent=2, default=str)

# Example usage and testing
if __name__ == "__main__":
    parser = AdvancedEventParser()
    
    sample_text = """
    Read & Run on the Road book club
    
    Tuesday, September 16
    6:00pm - 8:00pm EDT
    
    The Exchange Saloon
    1719 G Street Northwest, Washington, DC 20006
    
    On this 3.3 mile run through the heart of Washington, D.C., we'll explore the city's rich literary history while discussing the latest book selection. This lighthearted book club combines fitness with literature, making it perfect for book lovers who want to stay active.
    
    Price: $10 - $25
    """
    
    result = parser.parse_event_text(sample_text, "https://example.com/register", "Register Now")
    print(parser.to_json(result))

