# Admin Event Approval Dashboard Enhancement

## Current State Analysis

The admin approval page at `http://localhost:5001/admin/approval` currently shows pending events in a basic list format. With multiple scrapers running (Smithsonian, Brookings, DC Fray, etc.) and events being added every 10 minutes, admins need better organization tools to efficiently review and approve events.

## Enhancement Goals

### 1. **Smart Sorting & Filtering**
- Sort by event date (chronological - soonest first)
- Sort by source website (group by scraper)
- Sort by discovery time (newest found first)
- Filter by date range, source, or event type

### 2. **Bulk Operations**
- Select multiple events for batch approval/rejection
- Quick approval for trusted sources
- Smart recommendations based on event quality

### 3. **Enhanced Event Display**
- Show event freshness (how recently discovered)
- Display confidence scores and source reliability
- Preview event details without leaving page

### 4. **Admin Productivity Features**
- Keyboard shortcuts for quick actions
- Auto-refresh for new events
- Progress tracking and statistics

## Implementation Strategy

### Phase 1: Enhanced Data Structure

```sql
-- Add indexing for faster sorting
CREATE INDEX IF NOT EXISTS idx_events_approval_date ON events(approval_status, start_datetime);
CREATE INDEX IF NOT EXISTS idx_events_source_created ON events(source, created_at);
CREATE INDEX IF NOT EXISTS idx_events_url_pattern ON events(url);

-- Add computed columns for better sorting
ALTER TABLE events ADD COLUMN source_domain TEXT;
ALTER TABLE events ADD COLUMN event_freshness_hours INTEGER;
```

### Phase 2: Backend API Enhancements

```python
# Enhanced API endpoint for approval dashboard
@app.route('/api/admin/events/pending-enhanced')
@require_auth
def get_pending_events_enhanced():
    """Enhanced pending events with sorting and filtering"""
    
    # Get query parameters
    sort_by = request.args.get('sort', 'event_date')  # event_date, source, discovery_time, confidence
    order = request.args.get('order', 'asc')  # asc, desc
    source_filter = request.args.get('source', 'all')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build dynamic query
    query = '''
        SELECT 
            id, title, description, start_datetime, location_name, 
            url, source, created_at, category_id,
            -- Computed fields
            CASE 
                WHEN url LIKE '%brookings%' THEN 'Brookings Institution'
                WHEN url LIKE '%districtfray%' THEN 'DC Fray Sports'
                WHEN url LIKE '%naturalhistory%' THEN 'Smithsonian Natural History'
                WHEN url LIKE '%hirshhorn%' THEN 'Smithsonian Hirshhorn'
                WHEN url LIKE '%americanhistory%' THEN 'Smithsonian American History'
                WHEN url LIKE '%runpacers%' THEN 'Pacers Running Club'
                ELSE 'Other Source'
            END as source_name,
            
            -- Event freshness (hours since discovered)
            CAST((julianday('now') - julianday(created_at)) * 24 as INTEGER) as hours_since_discovery,
            
            -- Days until event
            CAST(julianday(start_datetime) - julianday('now') as INTEGER) as days_until_event,
            
            -- Confidence score estimation
            CASE 
                WHEN location_name IS NOT NULL AND location_name != '' THEN 85
                WHEN description IS NOT NULL AND length(description) > 50 THEN 80
                ELSE 75
            END as estimated_confidence
            
        FROM events 
        WHERE approval_status = 'pending'
    '''
    
    # Add filters
    params = []
    if source_filter != 'all':
        query += ' AND url LIKE ?'
        params.append(f'%{source_filter}%')
    
    if date_from:
        query += ' AND start_datetime >= ?'
        params.append(date_from)
    
    if date_to:
        query += ' AND start_datetime <= ?'
        params.append(date_to)
    
    # Add sorting
    sort_columns = {
        'event_date': 'start_datetime',
        'source': 'source_name, start_datetime',
        'discovery_time': 'created_at',
        'confidence': 'estimated_confidence',
        'urgency': 'days_until_event'
    }
    
    sort_column = sort_columns.get(sort_by, 'start_datetime')
    query += f' ORDER BY {sort_column} {order.upper()}'
    
    # Execute query and return enhanced data
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    events = []
    for row in cursor.fetchall():
        event = {
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'start_datetime': row[3],
            'location_name': row[4],
            'url': row[5],
            'source': row[6],
            'created_at': row[7],
            'category_id': row[8],
            'source_name': row[9],
            'hours_since_discovery': row[10],
            'days_until_event': row[11],
            'estimated_confidence': row[12],
            'freshness_badge': get_freshness_badge(row[10]),
            'urgency_badge': get_urgency_badge(row[11])
        }
        events.append(event)
    
    conn.close()
    return jsonify(events)

def get_freshness_badge(hours):
    """Get color-coded freshness badge"""
    if hours <= 1:
        return {'text': 'Just found', 'class': 'bg-green-100 text-green-800'}
    elif hours <= 6:
        return {'text': f'{hours}h ago', 'class': 'bg-blue-100 text-blue-800'}
    elif hours <= 24:
        return {'text': f'{hours}h ago', 'class': 'bg-yellow-100 text-yellow-800'}
    else:
        days = hours // 24
        return {'text': f'{days}d ago', 'class': 'bg-gray-100 text-gray-800'}

def get_urgency_badge(days):
    """Get urgency badge for events"""
    if days < 0:
        return {'text': 'Past event', 'class': 'bg-red-100 text-red-800'}
    elif days == 0:
        return {'text': 'Today!', 'class': 'bg-red-100 text-red-800'}
    elif days == 1:
        return {'text': 'Tomorrow', 'class': 'bg-orange-100 text-orange-800'}
    elif days <= 7:
        return {'text': f'{days} days', 'class': 'bg-yellow-100 text-yellow-800'}
    elif days <= 30:
        return {'text': f'{days} days', 'class': 'bg-blue-100 text-blue-800'}
    else:
        return {'text': f'{days} days', 'class': 'bg-gray-100 text-gray-800'}

# Bulk operations endpoints
@app.route('/api/admin/events/bulk-approve', methods=['POST'])
@require_auth
def bulk_approve_events():
    """Approve multiple events at once"""
    data = request.get_json()
    event_ids = data.get('event_ids', [])
    
    if not event_ids:
        return jsonify({'error': 'No events selected'}), 400
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    placeholders = ','.join(['?' for _ in event_ids])
    cursor.execute(f'''
        UPDATE events 
        SET approval_status = 'approved' 
        WHERE id IN ({placeholders})
    ''', event_ids)
    
    approved_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': f'Approved {approved_count} events',
        'approved_count': approved_count
    })

@app.route('/api/admin/events/auto-approve-trusted', methods=['POST'])
@require_auth
def auto_approve_trusted_sources():
    """Auto-approve events from trusted sources with high confidence"""
    
    trusted_patterns = ['brookings.edu', 'si.edu', 'naturalhistory.si.edu']
    
    conn = sqlite3.connect('calendar.db')
    cursor = conn.cursor()
    
    for pattern in trusted_patterns:
        cursor.execute('''
            UPDATE events 
            SET approval_status = 'approved' 
            WHERE approval_status = 'pending' 
            AND url LIKE ? 
            AND location_name IS NOT NULL 
            AND location_name != ''
        ''', (f'%{pattern}%',))
    
    total_approved = cursor.rowcount
    conn.commit()
    conn.close()
    
    return jsonify({
        'message': f'Auto-approved {total_approved} events from trusted sources',
        'approved_count': total_approved
    })
```

### Phase 3: Frontend Enhancement

```html
<!-- Enhanced Admin Approval Dashboard -->
<div x-data="enhancedApprovalDashboard()" class="p-6">
    <!-- Header with controls -->
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Event Approval Dashboard</h1>
        
        <!-- Auto-refresh toggle -->
        <div class="flex items-center space-x-4">
            <label class="flex items-center">
                <input type="checkbox" x-model="autoRefresh" class="mr-2">
                Auto-refresh (30s)
            </label>
            
            <button @click="refreshEvents()" class="btn btn-primary">
                <i class="fas fa-sync" :class="{'fa-spin': loading}"></i>
                Refresh
            </button>
        </div>
    </div>
    
    <!-- Enhanced filters and sorting -->
    <div class="bg-white p-4 rounded-lg shadow mb-6">
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <!-- Sort by -->
            <div>
                <label class="block text-sm font-medium mb-1">Sort by</label>
                <select x-model="sortBy" @change="loadEvents()" class="w-full border rounded px-3 py-2">
                    <option value="event_date">Event Date</option>
                    <option value="source">Source Website</option>
                    <option value="discovery_time">Discovery Time</option>
                    <option value="urgency">Urgency (Soon First)</option>
                    <option value="confidence">Confidence Score</option>
                </select>
            </div>
            
            <!-- Source filter -->
            <div>
                <label class="block text-sm font-medium mb-1">Source</label>
                <select x-model="sourceFilter" @change="loadEvents()" class="w-full border rounded px-3 py-2">
                    <option value="all">All Sources</option>
                    <option value="brookings">Brookings Institution</option>
                    <option value="naturalhistory">Smithsonian Natural History</option>
                    <option value="hirshhorn">Smithsonian Hirshhorn</option>
                    <option value="districtfray">DC Fray Sports</option>
                    <option value="runpacers">Pacers Running</option>
                </select>
            </div>
            
            <!-- Date range -->
            <div>
                <label class="block text-sm font-medium mb-1">Date From</label>
                <input type="date" x-model="dateFrom" @change="loadEvents()" 
                       class="w-full border rounded px-3 py-2">
            </div>
            
            <div>
                <label class="block text-sm font-medium mb-1">Date To</label>
                <input type="date" x-model="dateTo" @change="loadEvents()" 
                       class="w-full border rounded px-3 py-2">
            </div>
        </div>
        
        <!-- Bulk actions -->
        <div class="mt-4 flex items-center space-x-4">
            <button @click="selectAll()" class="text-blue-600 hover:text-blue-800">
                <i class="fas fa-check-square mr-1"></i>
                Select All
            </button>
            
            <button @click="clearSelection()" class="text-gray-600 hover:text-gray-800">
                <i class="fas fa-square mr-1"></i>
                Clear Selection
            </button>
            
            <button @click="bulkApprove()" 
                    :disabled="selectedEvents.length === 0"
                    class="btn btn-green disabled:opacity-50">
                <i class="fas fa-check mr-1"></i>
                Approve Selected (<span x-text="selectedEvents.length"></span>)
            </button>
            
            <button @click="bulkReject()" 
                    :disabled="selectedEvents.length === 0"
                    class="btn btn-red disabled:opacity-50">
                <i class="fas fa-times mr-1"></i>
                Reject Selected (<span x-text="selectedEvents.length"></span>)
            </button>
            
            <button @click="autoApproveTrusted()" class="btn btn-blue">
                <i class="fas fa-magic mr-1"></i>
                Auto-Approve Trusted
            </button>
        </div>
    </div>
    
    <!-- Stats overview -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white p-4 rounded-lg shadow">
            <div class="text-2xl font-bold text-blue-600" x-text="stats.total"></div>
            <div class="text-sm text-gray-600">Total Pending</div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow">
            <div class="text-2xl font-bold text-green-600" x-text="stats.freshEvents"></div>
            <div class="text-sm text-gray-600">Fresh (< 6h)</div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow">
            <div class="text-2xl font-bold text-orange-600" x-text="stats.urgentEvents"></div>
            <div class="text-sm text-gray-600">Urgent (< 7 days)</div>
        </div>
        
        <div class="bg-white p-4 rounded-lg shadow">
            <div class="text-2xl font-bold text-purple-600" x-text="stats.sourceCount"></div>
            <div class="text-sm text-gray-600">Different Sources</div>
        </div>
    </div>
    
    <!-- Enhanced events table -->
    <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="overflow-x-auto">
            <table class="min-w-full">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left">
                            <input type="checkbox" @change="toggleAllSelection($event.target.checked)">
                        </th>
                        <th class="px-4 py-3 text-left font-medium text-gray-900">Event Details</th>
                        <th class="px-4 py-3 text-left font-medium text-gray-900">Source & Freshness</th>
                        <th class="px-4 py-3 text-left font-medium text-gray-900">Date & Urgency</th>
                        <th class="px-4 py-3 text-left font-medium text-gray-900">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                    <template x-for="event in events" :key="event.id">
                        <tr class="hover:bg-gray-50" 
                            :class="{'bg-blue-50': selectedEvents.includes(event.id)}">
                            
                            <!-- Selection checkbox -->
                            <td class="px-4 py-3">
                                <input type="checkbox" 
                                       :value="event.id"
                                       x-model="selectedEvents">
                            </td>
                            
                            <!-- Event details -->
                            <td class="px-4 py-3">
                                <div class="flex items-start space-x-3">
                                    <!-- Confidence indicator -->
                                    <div class="flex-shrink-0 mt-1">
                                        <div class="w-3 h-3 rounded-full"
                                             :class="getConfidenceColor(event.estimated_confidence)"></div>
                                    </div>
                                    
                                    <div class="flex-1 min-w-0">
                                        <h3 class="text-sm font-medium text-gray-900 truncate" 
                                            x-text="event.title"></h3>
                                        
                                        <p class="text-sm text-gray-500 mt-1" 
                                           x-text="event.location_name"></p>
                                        
                                        <!-- Preview description -->
                                        <p class="text-xs text-gray-400 mt-1 line-clamp-2" 
                                           x-text="event.description?.substring(0, 100) + '...'"></p>
                                    </div>
                                </div>
                            </td>
                            
                            <!-- Source and freshness -->
                            <td class="px-4 py-3">
                                <div class="space-y-2">
                                    <div class="text-sm font-medium text-gray-900" 
                                         x-text="event.source_name"></div>
                                    
                                    <span class="inline-flex px-2 py-1 text-xs rounded-full"
                                          :class="event.freshness_badge.class"
                                          x-text="event.freshness_badge.text"></span>
                                </div>
                            </td>
                            
                            <!-- Date and urgency -->
                            <td class="px-4 py-3">
                                <div class="space-y-2">
                                    <div class="text-sm text-gray-900" 
                                         x-text="formatEventDate(event.start_datetime)"></div>
                                    
                                    <span class="inline-flex px-2 py-1 text-xs rounded-full"
                                          :class="event.urgency_badge.class"
                                          x-text="event.urgency_badge.text"></span>
                                </div>
                            </td>
                            
                            <!-- Actions -->
                            <td class="px-4 py-3">
                                <div class="flex space-x-2">
                                    <button @click="approveEvent(event.id)" 
                                            class="text-green-600 hover:text-green-800">
                                        <i class="fas fa-check"></i>
                                    </button>
                                    
                                    <button @click="rejectEvent(event.id)" 
                                            class="text-red-600 hover:text-red-800">
                                        <i class="fas fa-times"></i>
                                    </button>
                                    
                                    <button @click="viewEventDetails(event)" 
                                            class="text-blue-600 hover:text-blue-800">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
        
        <!-- Empty state -->
        <div x-show="events.length === 0 && !loading" class="text-center py-12">
            <i class="fas fa-check-circle text-4xl text-green-500 mb-4"></i>
            <h3 class="text-lg font-medium text-gray-900 mb-2">All caught up!</h3>
            <p class="text-gray-500">No pending events to review.</p>
        </div>
        
        <!-- Loading state -->
        <div x-show="loading" class="text-center py-12">
            <i class="fas fa-spinner fa-spin text-2xl text-blue-500 mb-4"></i>
            <p class="text-gray-500">Loading events...</p>
        </div>
    </div>
</div>

<script>
function enhancedApprovalDashboard() {
    return {
        events: [],
        selectedEvents: [],
        loading: false,
        autoRefresh: false,
        refreshInterval: null,
        
        // Filters and sorting
        sortBy: 'event_date',
        sourceFilter: 'all',
        dateFrom: '',
        dateTo: '',
        
        // Stats
        stats: {
            total: 0,
            freshEvents: 0,
            urgentEvents: 0,
            sourceCount: 0
        },
        
        init() {
            this.loadEvents();
            this.setupAutoRefresh();
            this.setupKeyboardShortcuts();
        },
        
        loadEvents() {
            this.loading = true;
            
            const params = new URLSearchParams({
                sort: this.sortBy,
                source: this.sourceFilter,
                date_from: this.dateFrom,
                date_to: this.dateTo
            });
            
            fetch(`/api/admin/events/pending-enhanced?${params}`)
                .then(response => response.json())
                .then(data => {
                    this.events = data;
                    this.updateStats();
                })
                .catch(error => {
                    console.error('Error loading events:', error);
                    this.showToast('Error loading events', 'error');
                })
                .finally(() => {
                    this.loading = false;
                });
        },
        
        updateStats() {
            this.stats.total = this.events.length;
            this.stats.freshEvents = this.events.filter(e => e.hours_since_discovery <= 6).length;
            this.stats.urgentEvents = this.events.filter(e => e.days_until_event <= 7).length;
            
            const sources = new Set(this.events.map(e => e.source_name));
            this.stats.sourceCount = sources.size;
        },
        
        setupAutoRefresh() {
            this.$watch('autoRefresh', (enabled) => {
                if (enabled) {
                    this.refreshInterval = setInterval(() => {
                        this.loadEvents();
                    }, 30000); // 30 seconds
                } else if (this.refreshInterval) {
                    clearInterval(this.refreshInterval);
                }
            });
        },
        
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + A: Select all
                if ((e.ctrlKey || e.metaKey) && e.key === 'a') {
                    e.preventDefault();
                    this.selectAll();
                }
                
                // Ctrl/Cmd + Enter: Approve selected
                if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                    e.preventDefault();
                    this.bulkApprove();
                }
                
                // R: Refresh
                if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault();
                    this.refreshEvents();
                }
            });
        },
        
        selectAll() {
            this.selectedEvents = this.events.map(e => e.id);
        },
        
        clearSelection() {
            this.selectedEvents = [];
        },
        
        toggleAllSelection(checked) {
            this.selectedEvents = checked ? this.events.map(e => e.id) : [];
        },
        
        bulkApprove() {
            if (this.selectedEvents.length === 0) return;
            
            fetch('/api/admin/events/bulk-approve', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({event_ids: this.selectedEvents})
            })
            .then(response => response.json())
            .then(data => {
                this.showToast(data.message, 'success');
                this.selectedEvents = [];
                this.loadEvents();
            })
            .catch(error => {
                this.showToast('Error approving events', 'error');
            });
        },
        
        autoApproveTrusted() {
            fetch('/api/admin/events/auto-approve-trusted', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    this.showToast(data.message, 'success');
                    this.loadEvents();
                })
                .catch(error => {
                    this.showToast('Error auto-approving events', 'error');
                });
        },
        
        formatEventDate(datetime) {
            return new Date(datetime).toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
            });
        },
        
        getConfidenceColor(confidence) {
            if (confidence >= 90) return 'bg-green-500';
            if (confidence >= 80) return 'bg-yellow-500';
            return 'bg-red-500';
        },
        
        showToast(message, type) {
            // Toast notification implementation
            console.log(`${type}: ${message}`);
        }
    }
}
</script>
```

## Key Benefits

### 1. **Efficient Organization**
- **Chronological sorting**: Events sorted by date (soonest first) helps prioritize urgent approvals
- **Source grouping**: Group events by website/scraper for consistent quality assessment
- **Smart filtering**: Filter by date range, source, or confidence level

### 2. **Productivity Features**
- **Bulk operations**: Select and approve/reject multiple events at once
- **Auto-approval**: Automatically approve high-confidence events from trusted sources
- **Keyboard shortcuts**: Quick actions without mouse clicks

### 3. **Visual Enhancements**
- **Freshness indicators**: Color-coded badges showing how recently events were discovered
- **Urgency badges**: Highlight events happening soon (today, tomorrow, this week)
- **Confidence indicators**: Visual cues for event data quality

### 4. **Admin Intelligence**
- **Auto-refresh**: Stay updated with new events every 30 seconds
- **Smart recommendations**: Suggest trusted sources for auto-approval
- **Statistics**: Quick overview of pending events and sources

This enhanced approval dashboard transforms the admin experience from a basic list to an intelligent, efficient workflow tool that scales with your growing number of event sources.
