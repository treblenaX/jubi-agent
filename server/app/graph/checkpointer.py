"""
SQLite Checkpointer for session persistence.

This module provides durable conversation storage via SQLite checkpoints.
Sessions are identified by thread_id and can be recovered across restarts.
"""

import sqlite3
from typing import Optional, List, Dict, Any
from datetime import datetime


class SqliteSaver:
    """
    SQLite checkpoint saver for LangGraph sessions.
    
    Provides session persistence via thread_id-based storage.
    """
    
    def __init__(self, db_path: str = "harness.db"):
        """
        Initialize the checkpointer.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
    
    @classmethod
    def from_conn_string(cls, conn_string: str) -> "SqliteSaver":
        """
        Create a checkpointer from a connection string.
        
        Args:
            conn_string: SQLite connection string (e.g., "harness.db")
            
        Returns:
            Configured SqliteSaver instance
        """
        saver = cls()
        saver.conn = sqlite3.connect(conn_string)
        saver._init_db()
        return saver
    
    def _init_db(self):
        """Initialize the database schema."""
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                thread_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                state_data TEXT NOT NULL
            )
        """)
        
        # Create checkpoints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                checkpoint_name TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                state_data TEXT NOT NULL,
                FOREIGN KEY (thread_id) REFERENCES sessions(thread_id)
            )
        """)
        
        self.conn.commit()
    
    def save_checkpoint(self, thread_id: str, checkpoint_name: str, state: Dict[str, Any]):
        """
        Save a checkpoint for a session.
        
        Args:
            thread_id: Session identifier
            checkpoint_name: Name of the checkpoint (e.g., "step_1", "complete")
            state: State snapshot to store
        """
        if not self.conn:
            return
        
        # Serialize state
        import json
        state_data = json.dumps(state, default=str)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO checkpoints (thread_id, checkpoint_name, state_data)
            VALUES (?, ?, ?)
        """, (thread_id, checkpoint_name, state_data))
        
        # Update session timestamp
        cursor.execute("""
            UPDATE sessions 
            SET last_updated = CURRENT_TIMESTAMP, state_data = ?
            WHERE thread_id = ?
        """, (state_data, thread_id))
        
        self.conn.commit()
    
    def load_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the latest checkpoint for a session.
        
        Args:
            thread_id: Session identifier
            
        Returns:
            State dict or None if not found
        """
        if not self.conn:
            return None
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT state_data FROM sessions 
            WHERE thread_id = ?
            ORDER BY last_updated DESC 
            LIMIT 1
        """, (thread_id,))
        
        row = cursor.fetchone()
        if row:
            import json
            return json.loads(row[0], object_hook=lambda d: d)
        
        return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all active sessions.
        
        Returns:
            List of session info dicts
        """
        if not self.conn:
            return []
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT thread_id, created_at, last_updated 
            FROM sessions 
            ORDER BY last_updated DESC
        """)
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "thread_id": row[0],
                "created_at": row[1],
                "last_updated": row[2]
            })
        
        return sessions
    
    def delete_session(self, thread_id: str):
        """
        Delete a session and its checkpoints.
        
        Args:
            thread_id: Session identifier to delete
        """
        if not self.conn:
            return
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        cursor.execute("DELETE FROM sessions WHERE thread_id = ?", (thread_id,))
        self.conn.commit()
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


# Module-level convenience function for langgraph.json
def create_saver(db_path: str = "harness.db") -> SqliteSaver:
    """
    Create a checkpointer instance.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Configured SqliteSaver
    """
    return SqliteSaver.from_conn_string(db_path)
