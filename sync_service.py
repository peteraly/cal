"""
Synchronization Service for Calendar Admin Dashboard
Handles real-time sync between admin dashboard and public website
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SyncService:
    """Handles synchronization between admin dashboard and public website"""
    
    def __init__(self, database_path: str = 'calendar.db'):
        self.database_path = database_path
        self.init_sync_tables()
    
    def init_sync_tables(self):
        """Initialize sync-related database tables"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create sync_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                source TEXT NOT NULL,
                event_id INTEGER,
                event_data TEXT,
                conflict_resolved BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                sync_session_id TEXT,
                success BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Create sync_conflicts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_id INTEGER,
                admin_data TEXT,
                public_data TEXT,
                conflict_type TEXT,
                resolution TEXT,
                resolved_by TEXT,
                resolved_at TEXT
            )
        ''')
        
        # Add sync metadata to events table
        try:
            cursor.execute('ALTER TABLE events ADD COLUMN last_sync_timestamp TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE events ADD COLUMN sync_hash TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
    
    def log_sync_operation(self, operation: str, source: str, event_id: int = None, 
                          event_data: Dict = None, error_message: str = None, 
                          sync_session_id: str = None, success: bool = True):
        """Log a synchronization operation"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO sync_logs 
            (timestamp, operation, source, event_id, event_data, error_message, sync_session_id, success)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            operation,
            source,
            event_id,
            json.dumps(event_data) if event_data else None,
            error_message,
            sync_session_id,
            success
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Sync operation logged: {operation} from {source} - {'Success' if success else 'Failed'}")
    
    def create_event_from_admin(self, event_data: Dict, sync_session_id: str = None) -> Tuple[bool, str, int]:
        """Create an event from admin dashboard data"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Transform admin data to database format
            start_datetime = f"{event_data['date']}T{event_data['time']}:00"
            tags_json = json.dumps(event_data.get('tags', []))
            
            cursor.execute('''
                INSERT INTO events 
                (title, start_datetime, description, location, category_id, tags, host, price_info, last_sync_timestamp, sync_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_data['title'],
                start_datetime,
                event_data.get('description', ''),
                event_data.get('location', ''),
                None,  # category_id - can be mapped later
                tags_json,
                event_data.get('host', ''),
                event_data.get('price', 'Free'),
                datetime.now().isoformat(),
                self._generate_sync_hash(event_data),
                datetime.now().isoformat()
            ))
            
            event_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # Log successful creation
            self.log_sync_operation('create', 'admin', event_id, event_data, 
                                  sync_session_id=sync_session_id, success=True)
            
            return True, "Event created successfully", event_id
            
        except Exception as e:
            error_msg = f"Failed to create event: {str(e)}"
            logger.error(error_msg)
            self.log_sync_operation('create', 'admin', None, event_data, 
                                  error_message=error_msg, sync_session_id=sync_session_id, success=False)
            return False, error_msg, None
    
    def update_event_from_admin(self, event_id: int, event_data: Dict, sync_session_id: str = None) -> Tuple[bool, str]:
        """Update an event from admin dashboard data"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if event exists
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            existing_event = cursor.fetchone()
            
            if not existing_event:
                return False, f"Event with ID {event_id} not found"
            
            # Check for conflicts
            conflict = self._detect_conflict(event_id, event_data, 'update')
            if conflict:
                return False, f"Conflict detected: {conflict}"
            
            # Transform admin data to database format
            start_datetime = f"{event_data['date']}T{event_data['time']}:00"
            tags_json = json.dumps(event_data.get('tags', []))
            
            cursor.execute('''
                UPDATE events SET 
                    title = ?, start_datetime = ?, description = ?, location = ?, 
                    tags = ?, host = ?, price_info = ?, last_sync_timestamp = ?, sync_hash = ?
                WHERE id = ?
            ''', (
                event_data['title'],
                start_datetime,
                event_data.get('description', ''),
                event_data.get('location', ''),
                tags_json,
                event_data.get('host', ''),
                event_data.get('price', 'Free'),
                datetime.now().isoformat(),
                self._generate_sync_hash(event_data),
                event_id
            ))
            
            conn.commit()
            conn.close()
            
            # Log successful update
            self.log_sync_operation('update', 'admin', event_id, event_data, 
                                  sync_session_id=sync_session_id, success=True)
            
            return True, "Event updated successfully"
            
        except Exception as e:
            error_msg = f"Failed to update event: {str(e)}"
            logger.error(error_msg)
            self.log_sync_operation('update', 'admin', event_id, event_data, 
                                  error_message=error_msg, sync_session_id=sync_session_id, success=False)
            return False, error_msg
    
    def delete_event_from_admin(self, event_id: int, sync_session_id: str = None) -> Tuple[bool, str]:
        """Delete an event from admin dashboard"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Check if event exists
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            existing_event = cursor.fetchone()
            
            if not existing_event:
                return False, f"Event with ID {event_id} not found"
            
            # Delete the event
            cursor.execute('DELETE FROM events WHERE id = ?', (event_id,))
            conn.commit()
            conn.close()
            
            # Log successful deletion
            self.log_sync_operation('delete', 'admin', event_id, None, 
                                  sync_session_id=sync_session_id, success=True)
            
            return True, "Event deleted successfully"
            
        except Exception as e:
            error_msg = f"Failed to delete event: {str(e)}"
            logger.error(error_msg)
            self.log_sync_operation('delete', 'admin', event_id, None, 
                                  error_message=error_msg, sync_session_id=sync_session_id, success=False)
            return False, error_msg
    
    def batch_sync_from_admin(self, sync_operations: List[Dict], sync_session_id: str = None) -> Dict:
        """Process a batch of sync operations from admin dashboard"""
        results = {
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'created_events': [],
            'updated_events': [],
            'deleted_events': []
        }
        
        for operation in sync_operations:
            try:
                op_type = operation.get('operation')
                event_data = operation.get('eventData')
                event_id = operation.get('eventId')
                
                if op_type == 'create':
                    success, message, new_id = self.create_event_from_admin(event_data, sync_session_id)
                    if success:
                        results['success_count'] += 1
                        results['created_events'].append(new_id)
                    else:
                        results['error_count'] += 1
                        results['errors'].append({
                            'operation': 'create',
                            'event_title': event_data.get('title', 'Unknown'),
                            'error': message
                        })
                
                elif op_type == 'update':
                    success, message = self.update_event_from_admin(event_id, event_data, sync_session_id)
                    if success:
                        results['success_count'] += 1
                        results['updated_events'].append(event_id)
                    else:
                        results['error_count'] += 1
                        results['errors'].append({
                            'operation': 'update',
                            'event_id': event_id,
                            'event_title': event_data.get('title', 'Unknown'),
                            'error': message
                        })
                
                elif op_type == 'delete':
                    success, message = self.delete_event_from_admin(event_id, sync_session_id)
                    if success:
                        results['success_count'] += 1
                        results['deleted_events'].append(event_id)
                    else:
                        results['error_count'] += 1
                        results['errors'].append({
                            'operation': 'delete',
                            'event_id': event_id,
                            'error': message
                        })
                
            except Exception as e:
                results['error_count'] += 1
                results['errors'].append({
                    'operation': operation.get('operation', 'unknown'),
                    'error': str(e)
                })
        
        # Log batch sync result
        self.log_sync_operation('batch_sync', 'admin', None, 
                              {'total_operations': len(sync_operations), 'results': results},
                              sync_session_id=sync_session_id, 
                              success=results['error_count'] == 0)
        
        return results
    
    def _detect_conflict(self, event_id: int, admin_data: Dict, operation: str) -> Optional[str]:
        """Detect conflicts between admin and public data"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM events WHERE id = ?', (event_id,))
            public_event = cursor.fetchone()
            
            if not public_event:
                return None  # No conflict if event doesn't exist
            
            # Check if public event was modified after last admin sync
            public_sync_time = public_event[9] if len(public_event) > 9 else None  # last_sync_timestamp
            if public_sync_time:
                # Simple conflict detection - in production, you'd want more sophisticated logic
                public_hash = public_event[10] if len(public_event) > 10 else None  # sync_hash
                admin_hash = self._generate_sync_hash(admin_data)
                
                if public_hash and public_hash != admin_hash:
                    return "Event was modified in public system after last admin sync"
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error detecting conflict: {str(e)}")
            return f"Error detecting conflict: {str(e)}"
    
    def _generate_sync_hash(self, event_data: Dict) -> str:
        """Generate a hash for event data to detect changes"""
        # Create a string representation of the event data
        data_string = f"{event_data.get('title', '')}{event_data.get('date', '')}{event_data.get('time', '')}{event_data.get('description', '')}{event_data.get('location', '')}{event_data.get('host', '')}{event_data.get('price', '')}"
        return hashlib.md5(data_string.encode()).hexdigest()
    
    def get_sync_history(self, limit: int = 50) -> List[Dict]:
        """Get recent sync history"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp, operation, source, event_id, success, error_message, sync_session_id
            FROM sync_logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (limit,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'timestamp': row[0],
                'operation': row[1],
                'source': row[2],
                'event_id': row[3],
                'success': row[4],
                'error_message': row[5],
                'sync_session_id': row[6]
            })
        
        conn.close()
        return history
    
    def get_sync_statistics(self) -> Dict:
        """Get sync statistics"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Total sync operations
        cursor.execute('SELECT COUNT(*) FROM sync_logs')
        total_operations = cursor.fetchone()[0]
        
        # Successful operations
        cursor.execute('SELECT COUNT(*) FROM sync_logs WHERE success = TRUE')
        successful_operations = cursor.fetchone()[0]
        
        # Failed operations
        cursor.execute('SELECT COUNT(*) FROM sync_logs WHERE success = FALSE')
        failed_operations = cursor.fetchone()[0]
        
        # Operations by type
        cursor.execute('SELECT operation, COUNT(*) FROM sync_logs GROUP BY operation')
        operations_by_type = dict(cursor.fetchall())
        
        # Recent activity (last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) FROM sync_logs 
            WHERE timestamp > datetime('now', '-1 day')
        ''')
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_operations': total_operations,
            'successful_operations': successful_operations,
            'failed_operations': failed_operations,
            'success_rate': (successful_operations / total_operations * 100) if total_operations > 0 else 0,
            'operations_by_type': operations_by_type,
            'recent_activity_24h': recent_activity
        }
