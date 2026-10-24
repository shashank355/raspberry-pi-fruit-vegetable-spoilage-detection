import os
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from src.config import Config


class Database:
    """
    Thread-safe SQLite database manager for FreshScan AI 2.0 event history and alert state.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = None):
        if self._initialized:
            return
        self._initialized = True
        self.db_path = db_path or Config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn_lock = threading.Lock()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    produce TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    freshness_score REAL NOT NULL,
                    category_score REAL NOT NULL,
                    image_path TEXT,
                    status TEXT NOT NULL DEFAULT 'NEW',
                    telegram_sent INTEGER DEFAULT 0,
                    telegram_error TEXT,
                    created_at TEXT NOT NULL,
                    acknowledged_at TEXT,
                    cleared_at TEXT
                );
                """)

                cursor.execute("""
                CREATE TABLE IF NOT EXISTS controller_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT,
                    timestamp TEXT NOT NULL
                );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_produce ON events(produce);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);")
                conn.commit()
            finally:
                conn.close()

    def get_next_event_id(self) -> str:
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT event_id FROM events WHERE event_id LIKE 'FS-%' ORDER BY rowid DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    last_id = row["event_id"]
                    try:
                        num = int(last_id.replace("FS-", "")) + 1
                        return f"FS-{num:04d}"
                    except Exception:
                        pass
                return "FS-0001"
            finally:
                conn.close()

    def create_event(
        self,
        event_id: str,
        produce: str,
        condition: str,
        freshness_score: float,
        category_score: float,
        image_path: str,
        status: str = "NEW"
    ) -> Dict[str, Any]:
        created_at = datetime.now().isoformat()
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO events (
                        event_id, produce, condition, freshness_score,
                        category_score, image_path, status, telegram_sent,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (event_id, produce, condition, freshness_score, category_score, image_path, status, created_at)
                )
                conn.commit()
            finally:
                conn.close()

        return {
            "event_id": event_id,
            "produce": produce,
            "condition": condition,
            "freshness_score": freshness_score,
            "category_score": category_score,
            "image_path": image_path,
            "status": status,
            "telegram_sent": 0,
            "created_at": created_at
        }

    def get_active_alert_by_produce(self, produce: str) -> Optional[Dict[str, Any]]:
        """
        Returns an unresolved alert (NEW or ACKNOWLEDGED) for a specific produce category.
        """
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM events WHERE produce = ? AND status IN ('NEW', 'ACKNOWLEDGED') ORDER BY rowid DESC LIMIT 1",
                    (produce,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM events WHERE status IN ('NEW', 'ACKNOWLEDGED') ORDER BY created_at DESC"
                )
                rows = cursor.fetchall()
                alerts = [dict(r) for r in rows]
                for a in alerts:
                    a["led_index"] = Config.PRODUCE_LED_MAP.get(a["produce"], 1)
                return alerts
            finally:
                conn.close()

    def acknowledge_alert(self, event_id: str) -> bool:
        ack_time = datetime.now().isoformat()
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE events SET status = 'ACKNOWLEDGED', acknowledged_at = ? WHERE (event_id = ? OR produce = ?) AND status = 'NEW'",
                    (ack_time, event_id, event_id)
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def clear_alert(self, event_id: str) -> bool:
        clear_time = datetime.now().isoformat()
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE events SET status = 'CLEARED', cleared_at = ? WHERE (event_id = ? OR produce = ?) AND status IN ('NEW', 'ACKNOWLEDGED')",
                    (clear_time, event_id, event_id)
                )
                conn.commit()
                return cursor.rowcount > 0
            finally:
                conn.close()

    def update_telegram_status(self, event_id: str, sent: bool, error: str = None):
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE events SET telegram_sent = ?, telegram_error = ? WHERE event_id = ?",
                    (1 if sent else 0, error, event_id)
                )
                conn.commit()
            finally:
                conn.close()

    def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM events ORDER BY created_at DESC LIMIT ?", (limit,)
                )
                rows = cursor.fetchall()
                results = [dict(r) for r in rows]
                for r in results:
                    r["led_index"] = Config.PRODUCE_LED_MAP.get(r["produce"], 1)
                return results
            finally:
                conn.close()

    def log_controller_event(self, device: str, event_type: str, payload: str):
        now = datetime.now().isoformat()
        with self._conn_lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO controller_logs (device, event_type, payload, timestamp) VALUES (?, ?, ?, ?)",
                    (device, event_type, payload, now)
                )
                conn.commit()
            finally:
                conn.close()
