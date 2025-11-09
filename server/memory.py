"""
SQLite-backed memory system for NPC interactions.
Implements salience × recency retrieval for contextual dialogue.
"""
import sqlite3
import json
import time
from typing import List, Optional
from contextlib import contextmanager
from pathlib import Path
import logging

from .schemas import NpcMemoryWrite, MemoryEntry
from .settings import settings

logger = logging.getLogger(__name__)


class MemoryDAO:
    """
    Lightweight SQLite DAO for NPC memory.
    Supports write/read with top-k retrieval by salience and recency.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the memory database.
        
        Args:
            db_path: Path to SQLite database file. If None, uses settings.db_path
        """
        self.db_path = db_path or settings.db_path
        self._init_db()
        logger.info(f"MemoryDAO initialized with database: {self.db_path}")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Create tables and indexes if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Main memory table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS npc_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    npc_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    salience INTEGER NOT NULL CHECK(salience >= 0 AND salience <= 3),
                    private INTEGER NOT NULL DEFAULT 1,
                    keys TEXT,
                    ts INTEGER NOT NULL
                )
            """)
            
            # Index for efficient querying by npc_id, player_id, salience, and recency
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_query 
                ON npc_memory(npc_id, player_id, salience DESC, ts DESC)
            """)
            
            # Index for timestamp-based cleanup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_mem_ts 
                ON npc_memory(ts)
            """)
            
            logger.info("Database schema initialized")
    
    def write(
        self,
        npc_id: str,
        player_id: str,
        text: str,
        salience: int,
        private: bool = True,
        keys: Optional[List[str]] = None,
        ts: Optional[int] = None
    ) -> int:
        """
        Write a memory entry.
        
        Args:
            npc_id: NPC identifier
            player_id: Player identifier
            text: Memory content (max 160 chars)
            salience: Importance level (0=trivial, 3=critical)
            private: Whether only this NPC knows this
            keys: Optional search keywords
            ts: Unix timestamp (defaults to now)
        
        Returns:
            ID of the inserted row
        """
        if not (0 <= salience <= 3):
            raise ValueError(f"Salience must be 0-3, got {salience}")
        
        if len(text) > 160:
            logger.warning(f"Memory text truncated from {len(text)} to 160 chars")
            text = text[:160]
        
        ts = ts or int(time.time())
        keys_json = json.dumps(keys) if keys else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO npc_memory (npc_id, player_id, text, salience, private, keys, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (npc_id, player_id, text, salience, int(private), keys_json, ts)
            )
            row_id = cursor.lastrowid
            logger.info(f"Wrote memory {row_id}: npc={npc_id}, salience={salience}")
            return row_id
    
    def write_from_model(self, memory: NpcMemoryWrite) -> int:
        """
        Convenience method to write from a Pydantic model.
        
        Args:
            memory: NpcMemoryWrite instance
        
        Returns:
            ID of the inserted row
        """
        return self.write(
            npc_id=memory.npc_id,
            player_id=memory.player_id,
            text=memory.text,
            salience=memory.salience,
            private=memory.private,
            keys=memory.keys
        )
    
    def top(
        self,
        npc_id: str,
        player_id: str,
        k: int = 3,
        min_salience: int = 0
    ) -> List[MemoryEntry]:
        """
        Retrieve top-k memories ordered by salience (desc) then recency (desc).
        
        Args:
            npc_id: NPC identifier
            player_id: Player identifier
            k: Number of memories to retrieve
            min_salience: Minimum salience threshold (default 0)
        
        Returns:
            List of MemoryEntry objects, most salient/recent first
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, npc_id, player_id, text, salience, private, keys, ts
                FROM npc_memory
                WHERE npc_id = ? AND player_id = ? AND salience >= ?
                ORDER BY salience DESC, ts DESC
                LIMIT ?
                """,
                (npc_id, player_id, min_salience, k)
            )
            
            rows = cursor.fetchall()
            memories = [
                MemoryEntry(
                    id=row["id"],
                    npc_id=row["npc_id"],
                    player_id=row["player_id"],
                    text=row["text"],
                    salience=row["salience"],
                    private=bool(row["private"]),
                    keys=row["keys"],
                    ts=row["ts"]
                )
                for row in rows
            ]
            
            logger.debug(f"Retrieved {len(memories)} memories for npc={npc_id}, player={player_id}")
            return memories
    
    def get_all_for_npc(
        self,
        npc_id: str,
        player_id: Optional[str] = None,
        limit: int = 100
    ) -> List[MemoryEntry]:
        """
        Get all memories for an NPC, optionally filtered by player.
        
        Args:
            npc_id: NPC identifier
            player_id: Optional player filter
            limit: Max results (default 100)
        
        Returns:
            List of MemoryEntry objects
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if player_id:
                cursor.execute(
                    """
                    SELECT id, npc_id, player_id, text, salience, private, keys, ts
                    FROM npc_memory
                    WHERE npc_id = ? AND player_id = ?
                    ORDER BY ts DESC
                    LIMIT ?
                    """,
                    (npc_id, player_id, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, npc_id, player_id, text, salience, private, keys, ts
                    FROM npc_memory
                    WHERE npc_id = ?
                    ORDER BY ts DESC
                    LIMIT ?
                    """,
                    (npc_id, limit)
                )
            
            rows = cursor.fetchall()
            return [
                MemoryEntry(
                    id=row["id"],
                    npc_id=row["npc_id"],
                    player_id=row["player_id"],
                    text=row["text"],
                    salience=row["salience"],
                    private=bool(row["private"]),
                    keys=row["keys"],
                    ts=row["ts"]
                )
                for row in rows
            ]
    
    def delete_old_memories(self, days_old: int = 30) -> int:
        """
        Delete memories older than specified days.
        Useful for keeping database size manageable.
        
        Args:
            days_old: Delete memories older than this many days
        
        Returns:
            Number of rows deleted
        """
        cutoff_ts = int(time.time()) - (days_old * 24 * 60 * 60)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM npc_memory WHERE ts < ?",
                (cutoff_ts,)
            )
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} memories older than {days_old} days")
            return deleted
    
    def count_memories(self, npc_id: Optional[str] = None) -> int:
        """
        Count total memories, optionally filtered by NPC.
        
        Args:
            npc_id: Optional NPC filter
        
        Returns:
            Memory count
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if npc_id:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM npc_memory WHERE npc_id = ?",
                    (npc_id,)
                )
            else:
                cursor.execute("SELECT COUNT(*) as count FROM npc_memory")
            
            return cursor.fetchone()["count"]


# Global DAO instance
memory_dao = MemoryDAO()

