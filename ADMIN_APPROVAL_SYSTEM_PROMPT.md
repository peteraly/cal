# Admin Approval System for New Events - Implementation Prompt

## 🎯 **Objective**
Implement a comprehensive admin approval system that requires manual review and approval of ALL new events before they appear on the public-facing website, regardless of source (web scrapers, RSS feeds, manual additions, etc.).

## 🔧 **Required Implementation**

### 1. **Database Schema Changes**

#### Add Approval Status Column
```sql
-- Add approval status to events table
ALTER TABLE events ADD COLUMN approval_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE events ADD COLUMN approved_by INTEGER;
ALTER TABLE events ADD COLUMN approved_at DATETIME;
ALTER TABLE events ADD COLUMN rejection_reason TEXT;

-- Create approval status enum
-- Values: 'pending', 'approved', 'rejected', 'auto_approved'
```

#### Create Admin Approval Log Table
```sql
CREATE TABLE IF NOT EXISTS event_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    admin_user_id INTEGER,
    action VARCHAR(20) NOT NULL, -- 'approve', 'reject', 'auto_approve'
    reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events (id),
    FOREIGN KEY (admin_user_id) REFERENCES users (id)
);
```

### 2. **Backend API Endpoints**

#### New API Routes in `app.py`
```python
# Admin approval endpoints
@app.route('/api/admin/events/pending', methods=['GET'])
def get_pending_events():
    """Get all events pending approval"""
    # Return events with approval_status = 'pending'
    
@app.route('/api/admin/events/<int:event_id>/approve', methods=['POST'])
def approve_event(event_id):
    """Approve a specific event"""
    # Update event approval_status to 'approved'
    # Log approval action
    
@app.route('/api/admin/events/<int:event_id>/reject', methods=['POST'])
def reject_event(event_id):
    """Reject a specific event"""
    # Update event approval_status to 'rejected'
    # Log rejection with reason
    
@app.route('/api/admin/events/bulk-approve', methods=['POST'])
def bulk_approve_events():
    """Bulk approve multiple events"""
    # Approve multiple events at once
    
@app.route('/api/admin/events/bulk-reject', methods=['POST'])
def bulk_reject_events():
    """Bulk reject multiple events"""
    # Reject multiple events at once

# Modified existing endpoints
@app.route('/api/events', methods=['GET'])
def get_public_events():
    """Get events for public display - ONLY approved events"""
    # Filter to only show approved events
    # WHERE approval_status = 'approved'
```

### 3. **Event Processing Modifications**

#### Update Web Scraper Manager
```python
# In web_scraper_manager.py
def _process_scraped_event(self, event_data, scraper_id):
    """Process scraped event with approval workflow"""
    # ... existing logic ...
    
    # Set default approval status to pending
    event_data['approval_status'] = 'pending'
    
    # Insert event with pending status
    # ... existing insert logic ...
    
    # Log that event needs approval
    logger.info(f"Event '{event_data['title']}' added and requires admin approval")
```

#### Update RSS Manager
```python
# In rss_manager.py
def _process_rss_event(self, event_data, feed_id):
    """Process RSS event with approval workflow"""
    # ... existing logic ...
    
    # Set default approval status to pending
    event_data['approval_status'] = 'pending'
    
    # Insert event with pending status
    # ... existing insert logic ...
```

### 4. **Admin Interface Components**

#### New Admin Page: Event Approval Dashboard
```html
<!-- templates/admin_event_approval.html -->
<div class="admin-approval-dashboard">
    <h2>📋 Event Approval Queue</h2>
    
    <!-- Statistics -->
    <div class="approval-stats">
        <div class="stat-card pending">
            <h3 id="pending-count">0</h3>
            <p>Pending Approval</p>
        </div>
        <div class="stat-card approved">
            <h3 id="approved-count">0</h3>
            <p>Approved Today</p>
        </div>
        <div class="stat-card rejected">
            <h3 id="rejected-count">0</h3>
            <p>Rejected Today</p>
        </div>
    </div>
    
    <!-- Bulk Actions -->
    <div class="bulk-actions">
        <button onclick="selectAll()">Select All</button>
        <button onclick="bulkApprove()" class="btn-approve">Approve Selected</button>
        <button onclick="bulkReject()" class="btn-reject">Reject Selected</button>
    </div>
    
    <!-- Event List -->
    <div class="pending-events-list">
        <!-- Dynamic list of pending events -->
    </div>
</div>
```

#### Event Approval Card Component
```html
<!-- Individual event approval card -->
<div class="event-approval-card" data-event-id="{{ event.id }}">
    <div class="event-preview">
        <h4>{{ event.title }}</h4>
        <p><strong>Date:</strong> {{ event.start_datetime }}</p>
        <p><strong>Location:</strong> {{ event.location_name }}</p>
        <p><strong>Source:</strong> {{ event.source_type }}</p>
        <p><strong>Description:</strong> {{ event.description[:200] }}...</p>
    </div>
    
    <div class="approval-actions">
        <button onclick="approveEvent({{ event.id }})" class="btn-approve">
            ✅ Approve
        </button>
        <button onclick="rejectEvent({{ event.id }})" class="btn-reject">
            ❌ Reject
        </button>
        <button onclick="viewEventDetails({{ event.id }})" class="btn-view">
            👁️ View Details
        </button>
    </div>
    
    <div class="rejection-reason" style="display: none;">
        <textarea placeholder="Reason for rejection (optional)"></textarea>
        <button onclick="confirmReject({{ event.id }})">Confirm Rejection</button>
    </div>
</div>
```

### 5. **Frontend JavaScript Functions**

#### Approval Management Functions
```javascript
// Event approval functions
async function approveEvent(eventId) {
    try {
        const response = await fetch(`/api/admin/events/${eventId}/approve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            removeEventFromList(eventId);
            updateApprovalStats();
            showNotification('Event approved successfully', 'success');
        }
    } catch (error) {
        showNotification('Error approving event', 'error');
    }
}

async function rejectEvent(eventId, reason = '') {
    try {
        const response = await fetch(`/api/admin/events/${eventId}/reject`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason })
        });
        
        if (response.ok) {
            removeEventFromList(eventId);
            updateApprovalStats();
            showNotification('Event rejected', 'info');
        }
    } catch (error) {
        showNotification('Error rejecting event', 'error');
    }
}

async function bulkApprove() {
    const selectedEvents = getSelectedEvents();
    if (selectedEvents.length === 0) {
        showNotification('Please select events to approve', 'warning');
        return;
    }
    
    try {
        const response = await fetch('/api/admin/events/bulk-approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_ids: selectedEvents })
        });
        
        if (response.ok) {
            removeSelectedEventsFromList();
            updateApprovalStats();
            showNotification(`${selectedEvents.length} events approved`, 'success');
        }
    } catch (error) {
        showNotification('Error bulk approving events', 'error');
    }
}
```

### 6. **Navigation Updates**

#### Add to Admin Menu
```html
<!-- In templates/base.html or admin navigation -->
<nav class="admin-nav">
    <a href="/admin">Dashboard</a>
    <a href="/admin/events">All Events</a>
    <a href="/admin/events/approval" class="approval-queue">
        📋 Approval Queue 
        <span class="pending-badge" id="pending-badge">0</span>
    </a>
    <a href="/admin/web-scrapers">Web Scrapers</a>
    <a href="/admin/rss-feeds">RSS Feeds</a>
</nav>
```

### 7. **Notification System**

#### Real-time Notifications
```javascript
// WebSocket or polling for new pending events
function checkForNewPendingEvents() {
    fetch('/api/admin/events/pending/count')
        .then(response => response.json())
        .then(data => {
            updatePendingBadge(data.count);
            if (data.count > 0) {
                showNotification(`${data.count} new events need approval`, 'info');
            }
        });
}

// Check every 30 seconds
setInterval(checkForNewPendingEvents, 30000);
```

### 8. **Email Notifications (Optional)**

#### Admin Email Alerts
```python
# In app.py or separate notification service
def send_approval_notification(event_count):
    """Send email to admin when new events need approval"""
    if event_count > 0:
        # Send email notification
        # Include link to approval dashboard
        pass
```

### 9. **Configuration Options**

#### Admin Settings
```python
# Configuration options
APPROVAL_SETTINGS = {
    'auto_approve_trusted_sources': False,  # Auto-approve from trusted sources
    'email_notifications': True,           # Send email alerts
    'approval_timeout_hours': 24,          # Auto-approve after X hours
    'max_pending_events': 100,             # Alert if too many pending
    'trusted_sources': [                   # Sources that can be auto-approved
        'aspeninstitute.org',
        'brookings.edu'
    ]
}
```

### 10. **Implementation Steps**

#### Phase 1: Database & Backend
1. ✅ Add approval columns to events table
2. ✅ Create event_approvals log table
3. ✅ Update event processing to set pending status
4. ✅ Create approval API endpoints
5. ✅ Modify public events API to filter approved only

#### Phase 2: Admin Interface
1. ✅ Create approval dashboard page
2. ✅ Add approval navigation menu
3. ✅ Implement approval/rejection functions
4. ✅ Add bulk operations
5. ✅ Create event preview cards

#### Phase 3: Notifications & Polish
1. ✅ Add real-time pending count updates
2. ✅ Implement email notifications
3. ✅ Add approval statistics
4. ✅ Create approval history log
5. ✅ Add search/filter for pending events

### 11. **Testing Checklist**

#### Functionality Tests
- [ ] New scraped events show as pending
- [ ] New RSS events show as pending
- [ ] Manually added events show as pending
- [ ] Approved events appear on public site
- [ ] Rejected events don't appear on public site
- [ ] Bulk approve/reject works correctly
- [ ] Approval statistics update correctly
- [ ] Email notifications send properly

#### User Experience Tests
- [ ] Approval queue loads quickly
- [ ] Event previews show all necessary info
- [ ] Approval actions are intuitive
- [ ] Bulk operations work smoothly
- [ ] Navigation shows pending count
- [ ] Mobile interface works well

### 12. **Security Considerations**

#### Admin Access Control
```python
# Ensure only admins can access approval functions
@app.route('/api/admin/events/<int:event_id>/approve', methods=['POST'])
@admin_required
def approve_event(event_id):
    # ... approval logic ...
```

#### Audit Trail
```python
# Log all approval actions
def log_approval_action(event_id, action, admin_id, reason=None):
    """Log approval action for audit trail"""
    # Insert into event_approvals table
```

## 🚀 **Expected Results**

### **Before Implementation**
- All events appear immediately on public site
- No quality control or filtering
- Potential for spam or inappropriate events

### **After Implementation**
- All events require admin approval
- Quality control and filtering
- Clean, curated event listings
- Audit trail of all approvals
- Real-time notifications for new events
- Bulk operations for efficiency

## 📋 **Admin Workflow**

1. **New Event Detected** → Event added with `approval_status = 'pending'`
2. **Admin Notification** → Email/UI notification of new pending events
3. **Admin Review** → Admin reviews event details in approval dashboard
4. **Admin Decision** → Approve, reject, or request more info
5. **Event Status Update** → Event status updated and logged
6. **Public Display** → Only approved events appear on public site

This system ensures complete control over what events appear on the public-facing website while maintaining efficiency through bulk operations and clear approval workflows.
