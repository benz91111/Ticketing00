"""
Database Manager - SQLite
"""
import sqlite3
import json
import datetime
import os
from pathlib import Path

# Railway usa /data para volumes persistentes
# Localmente usa a pasta databases do projeto
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME"):
    BASE_DIR = Path("/data")
else:
    BASE_DIR = Path(__file__).parent.parent.parent

DB_DIR = BASE_DIR / "databases"
DB_PATH = DB_DIR / "tickets.db"

# Garantir que a pasta databases existe
DB_DIR.mkdir(parents=True, exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize all database tables"""
    DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = get_connection()
    c = conn.cursor()

    # Tickets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT NOT NULL,
            channel_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            category_id TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            claimed_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            closed_at TIMESTAMP,
            closed_by TEXT,
            transcript_url TEXT,
            rating INTEGER,
            rating_comment TEXT,
            locked INTEGER DEFAULT 0,
            participants TEXT DEFAULT '[]',
            message_count INTEGER DEFAULT 0,
            first_response_at TIMESTAMP,
            last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ticket messages table
    c.execute("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            message_id TEXT,
            author_id TEXT,
            author_name TEXT,
            author_avatar TEXT,
            content TEXT,
            attachments TEXT,
            embeds TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )
    """)

    # Logs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            action TEXT,
            user_id TEXT,
            target_id TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Cooldowns table
    c.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id TEXT,
            guild_id TEXT,
            last_ticket_at TIMESTAMP,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    # Spam logs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS spam_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            guild_id TEXT,
            channel_id TEXT,
            message_count INTEGER,
            warned INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Backups table
    c.execute("""
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            size_bytes INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stats table
    c.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT,
            date TEXT,
            tickets_opened INTEGER DEFAULT 0,
            tickets_closed INTEGER DEFAULT 0,
            avg_rating REAL,
            avg_response_time INTEGER
        )
    """)

    # Ratings table
    c.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            user_id TEXT,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

# Ticket operations
def create_ticket(guild_id, channel_id, user_id, category_id, reason, priority="medium"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tickets (guild_id, channel_id, user_id, category_id, reason, status, priority, participants)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(guild_id), str(channel_id), str(user_id), category_id, reason, "open", priority, json.dumps([str(user_id)])))
    ticket_id = c.lastrowid
    conn.commit()
    conn.close()
    return ticket_id

def get_ticket(ticket_id=None, channel_id=None):
    conn = get_connection()
    c = conn.cursor()
    if ticket_id:
        c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    elif channel_id:
        c.execute("SELECT * FROM tickets WHERE channel_id = ?", (str(channel_id),))
    else:
        conn.close()
        return None
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_tickets(guild_id=None, status=None, limit=100):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []
    if guild_id:
        query += " AND guild_id = ?"
        params.append(str(guild_id))
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_ticket(ticket_id=None, channel_id=None, **kwargs):
    conn = get_connection()
    c = conn.cursor()

    fields = []
    values = []
    for key, value in kwargs.items():
        fields.append(f"{key} = ?")
        values.append(value)

    if ticket_id:
        values.append(ticket_id)
        c.execute(f"UPDATE tickets SET {', '.join(fields)} WHERE id = ?", values)
    elif channel_id:
        values.append(str(channel_id))
        c.execute(f"UPDATE tickets SET {', '.join(fields)} WHERE channel_id = ?", values)

    conn.commit()
    conn.close()

def delete_ticket(ticket_id=None, channel_id=None):
    conn = get_connection()
    c = conn.cursor()
    if ticket_id:
        c.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    elif channel_id:
        c.execute("DELETE FROM tickets WHERE channel_id = ?", (str(channel_id),))
    conn.commit()
    conn.close()

def count_user_tickets(user_id, guild_id, status="open"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tickets WHERE user_id = ? AND guild_id = ? AND status = ?", 
                (str(user_id), str(guild_id), status))
    count = c.fetchone()[0]
    conn.close()
    return count

# Message operations
def add_message(ticket_id, message_id, author_id, author_name, author_avatar, content, attachments=None, embeds=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO ticket_messages (ticket_id, message_id, author_id, author_name, author_avatar, content, attachments, embeds)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (ticket_id, str(message_id), str(author_id), author_name, author_avatar, content, 
          json.dumps(attachments or []), json.dumps(embeds or [])))
    c.execute("UPDATE tickets SET message_count = message_count + 1, last_activity_at = ? WHERE id = ?", 
              (datetime.datetime.now().isoformat(), ticket_id))
    conn.commit()
    conn.close()

def get_messages(ticket_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM ticket_messages WHERE ticket_id = ? ORDER BY created_at", (ticket_id,))
    rows = c.fetchall()
    conn.close()
    messages = []
    for row in rows:
        msg = dict(row)
        msg["attachments"] = json.loads(msg["attachments"] or "[]")
        msg["embeds"] = json.loads(msg["embeds"] or "[]")
        messages.append(msg)
    return messages

# Cooldown operations
def check_cooldown(user_id, guild_id, cooldown_seconds):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT last_ticket_at FROM cooldowns WHERE user_id = ? AND guild_id = ?", 
              (str(user_id), str(guild_id)))
    row = c.fetchone()
    conn.close()

    if row and row["last_ticket_at"]:
        last_time = datetime.datetime.fromisoformat(row["last_ticket_at"])
        elapsed = (datetime.datetime.now() - last_time).total_seconds()
        if elapsed < cooldown_seconds:
            return int(cooldown_seconds - elapsed)
    return 0

def update_cooldown(user_id, guild_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO cooldowns (user_id, guild_id, last_ticket_at, count) 
        VALUES (?, ?, ?, 1)
        ON CONFLICT(user_id, guild_id) DO UPDATE SET
        last_ticket_at = ?, count = count + 1
    """, (str(user_id), str(guild_id), datetime.datetime.now().isoformat(), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

# Log operations
def add_log(guild_id, action, user_id, target_id=None, details=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (guild_id, action, user_id, target_id, details)
        VALUES (?, ?, ?, ?, ?)
    """, (str(guild_id), action, str(user_id), str(target_id) if target_id else None, json.dumps(details) if details else None))
    conn.commit()
    conn.close()

    # Also write to file
    from .logger import log_to_file
    log_to_file(action, user_id, target_id, details)

def get_logs(guild_id=None, action=None, limit=100):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    if guild_id:
        query += " AND guild_id = ?"
        params.append(str(guild_id))
    if action:
        query += " AND action = ?"
        params.append(action)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Stats operations
def get_stats(guild_id=None):
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT COUNT(*) FROM tickets"
    params = []
    if guild_id:
        query += " WHERE guild_id = ?"
        params.append(str(guild_id))

    c.execute(query, params)
    total = c.fetchone()[0]

    c.execute(query + " AND status = 'open'", params)
    open_count = c.fetchone()[0]

    c.execute(query + " AND status = 'closed'", params)
    closed_count = c.fetchone()[0]

    c.execute("SELECT AVG(rating) FROM tickets WHERE rating IS NOT NULL" + (" AND guild_id = ?" if guild_id else ""), params)
    avg_rating = c.fetchone()[0] or 0

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM tickets WHERE DATE(created_at) = ?" + (" AND guild_id = ?" if guild_id else ""), [today] + params)
    today_count = c.fetchone()[0]

    conn.close()

    return {
        "total": total,
        "open": open_count,
        "closed": closed_count,
        "avg_rating": round(avg_rating, 1),
        "today": today_count
    }

# Rating operations
def add_rating(ticket_id, user_id, rating, comment=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO ratings (ticket_id, user_id, rating, comment)
        VALUES (?, ?, ?, ?)
    """, (ticket_id, str(user_id), rating, comment))
    c.execute("UPDATE tickets SET rating = ? WHERE id = ?", (rating, ticket_id))
    conn.commit()
    conn.close()

def get_ratings(guild_id=None):
    conn = get_connection()
    c = conn.cursor()
    query = """
        SELECT r.* FROM ratings r
        JOIN tickets t ON r.ticket_id = t.id
        WHERE 1=1
    """
    params = []
    if guild_id:
        query += " AND t.guild_id = ?"
        params.append(str(guild_id))
    query += " ORDER BY r.created_at DESC"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
