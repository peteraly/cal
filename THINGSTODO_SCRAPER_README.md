# 🎯 ThingsToDo DC Scraper

## Overview

The ThingsToDo DC Scraper is a specialized web scraping tool designed to extract structured event data from individual event pages on `thingstododc.com`. This scraper is integrated into the main scraper system and automatically detects thingstododc.com URLs to use the specialized parsing logic.

## 🚀 Features

### **Specialized Event Extraction**
- **Title Extraction**: Intelligently extracts event titles, with fallback to URL slug parsing
- **Date/Time Parsing**: Handles complex date/time formats like "Tue, September 16, 2025 @ 07:30PM To Tue, September 16, 2025 @ 09:00PM"
- **Location Detection**: Extracts venue information and handles both physical and virtual locations
- **Price Extraction**: Parses pricing information including free events
- **Description Processing**: Cleans and extracts event descriptions while filtering out unwanted content

### **Smart Data Processing**
- **URL Slug Fallback**: If HTML title extraction fails, generates readable titles from URL slugs
- **Content Filtering**: Removes navigation elements, buttons, and non-event content
- **Data Normalization**: Converts dates to YYYY-MM-DD format and times to HH:MM:SS format
- **Error Handling**: Graceful handling of missing or malformed data

## 📋 Supported Data Fields

| Field | Description | Format | Example |
|-------|-------------|---------|---------|
| `title` | Event title | String | "Virtual Guided Nature Tour of Costa Rica" |
| `start_date` | Event start date | YYYY-MM-DD | "2025-09-16" |
| `end_date` | Event end date | YYYY-MM-DD | "2025-09-16" |
| `start_time` | Event start time | HH:MM:SS | "19:30:00" |
| `end_time` | Event end time | HH:MM:SS | "21:00:00" |
| `location` | Event location | String | "601 New Hampshire Avenue, NW Washington, DC" |
| `price` | Event price | Float | 20.0 |
| `description` | Event description | String | "Join us for a virtual tour..." |
| `url` | Source URL | String | "https://thingstododc.com/event/..." |
| `source` | Data source | String | "thingstododc.com" |

## 🔧 Usage

### **Direct Usage**

```python
from thingstodo_scraper import scrape_thingstodo_event

# Scrape a single event
url = "https://thingstododc.com/event/virtual-guided-nature-tour-of-costa-rica-4/"
result = scrape_thingstodo_event(url)

print(result)
```

### **Integrated Usage**

The scraper is automatically integrated into the main scraper system. When you add a thingstododc.com URL to the monitored URLs, it will automatically use the specialized scraper:

```python
from scraper_service import ScraperService

scraper = ScraperService()

# Check if URL is supported
if scraper.is_thingstodo_url(url):
    events = scraper.scrape_thingstodo_event(url)
```

### **API Usage**

Test the scraper via the admin API:

```bash
curl -X POST http://localhost:5001/api/scraper/test-thingstodo \
  -H "Content-Type: application/json" \
  -H "Cookie: session=your_session_cookie" \
  -d '{"url": "https://thingstododc.com/event/your-event-slug/"}'
```

## 🎯 URL Format Support

The scraper supports URLs in the following format:
- `https://thingstododc.com/event/[event-slug]/`
- `http://thingstododc.com/event/[event-slug]/`

## 🔍 Extraction Logic

### **Title Extraction**
1. **Primary**: Look for specific CSS selectors (`.event-title`, `h1`, etc.)
2. **Filtering**: Remove common non-title elements (RSVP, Register, etc.)
3. **Fallback**: Extract title from URL slug if HTML extraction fails

### **Date/Time Parsing**
1. **Pattern Matching**: Uses regex to find date/time strings
2. **Format Detection**: Handles various date/time formats
3. **Normalization**: Converts to standardized formats

### **Location Extraction**
1. **Selector Search**: Looks for location-specific CSS classes
2. **Text Analysis**: Searches for location indicators in content
3. **Cleaning**: Removes prefixes and normalizes text

### **Price Extraction**
1. **Pattern Matching**: Finds price patterns ($20, 20 dollars, etc.)
2. **Free Detection**: Identifies free events
3. **Numeric Conversion**: Converts to float values

## 🛠️ Configuration

### **Dependencies**
- `beautifulsoup4`: HTML parsing
- `requests`: HTTP requests
- `re`: Regular expressions
- `datetime`: Date/time handling

### **User Agent**
The scraper uses a realistic browser user agent to avoid blocking:
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36
```

## 🚨 Error Handling

The scraper includes comprehensive error handling:

- **Network Errors**: Timeout and connection error handling
- **Parsing Errors**: Graceful handling of malformed HTML
- **Missing Data**: Returns null/None for missing fields
- **Invalid URLs**: Validates URL format and accessibility

## 📊 Example Output

```json
{
  "title": "Virtual Guided Nature Tour of Costa Rica",
  "start_date": "2025-09-16",
  "end_date": "2025-09-16",
  "start_time": "19:30:00",
  "end_time": "21:00:00",
  "location": "601 New Hampshire Avenue, NW Washington, District Of Columbia",
  "price": 20.0,
  "description": null,
  "url": "https://thingstododc.com/event/virtual-guided-nature-tour-of-costa-rica-4/",
  "source": "thingstododc.com"
}
```

## 🔄 Integration with Main System

The ThingsToDo scraper is fully integrated with the main event management system:

1. **Automatic Detection**: URLs are automatically detected and routed to the specialized scraper
2. **Data Format**: Output is converted to the standard event format
3. **Duplicate Detection**: Uses the advanced event tracking system
4. **Database Storage**: Events are stored in the scraped_events table for review
5. **Admin Interface**: Can be managed through the admin dashboard

## 🎯 Best Practices

1. **URL Validation**: Always validate URLs before scraping
2. **Rate Limiting**: Respect the website's rate limits
3. **Error Monitoring**: Monitor for parsing errors and update selectors as needed
4. **Data Review**: Always review scraped events before approving them
5. **Regular Updates**: Update selectors if the website structure changes

## 🚀 Future Enhancements

- **Multi-page Support**: Support for event listing pages
- **Image Extraction**: Extract event images and media
- **Category Detection**: Automatically categorize events
- **Recurring Events**: Detect and handle recurring event patterns
- **Enhanced Filtering**: More sophisticated content filtering









