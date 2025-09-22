# Quick Start: Admin Approval System Implementation

## 🚀 **Immediate Implementation Steps**

### Step 1: Database Changes (5 minutes)
```sql
-- Run these SQL commands in your database
ALTER TABLE events ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE events ADD COLUMN approved_by INTEGER;
ALTER TABLE events ADD COLUMN approved_at DATETIME;
ALTER TABLE events ADD COLUMN rejection_reason TEXT;

-- Update existing events to approved (so they don't disappear)
UPDATE events SET approval_status = 'approved' WHERE approval_status IS NULL;
```

### Step 2: Update Event Processing (10 minutes)

#### Modify `web_scraper_manager.py`
```python
# In _process_scraped_event method, add:
event_data['approval_status'] = 'pending'
```

#### Modify `rss_manager.py`
```python
# In _process_rss_event method, add:
event_data['approval_status'] = 'pending'
```

### Step 3: Add API Endpoints (15 minutes)

#### Add to `app.py`
```python
@app.route('/api/admin/events/pending', methods=['GET'])
@admin_required
def get_pending_events():
    """Get all events pending approval"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM events 
        WHERE approval_status = 'pending' 
        ORDER BY created_at DESC
    """)
    
    events = []
    for row in cursor.fetchall():
        events.append(dict(zip([col[0] for col in cursor.description], row)))
    
    conn.close()
    return jsonify(events)

@app.route('/api/admin/events/<int:event_id>/approve', methods=['POST'])
@admin_required
def approve_event(event_id):
    """Approve a specific event"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE events 
        SET approval_status = 'approved', 
            approved_at = CURRENT_TIMESTAMP,
            approved_by = ?
        WHERE id = ?
    """, (session.get('user_id'), event_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Event approved'})

@app.route('/api/admin/events/<int:event_id>/reject', methods=['POST'])
@admin_required
def reject_event(event_id):
    """Reject a specific event"""
    data = request.get_json()
    reason = data.get('reason', '')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE events 
        SET approval_status = 'rejected', 
            approved_at = CURRENT_TIMESTAMP,
            approved_by = ?,
            rejection_reason = ?
        WHERE id = ?
    """, (session.get('user_id'), reason, event_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Event rejected'})
```

### Step 4: Update Public Events API (2 minutes)

#### Modify existing `/api/events` endpoint in `app.py`
```python
@app.route('/api/events', methods=['GET'])
def get_public_events():
    """Get events for public display - ONLY approved events"""
    # ... existing code ...
    
    # Add this filter to your existing query:
    # WHERE approval_status = 'approved' OR approval_status IS NULL
    
    # Or if you want to be strict:
    # WHERE approval_status = 'approved'
```

### Step 5: Create Simple Admin Approval Page (20 minutes)

#### Create `templates/admin_approval.html`
```html
{% extends "base.html" %}

{% block content %}
<div class="container mx-auto px-4 py-8">
    <h1 class="text-3xl font-bold mb-6">📋 Event Approval Queue</h1>
    
    <div id="pending-events" class="space-y-4">
        <!-- Events will be loaded here -->
    </div>
</div>

<script>
async function loadPendingEvents() {
    try {
        const response = await fetch('/api/admin/events/pending');
        const events = await response.json();
        
        const container = document.getElementById('pending-events');
        container.innerHTML = '';
        
        events.forEach(event => {
            const eventCard = createEventCard(event);
            container.appendChild(eventCard);
        });
    } catch (error) {
        console.error('Error loading pending events:', error);
    }
}

function createEventCard(event) {
    const div = document.createElement('div');
    div.className = 'bg-white border rounded-lg p-4 shadow';
    div.innerHTML = `
        <div class="flex justify-between items-start">
            <div class="flex-1">
                <h3 class="text-lg font-semibold">${event.title}</h3>
                <p class="text-gray-600">${event.start_datetime}</p>
                <p class="text-gray-600">${event.location_name}</p>
                <p class="text-sm text-gray-500 mt-2">${event.description?.substring(0, 200)}...</p>
            </div>
            <div class="flex space-x-2 ml-4">
                <button onclick="approveEvent(${event.id})" 
                        class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                    ✅ Approve
                </button>
                <button onclick="rejectEvent(${event.id})" 
                        class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
                    ❌ Reject
                </button>
            </div>
        </div>
    `;
    return div;
}

async function approveEvent(eventId) {
    try {
        const response = await fetch(`/api/admin/events/${eventId}/approve`, {
            method: 'POST'
        });
        
        if (response.ok) {
            loadPendingEvents(); // Reload the list
            alert('Event approved!');
        }
    } catch (error) {
        console.error('Error approving event:', error);
    }
}

async function rejectEvent(eventId) {
    const reason = prompt('Reason for rejection (optional):');
    
    try {
        const response = await fetch(`/api/admin/events/${eventId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        });
        
        if (response.ok) {
            loadPendingEvents(); // Reload the list
            alert('Event rejected!');
        }
    } catch (error) {
        console.error('Error rejecting event:', error);
    }
}

// Load events when page loads
document.addEventListener('DOMContentLoaded', loadPendingEvents);
</script>
{% endblock %}
```

### Step 6: Add Route for Approval Page (2 minutes)

#### Add to `app.py`
```python
@app.route('/admin/approval')
@admin_required
def admin_approval():
    """Admin event approval page"""
    return render_template('admin_approval.html')
```

### Step 7: Add to Admin Navigation (2 minutes)

#### Update admin navigation in your base template
```html
<!-- Add this to your admin navigation -->
<a href="/admin/approval" class="nav-link">
    📋 Approval Queue
    <span id="pending-count" class="badge">0</span>
</a>
```

## 🎯 **Testing the Implementation**

### 1. Test New Event Approval
1. Add a new web scraper or RSS feed
2. Trigger a scrape
3. Check that new events show as "pending"
4. Go to `/admin/approval`
5. Approve/reject events
6. Verify approved events appear on public site

### 2. Test Existing Events
1. Existing events should still appear (they're auto-approved)
2. New events should require approval

## 🔧 **Quick Customizations**

### Auto-approve Trusted Sources
```python
# In your event processing, add:
trusted_sources = ['aspeninstitute.org', 'brookings.edu']
if any(trusted in event_data.get('url', '') for trusted in trusted_sources):
    event_data['approval_status'] = 'approved'
else:
    event_data['approval_status'] = 'pending'
```

### Add Pending Count Badge
```javascript
// Add this to your admin dashboard
async function updatePendingCount() {
    const response = await fetch('/api/admin/events/pending/count');
    const data = await response.json();
    document.getElementById('pending-count').textContent = data.count;
}

// Update every 30 seconds
setInterval(updatePendingCount, 30000);
```

## ⚡ **Total Implementation Time: ~1 Hour**

This quick implementation gives you:
- ✅ All new events require approval
- ✅ Simple admin approval interface
- ✅ Approve/reject functionality
- ✅ Public site only shows approved events
- ✅ Basic audit trail

You can enhance it later with bulk operations, email notifications, and more advanced features!
