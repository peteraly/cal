# Event Calendar Web App

A mobile-first, ultraminimalist event calendar web app with a public view and an admin interface. Built with Flask + SQLite backend and Tailwind CSS + Alpine.js frontend.

## 🎯 **New Mobile-First Design**

The app now features a modern, mobile-first interface with four distinct views accessible via bottom navigation:

### **📄 Rolodex View (Default)**
- **Text-first approach**: Events displayed in a clean, vertical chronological list
- **Minimal information**: Shows only time, title, and location per row
- **Expandable cards**: Tap any event to reveal full details
- **Smart navigation**: Calendar view automatically returns to Rolodex when a date is selected

### **🗓️ Calendar View**
- **Month-by-month grid**: Standard calendar layout with visual event indicators
- **Event dots**: Clear visual markers on days with events
- **Seamless navigation**: Tapping a date returns to Rolodex view and scrolls to that day's events

### **📍 Map View**
- **Interactive map**: Shows all events with location data as pins
- **Event popups**: Tap pins to see event details and navigate back to full view
- **Location-based**: Only displays events that have location information

### **▶️ Feed/Reels View**
- **Video content**: Dedicated space for event-related video content
- **Full-screen experience**: Vertical feed optimized for mobile viewing
- **Future-ready**: Prepared for video integration and social features

## 🎨 **Design Principles**

- **Mobile-First**: Designed for smartphones, enhanced for larger screens
- **Ultra-Minimalist**: Clean, uncluttered interface focusing on content
- **Touch-Friendly**: All interactive elements optimized for finger navigation
- **Fast & Responsive**: Smooth animations and instant feedback
- **Accessible**: Proper contrast, focus states, and screen reader support

## Features

### Public View (`/`)
- Mini month-view calendar at the top
- **🔍 Natural Language Search**: Search events with queries like "meetings next week", "workshops in October"
- **🔔 Smart Subscriptions**: Follow events, hosts, venues, or tags without accounts
- Click on a date to load events below
- Event list shows time, title, location, host, price information, and description
- **AI-powered event highlighting** for important events
- **Smart tags** display for better organization
- Dots/markers on dates with events
- Month navigation
- Responsive design for desktop and mobile

### Admin Interface (`/admin`)
- Simple login page (username: admin, password: test)
- Same calendar layout as public view
- **🤖 AI-Powered Smart Entry**: Type natural language like "Team sync with Sam at 10am next Wednesday in Zoom"
- **📥 Bulk Import**: Import multiple events from news articles or event listings
- Add, edit, and delete events with **auto-generated tags**
- **Auto-summarize** event descriptions
- Modal forms for event management
- Session-based authentication

### AI Features
- **Natural Language Processing**: Parse event descriptions into structured data
- **Smart Tagging**: Automatically assign relevant tags (Meeting, Online, Work, etc.)
- **Auto-Summarization**: Generate descriptions for events
- **Intelligent Highlighting**: Mark important events with visual indicators
- **Analytics Dashboard**: View event statistics and patterns

## Tech Stack

- **Backend**: Python + Flask
- **Database**: SQLite
- **Frontend**: HTML + Tailwind CSS + Alpine.js
- **Authentication**: Flask sessions

## Installation & Setup

### Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

### Quick Start

1. **Clone or download the project**
   ```bash
   cd cal
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` file and set your preferred admin password and optional OpenAI API key:
   ```
   ADMIN_PASSWORD=test
   SECRET_KEY=your-secret-key-here
   OPENAI_API_KEY=your-openai-api-key-here  # Optional for AI features
   ```
   
   **Note**: The AI features work with or without an OpenAI API key. Without it, the app uses intelligent regex-based parsing.

5. **Run the application**
   ```bash
   # Option 1: Use the startup script (recommended)
   python run.py
   
   # Option 2: Run directly
   python app.py
   ```

6. **Open your browser**
   - **Public view**: http://localhost:5001
   - **Admin login**: http://localhost:5001/admin/login
   - **Admin stats**: http://localhost:5001/admin/stats
   - **Login credentials**: username: `admin`, password: `test`

## API Endpoints

### Public Endpoints
- `GET /` - Public calendar view
- `GET /api/events?month=9&year=2025` - Get events for a specific month
- `GET /api/events?date=YYYY-MM-DD` - Get events for a specific date
- `GET /api/events/search?q=query` - Search events with natural language
- `GET /api/subscriptions/events` - Get events based on subscription preferences
- `GET /api/subscriptions/suggestions` - Get available hosts, venues, and tags

### Admin Endpoints (Requires Authentication)
- `GET /admin` - Admin calendar view
- `GET /admin/stats` - Analytics dashboard
- `GET /admin/login` - Admin login page
- `POST /admin/login` - Process login
- `GET /admin/logout` - Logout
- `POST /api/events` - Create new event
- `PUT /api/events/<id>` - Update existing event
- `DELETE /api/events/<id>` - Delete event

### AI Endpoints (Requires Authentication)
- `POST /api/ai/parse-event` - Parse natural language into event data
- `POST /api/ai/suggest-recurrence` - Suggest recurring event patterns
- `POST /api/ai/analyze-importance` - Analyze event importance
- `GET /api/admin/stats` - Get analytics data

## Database Schema

The app uses SQLite with two main tables:

```sql
-- Categories table
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL
);

-- Events table with AI enhancements, subscriptions, and pricing
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_datetime TEXT NOT NULL,
    description TEXT,
    location TEXT,
    category_id INTEGER,
    tags TEXT,  -- JSON array of tags
    host TEXT,  -- Event host/organizer
    price_info TEXT,  -- Price information (Free, $25, Free; dog show $25)
    FOREIGN KEY (category_id) REFERENCES categories (id)
);
```

## Project Structure

```
cal/
├── app.py                 # Main Flask application
├── ai_parser.py          # AI-powered event parsing module
├── run.py                 # Startup script
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md             # This file
├── calendar.db           # SQLite database (created automatically)
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Public calendar view
│   ├── admin.html        # Admin calendar view
│   ├── admin_stats.html  # Analytics dashboard
│   └── login.html        # Admin login page
└── static/               # Static assets (CSS, JS)
    ├── css/
    └── js/
```

## Usage

### Public View
1. Visit http://localhost:5001
2. Use the month navigation arrows to browse different months
3. Click on any date to view events for that day
4. Events are displayed below the calendar with time, title, location, and description

### Admin Interface
1. Visit http://localhost:5001/admin
2. Login with username: `admin` and password: `test`
3. Use the same calendar interface as the public view
4. Click "Add Event" to create new events
5. Click "Edit" or "Delete" on existing events to manage them
6. Use the modal forms to add/edit event details

### Event Management
- **Title**: Required field for event name
- **Date**: Required field for event date
- **Time**: Required field for event time
- **Location**: Optional field for event location
- **Category**: Optional field to assign event to a category with color coding
- **Description**: Optional field for event description

### Categories
The app includes 6 default categories with color coding:
- **Work** (Blue) - Professional events and meetings
- **Personal** (Green) - Personal tasks and activities
- **Health** (Yellow) - Medical appointments and fitness
- **Travel** (Purple) - Trips and transportation
- **Social** (Red) - Social events and gatherings
- **Other** (Gray) - Miscellaneous events

Events with categories will display colored borders and category badges in both public and admin views.

## AI Features

### Smart Entry
Type natural language descriptions in the admin interface:
- "Team sync with Sam at 10am next Wednesday in Zoom"
- "Lunch with John tomorrow at 12:30pm"
- "Project deadline next Friday at 5pm"

The AI will automatically parse:
- **Title**: Extracted from the description
- **Date**: Parsed from relative terms (tomorrow, next Wednesday, etc.)
- **Time**: Extracted and converted to 24-hour format
- **Location**: Identified from context (Zoom, office, etc.)
- **Tags**: Auto-generated based on content (Meeting, Online, Work, etc.)
- **Description**: Auto-generated if not provided

### Intelligent Features
- **Auto-tagging**: Events are automatically tagged based on content
- **Importance Detection**: Events with keywords like "launch", "deadline", "urgent" are highlighted
- **Smart Suggestions**: Recurring event patterns are detected and suggested
- **Analytics**: View event patterns, popular times, and category distributions

### AI Configuration
The app works with or without an OpenAI API key:
- **With OpenAI**: Uses GPT-3.5 for advanced natural language processing
- **Without OpenAI**: Uses intelligent regex patterns and date parsing libraries

## Search Features

### Natural Language Search
The public calendar includes a powerful search bar that understands natural language queries:

**Date-based searches:**
- "events next week"
- "meetings this week" 
- "workshops in October"
- "events next Monday"

**Tag-based searches:**
- "zoom calls on Friday"
- "lunch meetings"
- "work events"
- "online workshops"

**Keyword searches:**
- "team sync"
- "project deadline"
- "client meetings"

**Time-based searches:**
- "morning meetings"
- "afternoon events"
- "evening workshops"

The search automatically parses your query and filters events by:
- **Keywords**: Searches in titles, descriptions, and locations
- **Tags**: Matches event tags (Meeting, Online, Work, etc.)
- **Date ranges**: Understands relative dates (next week, tomorrow, etc.)
- **Time ranges**: Filters by time of day (morning, afternoon, evening)
- **Locations**: Finds events at specific locations

## Subscription Features

### Smart Subscriptions (No Account Required)
The calendar includes a minimal subscription system that works entirely in the browser:

**Subscription Types:**
- **🔔 Event Subscriptions**: Follow specific events for updates
- **⭐ Host Subscriptions**: Follow all events by a particular host/organizer
- **🏢 Venue Subscriptions**: Follow all events at a specific location
- **🏷️ Tag Subscriptions**: Follow events with specific tags (e.g., "workshop", "music")

**How It Works:**
1. **Local Storage**: All subscriptions are stored in your browser's localStorage
2. **No Accounts**: No email or user registration required
3. **Instant Setup**: Click buttons on events to subscribe immediately
4. **Smart Suggestions**: Browse available hosts, venues, and tags to follow
5. **Visual Management**: See all your subscriptions in one place

**Usage:**
- Click "🔔 Follow Event" on any event to subscribe
- Click "⭐ Follow Host" to follow all events by that organizer
- Click "🏢 Follow Venue" to follow all events at that location
- Use the "Manage" button to browse and toggle subscriptions
- Subscriptions persist across browser sessions

**Data Structure:**
```javascript
{
  subscriptions: {
    event: [1, 2, 3],           // Event IDs
    host: ["John Smith", "Tech Meetup"],  // Host names
    venue: ["Conference Center", "Zoom"], // Venue names
    tag: ["workshop", "music"]   // Tag names
  }
}
```

## Pricing Information

### Smart Price Detection
The calendar automatically detects and displays pricing information for events:

**Price Display Logic:**
- **Free Events**: Shows "💰 Free" in green
- **Paid Events**: Shows "💰 $25" in blue  
- **Mixed Pricing**: Shows "💰 Free; dog show $25" for events with both free and paid components

**Examples:**
- `"Free admission"` → **Free**
- `"$25 per person"` → **$25**
- `"Free; dog show registration $25"` → **Free; $25**
- `"Tickets start at $35. Premium seating $75"` → **$35, $75**

**How It Works:**
1. **AI Parsing**: When using smart entry, the system automatically extracts price information from event descriptions
2. **Manual Entry**: Admins can manually specify pricing in the "Price Information" field
3. **Smart Detection**: The system uses regex patterns to find dollar amounts and "free" mentions
4. **Visual Display**: Price information is prominently displayed with color coding (green for free, blue for paid)

**Usage:**
- **For Admins**: Add pricing in the "Price Information" field when creating/editing events
- **For AI**: The system automatically detects pricing from natural language descriptions
- **For Visitors**: Price information is clearly displayed on each event

## Bulk Import Feature

### Smart Event Extraction
The calendar includes a powerful bulk import feature that can extract multiple events from structured text like news articles or event listings.

**How It Works:**
1. **Paste Text**: Copy and paste event information from articles, websites, or documents
2. **AI Extraction**: The system automatically identifies and separates individual events
3. **Preview & Edit**: Review extracted events before importing
4. **Bulk Import**: Import all events at once with automatic parsing

**Supported Formats:**
- News articles with date headers (e.g., "Thursday, Sept. 4")
- Event listings with clear titles and descriptions
- Structured text with time, location, and pricing information

**Example Usage:**
1. Go to Admin Interface → "Bulk Import" button
2. Paste text from a Washington Post "Things to Do" article
3. Click "Extract Events" to parse the content
4. Review the extracted events in the preview
5. Remove any unwanted events
6. Click "Import All Events" to add them to your calendar

**Features:**
- **Multiple Extraction Methods**: Choose from Enhanced (rule-based), Advanced (NLP), or AI-Powered (LLM) extraction
- **Smart Parsing**: Automatically extracts titles, dates, times, locations, and pricing
- **Preview Mode**: See exactly what will be imported before committing
- **Selective Import**: Remove individual events from the import list
- **Error Handling**: Clear feedback on successful and failed imports
- **Batch Processing**: Import multiple events efficiently
- **Fallback Mechanisms**: Automatically falls back to simpler methods if advanced ones fail

### Advanced Extraction Methods

#### Enhanced (Rule-based) - Default
- Fast, reliable pattern matching
- Works offline with no external dependencies
- Best for structured text with clear event boundaries

#### Advanced (NLP) - Optional
- Uses spaCy and NLTK for better language understanding
- Named Entity Recognition for dates, times, and locations
- Best for complex text with varied formatting
- Install with: `pip install -r requirements-advanced.txt`

#### AI-Powered (LLM) - Most Accurate
- Uses OpenAI GPT for semantic understanding
- Handles any text format with high accuracy
- Best for unstructured text and complex articles
- Requires OpenAI API key in `.env`

## Development

### Running in Development Mode
The app runs in debug mode by default when using `python app.py`. This enables:
- Auto-reload on code changes
- Detailed error messages
- Debug toolbar (if installed)

### Customization
- Modify `templates/` for UI changes
- Update `app.py` for backend logic
- Customize Tailwind classes for styling
- Add new API endpoints as needed

## Security Notes

- Change the default admin password in production
- Use a strong SECRET_KEY for session management
- Consider using environment variables for all sensitive data
- Implement proper password hashing for production use

## Troubleshooting

### Common Issues

1. **Port already in use**
   - The app is configured to run on port 5001 by default to avoid conflicts with macOS AirPlay
   - If needed, change the port in `app.py`: `app.run(debug=True, port=5002)`

2. **Database errors**
   - Delete `calendar.db` and restart the app to recreate the database

3. **Login not working**
   - Check your `.env` file has the correct `ADMIN_PASSWORD`
   - Ensure the `.env` file is in the project root

4. **Static files not loading**
   - Ensure you're using the CDN versions of Tailwind and Alpine.js (included in templates)

## License

This project is open source and available under the MIT License.
