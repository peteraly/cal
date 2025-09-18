# 🔧 Troubleshooting Guide

## 🚀 **Quick Start (Recommended)**

### **Method 1: Use the Startup Script (Easiest)**
```bash
./start_calendar_app.sh
```

### **Method 2: Use Python Startup Script**
```bash
python3 start_app.py
```

### **Method 3: Manual Start (If scripts fail)**
```bash
# Navigate to project directory
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"

# Activate virtual environment
source venv/bin/activate

# Start the app
python3 app.py
```

---

## 🐛 **Common Issues & Solutions**

### **Issue 1: "ModuleNotFoundError: No module named 'flask'"**

**Cause:** Not using the virtual environment or Flask not installed

**Solution:**
```bash
# Make sure you're in the project directory
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify Flask is working
python3 -c "import flask; print('Flask version:', flask.__version__)"
```

### **Issue 2: "No such file or directory: 'app.py'"**

**Cause:** Wrong directory

**Solution:**
```bash
# Navigate to the correct directory
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"

# Verify you're in the right place
ls -la app.py
```

### **Issue 3: "ERR_CONNECTION_REFUSED" in Browser**

**Cause:** App not running or wrong port

**Solutions:**
1. **Check if app is running:**
   ```bash
   ps aux | grep "python3 app.py"
   ```

2. **Check the correct URL:**
   - http://localhost:5001
   - http://127.0.0.1:5001

3. **Restart the app:**
   ```bash
   # Stop any running instances
   pkill -f "python3 app.py"
   
   # Start fresh
   ./start_calendar_app.sh
   ```

### **Issue 4: Virtual Environment Issues**

**Cause:** Virtual environment corrupted or missing

**Solution:**
```bash
# Remove old virtual environment
rm -rf venv

# Create new one
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **Issue 5: Permission Denied on Startup Script**

**Cause:** Script not executable

**Solution:**
```bash
chmod +x start_calendar_app.sh
```

---

## 🔍 **Diagnostic Commands**

### **Check System Status**
```bash
# Check Python version
python3 --version

# Check if virtual environment exists
ls -la venv/

# Check if Flask is installed
source venv/bin/activate && python3 -c "import flask; print(flask.__version__)"

# Check if app is running
ps aux | grep "python3 app.py"

# Test app connectivity
curl -s http://localhost:5001 | head -5
```

### **Check Project Structure**
```bash
# Verify all essential files exist
ls -la app.py requirements.txt calendar.db

# Check templates
ls -la templates/

# Check static files
ls -la static/
```

---

## 🚨 **Emergency Recovery**

### **If Everything is Broken**
```bash
# 1. Navigate to project directory
cd "/Users/alyssapeterson/Library/Mobile Documents/com~apple~CloudDocs/cal"

# 2. Check if backup exists
ls -la backup_*/

# 3. Restore from backup if needed
cp backup_*/app.py .
cp backup_*/requirements.txt .

# 4. Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Start the app
python3 app.py
```

---

## 📱 **Accessing Your App**

### **Local Access**
- **Main App:** http://localhost:5001
- **Admin Panel:** http://localhost:5001/admin
- **RSS Feeds:** http://localhost:5001/admin/rss-feeds

### **Network Access (if needed)**
- **From other devices:** http://[YOUR_IP]:5001
- **Find your IP:** `ifconfig | grep "inet " | grep -v 127.0.0.1`

---

## 🔄 **Maintenance Commands**

### **Weekly Cleanup**
```bash
python3 maintenance_script.py
```

### **Update Dependencies**
```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### **Check App Health**
```bash
python3 diagnostic.py
```

---

## 📞 **Getting Help**

### **If You're Still Stuck**
1. **Run the diagnostic script:**
   ```bash
   python3 diagnostic.py
   ```

2. **Check the logs:**
   ```bash
   tail -f rss_scheduler.log
   ```

3. **Verify all files are present:**
   ```bash
   ls -la
   ```

### **Key Files to Check**
- ✅ `app.py` - Main application
- ✅ `requirements.txt` - Dependencies
- ✅ `calendar.db` - Database
- ✅ `venv/` - Virtual environment
- ✅ `templates/` - HTML templates
- ✅ `static/` - CSS/JS files

---

## 🎯 **Success Indicators**

### **App is Working When:**
- ✅ No error messages in terminal
- ✅ Browser shows calendar at http://localhost:5001
- ✅ Admin panel accessible at http://localhost:5001/admin
- ✅ RSS feeds page loads at http://localhost:5001/admin/rss-feeds

### **Common Success Messages:**
```
Starting RSS feed scheduler...
RSS scheduler started successfully!
 * Running on http://127.0.0.1:5001
 * Debug mode: on
```
