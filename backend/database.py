import sqlite3
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "ticket_matcher.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_keyword TEXT NOT NULL,
        buyer_tweet_id TEXT NOT NULL,
        buyer_username TEXT NOT NULL,
        buyer_text TEXT NOT NULL,
        buyer_timestamp TEXT NOT NULL,
        seller_tweet_id TEXT NOT NULL,
        seller_username TEXT NOT NULL,
        seller_text TEXT NOT NULL,
        seller_timestamp TEXT NOT NULL,
        confidence_score INTEGER NOT NULL,
        ai_reasoning TEXT NOT NULL,
        suggested_reply TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'auto_posted',
        post_type TEXT NOT NULL DEFAULT 'none',
        posted_tweet_id TEXT,
        posted_at TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(buyer_tweet_id, seller_tweet_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monitored_keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        details TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT NOT NULL,
        buyer_count INTEGER NOT NULL,
        seller_count INTEGER NOT NULL,
        match_count INTEGER NOT NULL,
        auto_posted_count INTEGER NOT NULL,
        scanned_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

# Auto-initialize DB on module load
init_db()

def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row is not None:
        return row["value"]
    val = os.getenv(key.upper()) or os.getenv(f"DEFAULT_{key.upper()}")
    if val is not None and val.strip() != "":
        return val.strip()
    return default

def set_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def log_activity(level: str, message: str, details: Optional[str] = None):
    conn = get_connection()
    cursor = conn.cursor()
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    cursor.execute("""
    INSERT INTO activity_logs (level, message, details, timestamp)
    VALUES (?, ?, ?, ?)
    """, (level, message, details, ts))
    cursor.execute("""
    DELETE FROM activity_logs WHERE id NOT IN (
        SELECT id FROM activity_logs ORDER BY id DESC LIMIT 200
    )
    """)
    conn.commit()
    conn.close()

def get_activity_logs(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def pair_already_processed(buyer_tweet_id: str, seller_tweet_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM matches WHERE buyer_tweet_id = ? AND seller_tweet_id = ?",
        (buyer_tweet_id, seller_tweet_id)
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def insert_match(
    event_keyword: str,
    buyer_tweet_id: str,
    buyer_username: str,
    buyer_text: str,
    buyer_timestamp: str,
    seller_tweet_id: str,
    seller_username: str,
    seller_text: str,
    seller_timestamp: str,
    confidence_score: int,
    ai_reasoning: str,
    suggested_reply: str,
    status: str = 'auto_posted',
    post_type: str = 'none',
    posted_tweet_id: Optional[str] = None,
    posted_at: Optional[str] = None
) -> Optional[int]:
    conn = get_connection()
    cursor = conn.cursor()
    created_at = datetime.utcnow().isoformat()
    try:
        cursor.execute("""
        INSERT INTO matches (
            event_keyword, buyer_tweet_id, buyer_username, buyer_text, buyer_timestamp,
            seller_tweet_id, seller_username, seller_text, seller_timestamp,
            confidence_score, ai_reasoning, suggested_reply,
            status, post_type, posted_tweet_id, posted_at, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_keyword, buyer_tweet_id, buyer_username, buyer_text, buyer_timestamp,
            seller_tweet_id, seller_username, seller_text, seller_timestamp,
            confidence_score, ai_reasoning, suggested_reply,
            status, post_type, posted_tweet_id, posted_at, created_at
        ))
        match_id = cursor.lastrowid
        conn.commit()
        return match_id
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_matches(status: Optional[str] = None, keyword: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM matches WHERE 1=1"
    params = []
    if status and status != 'all':
        query += " AND status = ?"
        params.append(status)
    if keyword:
        query += " AND event_keyword LIKE ?"
        params.append(f"%{keyword}%")
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_match_by_id(match_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_match_status(
    match_id: int,
    status: str,
    post_type: str,
    posted_tweet_id: str,
    reply_text: Optional[str] = None
):
    conn = get_connection()
    cursor = conn.cursor()
    posted_at = datetime.utcnow().isoformat()
    if reply_text:
        cursor.execute("""
        UPDATE matches
        SET status = ?, post_type = ?, posted_tweet_id = ?, posted_at = ?, suggested_reply = ?
        WHERE id = ?
        """, (status, post_type, posted_tweet_id, posted_at, reply_text, match_id))
    else:
        cursor.execute("""
        UPDATE matches
        SET status = ?, post_type = ?, posted_tweet_id = ?, posted_at = ?
        WHERE id = ?
        """, (status, post_type, posted_tweet_id, posted_at, match_id))
    conn.commit()
    conn.close()

def delete_match(match_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def get_monitored_keywords() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM monitored_keywords ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_monitored_keyword(keyword: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        ts = datetime.utcnow().isoformat()
        cursor.execute(
            "INSERT INTO monitored_keywords (keyword, is_active, created_at) VALUES (?, 1, ?)",
            (keyword.strip(), ts)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def remove_monitored_keyword(keyword_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM monitored_keywords WHERE id = ?", (keyword_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0

def clear_all_monitored_keywords() -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM monitored_keywords")
    conn.commit()
    conn.close()
    return True

def record_scan(keyword: str, buyer_count: int, seller_count: int, match_count: int, auto_posted_count: int):
    conn = get_connection()
    cursor = conn.cursor()
    scanned_at = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO scan_history (keyword, buyer_count, seller_count, match_count, auto_posted_count, scanned_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (keyword, buyer_count, seller_count, match_count, auto_posted_count, scanned_at))
    conn.commit()
    conn.close()

def get_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM matches")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'auto_posted'")
    auto_posted = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'approved'")
    manual_approved = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM matches WHERE confidence_score >= 70")
    high_confidence = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM monitored_keywords WHERE is_active = 1")
    active_keywords = cursor.fetchone()[0]
    conn.close()
    return {
        "total_matches": total,
        "auto_posted": auto_posted,
        "manual_approved": manual_approved,
        "posted": auto_posted + manual_approved,
        "high_confidence": high_confidence,
        "active_keywords": active_keywords
    }
