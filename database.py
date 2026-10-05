import sqlite3
from pathlib import Path

from config import DATABASE_PATH


DB_PATH = Path(DATABASE_PATH)


def prepare_database_path():
    if DB_PATH.parent:
        DB_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )


def get_db():
    prepare_database_path()

    db = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False
    )

    db.row_factory = sqlite3.Row

    return db


def init_db():
    db = get_db()

    db.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            protocol TEXT NOT NULL DEFAULT 'vless',
            node TEXT DEFAULT '',
            inbound_id INTEGER,
            uuid TEXT DEFAULT '',
            link TEXT DEFAULT '',
            sub_token TEXT UNIQUE NOT NULL,
            total_gb REAL DEFAULT 0,
            used_gb REAL DEFAULT 0,
            expire_date TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            username TEXT DEFAULT '',
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS telegram_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id TEXT DEFAULT '',
            username TEXT DEFAULT '',
            name TEXT DEFAULT '',
            token TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.commit()
    db.close()


def log_action(action, details=""):
    db = get_db()

    db.execute(
        """
        INSERT INTO audit_log(action, details)
        VALUES (?, ?)
        """,
        (action, details)
    )

    db.commit()
    db.close()


init_db()
