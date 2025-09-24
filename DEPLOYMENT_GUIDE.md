# 🚀 Deployment Guide - Simplified Calendar Application

## 📊 **Current Setup Summary**

### **RSS Feeds (8 active):**
- Washingtonian.com: `https://www.washingtonian.com/feed/`
- Washington Post feeds (6): Going Out Guide, Wizards, Nationals, Capitals, Commanders, Spirit, Terrapins

### **Web Scrapers (6 active):**
- **Brookings**: `https://www.brookings.edu/events/`
- **Cato Institute**: `https://www.cato.org/events/upcoming`
- **Pacers Running**: `https://runpacers.com/pages/events`
- **Smithsonian**: `https://www.si.edu/events`
- **DC Fray**: `https://districtfray.com/eventscalendar/?event_category=official-fray-events`
- **Volo Sports**: `https://www.volosports.com/discover?cityName=Washington%20DC&subView=LEAGUE&view=EVENTS`

## 🔄 **Automatic Updates**

### **Current Status:**
- ❌ **RSS Feeds**: Not running automatically (scheduler disabled)
- ❌ **Web Scrapers**: Not running automatically (scheduler disabled)

### **After Deployment:**
- ✅ **RSS Feeds**: Will refresh every 30 minutes automatically
- ✅ **Web Scrapers**: Will run every 2 hours automatically
- ✅ **Background Scheduler**: Enabled in production

## 🚀 **Deployment Options**

### **Option 1: Vercel (Recommended)**

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy:**
   ```bash
   vercel --prod
   ```

4. **Set Environment Variables in Vercel Dashboard:**
   - `SECRET_KEY`: Generate a secure random string
   - `ADMIN_PASSWORD`: Set your admin password
   - `ENABLE_SCHEDULER`: Set to `true`

### **Option 2: GitHub + Vercel Integration**

1. **Create GitHub Repository:**
   ```bash
   # Create repo on GitHub, then:
   git remote add origin https://github.com/yourusername/calendar-app.git
   git push -u origin main
   ```

2. **Connect to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel will auto-deploy on every push

### **Option 3: Local Production Server**

1. **Install Dependencies:**
   ```bash
   pip install -r requirements-vercel.txt
   ```

2. **Set Environment Variables:**
   ```bash
   export SECRET_KEY="your-secret-key"
   export ADMIN_PASSWORD="your-admin-password"
   export ENABLE_SCHEDULER="true"
   ```

3. **Run:**
   ```bash
   python app.py
   ```

## 🔧 **Environment Variables**

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Flask session secret | `your-super-secret-key-here` |
| `ADMIN_PASSWORD` | Admin login password | `your-admin-password` |
| `ENABLE_SCHEDULER` | Enable background scheduler | `true` |

## 📱 **Access URLs**

- **Public Calendar**: `https://your-app.vercel.app/`
- **Admin Dashboard**: `https://your-app.vercel.app/admin`
- **Admin Login**: `admin` / `[your-admin-password]`

## 🔄 **Automatic Updates After Deployment**

Once deployed with `ENABLE_SCHEDULER=true`:

### **RSS Feeds:**
- ✅ Check every 30 minutes for new events
- ✅ Automatically add new events to calendar
- ✅ Prevent duplicate events
- ✅ Log all activity

### **Web Scrapers:**
- ✅ Run every 2 hours
- ✅ Extract events from 6 websites
- ✅ Handle rate limiting and errors
- ✅ Update existing events

## 🛠️ **Monitoring & Maintenance**

### **Check Status:**
- Visit admin dashboard to see RSS feed status
- Check logs for any errors
- Monitor event counts

### **Manual Refresh:**
- Use "Refresh All" button in admin dashboard
- Or call API endpoints directly

### **Troubleshooting:**
- Check Vercel function logs
- Verify environment variables
- Test RSS feeds manually

## 🎯 **Recommendations**

### **For Production:**
1. **Use Vercel Pro** for better performance and reliability
2. **Set up monitoring** with Vercel Analytics
3. **Use a proper database** (PostgreSQL) for better performance
4. **Implement proper job queue** (Redis + Celery) for scheduling

### **For Development:**
1. **Keep local version** for testing
2. **Use environment variables** for configuration
3. **Test RSS feeds** before deploying
4. **Monitor logs** regularly

## 🚨 **Important Notes**

- **Database**: Currently uses SQLite (file-based)
- **Scheduling**: Basic threading (not production-grade)
- **Rate Limiting**: Respects website rate limits
- **Error Handling**: Graceful degradation on failures

## 🎉 **You're Ready to Deploy!**

Your simplified calendar application is now ready for deployment with:
- ✅ Clean, maintainable code
- ✅ Automatic RSS feed updates
- ✅ Web scraper integration
- ✅ Production-ready configuration
- ✅ Comprehensive documentation
