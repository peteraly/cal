# 📡 RSS Feeds Management - Easy Setup Guide

## 🎯 What This Does
Your calendar now automatically imports events from RSS feeds! No technical knowledge required.

## 🚀 How to Start Everything (Super Easy!)

### Option 1: Simple Startup (Recommended)
```bash
python3 start_app.py
```
That's it! This starts everything automatically.

### Option 2: Manual Startup
```bash
source venv/bin/activate
python3 app.py
```

## 📱 Access Your RSS Feeds Dashboard
1. Go to: http://localhost:5001/admin/rss-feeds
2. Click "Add Feed" 
3. Enter an RSS URL (like: `https://www.washingtonian.com/tag/neighborhood-guide/feed/`)
4. Click "Add Feed" - that's it!

## ✨ What Happens Automatically
- ✅ RSS feeds check for new events every 15 minutes
- ✅ New events are added to your calendar automatically
- ✅ Duplicate events are prevented
- ✅ Manual changes to events are protected from being overwritten
- ✅ All activity is logged and visible in the dashboard

## 🔧 RSS Feeds Dashboard Features
- **Add/Remove Feeds**: Easy management of RSS sources
- **Health Status**: See which feeds are working or having issues
- **Activity Logs**: View all feed updates and any errors
- **Manual Refresh**: Force immediate updates if needed
- **Scheduler Status**: See when feeds will be checked next

## 📊 Example RSS Feeds to Try
- Washingtonian Events: `https://www.washingtonian.com/tag/neighborhood-guide/feed/`
- DCist Events: `https://dcist.com/feed/`
- Washington Post Events: `https://www.washingtonpost.com/events/feed/`

## 🛠️ Troubleshooting
- **"Virtual environment not found"**: Run `python3 -m venv venv` then `source venv/bin/activate`
- **"Module not found"**: Run `pip install -r requirements.txt`
- **Feeds not updating**: Check the RSS Feeds dashboard for error messages

## 💡 Pro Tips
1. Start with 1-2 feeds to test the system
2. Check the Activity Logs to see what's happening
3. Use "Refresh All" to force immediate updates
4. The scheduler runs automatically - no need to restart anything

## 🎉 You're All Set!
Your calendar will now stay updated with fresh events automatically. Just add RSS feeds and let the system do the work!

