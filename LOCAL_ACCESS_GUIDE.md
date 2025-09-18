# 🏠 Local Access Guide

## 🚀 **Quick Start - Local Access**

### **Method 1: Simple App (Recommended for Testing)**
```bash
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"
source venv/bin/activate
python3 start_simple_app.py
```

### **Method 2: Full App with RSS Features**
```bash
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"
source venv/bin/activate
python3 app.py
```

### **Method 3: Using Startup Scripts**
```bash
# Bash script
./start_calendar_app.sh

# Python script
python3 start_app.py
```

---

## 🌐 **Local Access URLs**

### **Main Application**
- **Public Calendar:** http://localhost:5001
- **Admin Login:** http://localhost:5001/admin/login
- **Admin Dashboard:** http://localhost:5001/admin

### **API Endpoints**
- **All Events:** http://localhost:5001/api/events
- **Categories:** http://localhost:5001/api/categories
- **Event Search:** http://localhost:5001/api/events/search

### **Admin Features (Full App Only)**
- **RSS Feeds:** http://localhost:5001/admin/rss-feeds
- **Admin Table:** http://localhost:5001/admin/table
- **Admin Stats:** http://localhost:5001/admin/stats

---

## 🔐 **Admin Access**

### **Login Credentials**
- **Username:** admin
- **Password:** admin123

### **Admin Features Available:**
- ✅ Add/Edit/Delete Events
- ✅ Bulk Import Events
- ✅ Event Categories Management
- ✅ RSS Feed Management (Full App)
- ✅ Event Statistics
- ✅ Data Export/Import

---

## 📱 **Testing Local Access**

### **1. Test Main Page**
```bash
curl http://localhost:5001
```

### **2. Test API**
```bash
curl http://localhost:5001/api/events
```

### **3. Test Admin Redirect**
```bash
curl http://localhost:5001/admin
```

### **4. Browser Testing**
Open your browser and navigate to:
- http://localhost:5001
- http://localhost:5001/admin

---

## 🔧 **Troubleshooting Local Access**

### **Issue: "Connection Refused"**
**Solution:**
```bash
# Check if app is running
ps aux | grep "python3.*app.py"

# If not running, start it
source venv/bin/activate
python3 start_simple_app.py
```

### **Issue: "Module Not Found"**
**Solution:**
```bash
# Make sure you're in the right directory
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **Issue: "Port Already in Use"**
**Solution:**
```bash
# Kill existing processes
pkill -f "python3.*app.py"

# Or use a different port
python3 start_simple_app.py  # Will use port 5001
```

---

## 📊 **Local vs Production**

### **Local Development (localhost:5001)**
- ✅ Full admin access
- ✅ Database editing
- ✅ Debug mode enabled
- ✅ Hot reloading
- ✅ All features available

### **Production (Vercel)**
- ✅ Public calendar view
- ✅ Read-only access
- ✅ Optimized performance
- ✅ HTTPS enabled
- ⚠️ Limited admin features

---

## 🎯 **Quick Commands**

### **Start Local App**
```bash
# Simple version (fastest)
python3 start_simple_app.py

# Full version (all features)
python3 app.py
```

### **Stop Local App**
```bash
# Press Ctrl+C in the terminal
# Or kill the process
pkill -f "python3.*app.py"
```

### **Check App Status**
```bash
# Check if running
curl -s http://localhost:5001 | head -5

# Check processes
ps aux | grep "python3.*app.py"
```

---

## 📋 **Local Access Checklist**

- ✅ App starts without errors
- ✅ Main page loads at http://localhost:5001
- ✅ Admin login works at http://localhost:5001/admin
- ✅ API returns data at http://localhost:5001/api/events
- ✅ Database is accessible and populated
- ✅ All templates load correctly
- ✅ Static files (CSS/JS) load properly

---

## 🚀 **Next Steps**

1. **Test all local URLs** to ensure everything works
2. **Add some test events** through the admin interface
3. **Verify data persistence** by restarting the app
4. **Test all admin features** (add, edit, delete events)
5. **Check mobile responsiveness** on different screen sizes

Your local calendar app is now fully accessible and ready for development! 🎉
