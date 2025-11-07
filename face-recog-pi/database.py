"""
Database module for storing camera configurations, detections, and alerts
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import threading
import config

class Database:
    def __init__(self, db_file=config.DATABASE_FILE):
        self.db_file = db_file
        self.local = threading.local()
        self.init_database()
    
    def get_connection(self):
        """Get thread-local database connection"""
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            self.local.conn.row_factory = sqlite3.Row
        return self.local.conn
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Cameras table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                stream_url TEXT NOT NULL,
                location TEXT,
                status TEXT DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Detections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER NOT NULL,
                person_name TEXT NOT NULL,
                confidence REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                snapshot_path TEXT,
                bbox TEXT,
                FOREIGN KEY (camera_id) REFERENCES cameras(id)
            )
        """)
        
        # Alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER NOT NULL,
                person_name TEXT NOT NULL,
                alert_level TEXT DEFAULT 'medium',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                snapshot_path TEXT,
                acknowledged BOOLEAN DEFAULT 0,
                notes TEXT,
                FOREIGN KEY (camera_id) REFERENCES cameras(id)
            )
        """)
        
        # Watchlist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL UNIQUE,
                threat_level TEXT DEFAULT 'medium',
                description TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        conn.commit()
    
    # Camera operations
    def add_camera(self, name: str, stream_url: str, location: str = "", metadata: Dict = None) -> int:
        """Add a new camera"""
        conn = self.get_connection()
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        cursor.execute("""
            INSERT INTO cameras (name, stream_url, location, metadata)
            VALUES (?, ?, ?, ?)
        """, (name, stream_url, location, metadata_json))
        conn.commit()
        return cursor.lastrowid
    
    def get_camera(self, camera_id: int) -> Optional[Dict]:
        """Get camera by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras WHERE id = ?", (camera_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_camera_by_name(self, name: str) -> Optional[Dict]:
        """Get camera by name"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_cameras(self) -> List[Dict]:
        """Get all cameras"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cameras ORDER BY id")
        return [dict(row) for row in cursor.fetchall()]
    
    def update_camera_status(self, camera_id: int, status: str):
        """Update camera status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cameras 
            SET status = ?, last_seen = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (status, camera_id))
        conn.commit()
    
    def delete_camera(self, camera_id: int):
        """Delete a camera"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        conn.commit()
    
    # Detection operations
    def add_detection(self, camera_id: int, person_name: str, confidence: float, 
                     snapshot_path: str = None, bbox: tuple = None):
        """Add a detection record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        bbox_json = json.dumps(bbox) if bbox else None
        
        cursor.execute("""
            INSERT INTO detections (camera_id, person_name, confidence, snapshot_path, bbox)
            VALUES (?, ?, ?, ?, ?)
        """, (camera_id, person_name, confidence, snapshot_path, bbox_json))
        conn.commit()
        return cursor.lastrowid
    
    def get_recent_detections(self, limit: int = 100) -> List[Dict]:
        """Get recent detections"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.*, c.name as camera_name 
            FROM detections d
            JOIN cameras c ON d.camera_id = c.id
            ORDER BY d.timestamp DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_detections_by_camera(self, camera_id: int, limit: int = 50) -> List[Dict]:
        """Get detections for a specific camera"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM detections 
            WHERE camera_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (camera_id, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    # Alert operations
    def add_alert(self, camera_id: int, person_name: str, alert_level: str = "medium",
                 snapshot_path: str = None, notes: str = None) -> int:
        """Add an alert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts (camera_id, person_name, alert_level, snapshot_path, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (camera_id, person_name, alert_level, snapshot_path, notes))
        conn.commit()
        return cursor.lastrowid
    
    def get_recent_alerts(self, limit: int = 50, unacknowledged_only: bool = False) -> List[Dict]:
        """Get recent alerts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT a.*, c.name as camera_name 
            FROM alerts a
            JOIN cameras c ON a.camera_id = c.id
        """
        if unacknowledged_only:
            query += " WHERE a.acknowledged = 0"
        query += " ORDER BY a.timestamp DESC LIMIT ?"
        
        cursor.execute(query, (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def acknowledge_alert(self, alert_id: int):
        """Acknowledge an alert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
        conn.commit()
    
    # Watchlist operations
    def add_to_watchlist(self, person_name: str, threat_level: str = "medium", 
                        description: str = "", metadata: Dict = None) -> int:
        """Add person to watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        cursor.execute("""
            INSERT INTO watchlist (person_name, threat_level, description, metadata)
            VALUES (?, ?, ?, ?)
        """, (person_name, threat_level, description, metadata_json))
        conn.commit()
        return cursor.lastrowid
    
    def get_watchlist(self) -> List[Dict]:
        """Get all watchlist entries"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist ORDER BY threat_level, person_name")
        return [dict(row) for row in cursor.fetchall()]
    
    def is_on_watchlist(self, person_name: str) -> Optional[Dict]:
        """Check if person is on watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist WHERE person_name = ?", (person_name,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def remove_from_watchlist(self, person_name: str):
        """Remove person from watchlist"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watchlist WHERE person_name = ?", (person_name,))
        conn.commit()
    
    def get_statistics(self) -> Dict:
        """Get system statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # Total cameras
        cursor.execute("SELECT COUNT(*) as count FROM cameras")
        stats['total_cameras'] = cursor.fetchone()['count']
        
        # Active cameras
        cursor.execute("SELECT COUNT(*) as count FROM cameras WHERE status = 'active'")
        stats['active_cameras'] = cursor.fetchone()['count']
        
        # Total detections
        cursor.execute("SELECT COUNT(*) as count FROM detections")
        stats['total_detections'] = cursor.fetchone()['count']
        
        # Detections today
        cursor.execute("""
            SELECT COUNT(*) as count FROM detections 
            WHERE DATE(timestamp) = DATE('now')
        """)
        stats['detections_today'] = cursor.fetchone()['count']
        
        # Total alerts
        cursor.execute("SELECT COUNT(*) as count FROM alerts")
        stats['total_alerts'] = cursor.fetchone()['count']
        
        # Unacknowledged alerts
        cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE acknowledged = 0")
        stats['unacknowledged_alerts'] = cursor.fetchone()['count']
        
        # Watchlist count
        cursor.execute("SELECT COUNT(*) as count FROM watchlist")
        stats['watchlist_count'] = cursor.fetchone()['count']
        
        return stats

# Global database instance
db = Database()
