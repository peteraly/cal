# 📁 Project Structure Documentation

## 🎯 **Current Project: Calendar Application**

### **Core Application Files**
```
app.py                    # Main Flask application
rss_manager.py           # RSS feed management system
rss_scheduler.py         # Background task scheduler
calendar.db              # SQLite database
requirements.txt         # Python dependencies
vercel.json             # Deployment configuration
```

### **Templates (Frontend)**
```
templates/
├── admin.html           # Admin dashboard
├── admin_new.html       # New admin interface
├── admin_table.html     # Admin table view
├── base.html           # Base template
├── index.html          # Home page
├── login.html          # Login page
├── public.html         # Public calendar view
└── rss_feeds.html      # RSS feeds management
```

### **Static Assets**
```
static/
├── css/
│   └── mobile.css      # Mobile styles
└── js/                 # JavaScript files
```

### **Documentation**
```
README.md               # Main project documentation
RSS_FEEDS_README.md     # RSS system documentation
THINGSTODO_SCRAPER_README.md  # Scraper documentation
PROJECT_STRUCTURE.md    # This file
```

### **Scripts (Organized)**
```
scripts/
├── create_full_wp_file.py
├── import_all_wp_events.py
├── import_wp_events.py
└── import_wp_final.py
```

### **Utilities**
```
cleanup_project.py      # One-time cleanup script
maintenance_script.py   # Ongoing maintenance
diagnostic.py          # System diagnostics
```

## 🗑️ **Files to Remove**

### **Test/Startup Scripts (Redundant)**
- `quick_start.py`
- `simple_test.py`
- `start_app.py`
- `start_now.py`
- `start_simple.py`
- `test_app.py`

### **Cache Files**
- `__pycache__/` directories
- `*.pyc` files
- `rss_scheduler.log`

### **System Files**
- `.DS_Store`
- `Thumbs.db`
- `*.tmp`, `*.bak` files

## 📦 **Backup Strategy**

### **Critical Files to Backup**
1. **Database**: `calendar.db`
2. **Core Code**: `app.py`, `rss_manager.py`, `rss_scheduler.py`
3. **Configuration**: `requirements.txt`, `vercel.json`
4. **Templates**: All files in `templates/`
5. **Documentation**: All `.md` files

### **Backup Location**
- `backup_YYYYMMDD_HHMMSS/` directory
- Timestamped for easy identification

## 🔄 **Maintenance Schedule**

### **Daily**
- Run `maintenance_script.py` to clean temp files
- Check for new log files

### **Weekly**
- Review and clean old log files
- Check disk usage
- Update dependencies if needed

### **Monthly**
- Full project cleanup
- Archive old backups
- Review file structure

## 🚀 **Deployment Files**

### **Production**
- `vercel.json` - Vercel deployment config
- `requirements.txt` - Python dependencies
- `app.py` - Main application

### **Development**
- `diagnostic.py` - System diagnostics
- `maintenance_script.py` - Maintenance tools

## 📋 **File Naming Conventions**

### **Python Files**
- `app.py` - Main application
- `*_manager.py` - Management classes
- `*_scheduler.py` - Background tasks
- `*_parser.py` - Data parsing
- `*_service.py` - Service classes

### **Templates**
- `admin_*.html` - Admin interfaces
- `base.html` - Base template
- `index.html` - Home page
- `public.html` - Public pages

### **Documentation**
- `README.md` - Main documentation
- `*_README.md` - Feature-specific docs
- `PROJECT_STRUCTURE.md` - This file

## 🔧 **Tools and Scripts**

### **Cleanup Tools**
- `cleanup_project.py` - One-time cleanup
- `maintenance_script.py` - Ongoing maintenance

### **Diagnostic Tools**
- `diagnostic.py` - System health check

### **Development Tools**
- Virtual environment in `venv/`
- Git for version control
- Vercel for deployment
