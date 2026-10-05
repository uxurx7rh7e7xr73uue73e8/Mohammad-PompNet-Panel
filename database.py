import sqlite3
from pathlib import Path

from config import DATABASE_PATH


def get_db():

    db = sqlite3.connect(
        DATABASE_PATH,
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

            protocol TEXT NOT NULL,

            link TEXT NOT NULL,

            token TEXT UNIQUE NOT NULL,

            volume_gb REAL DEFAULT 0,

            used_gb REAL DEFAULT 0,

            expire_at TEXT DEFAULT '',

            enabled INTEGER DEFAULT 1,

            created_at TEXT
            DEFAULT CURRENT_TIMESTAMP

        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS telegram_bots (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            bot_id TEXT,

            username TEXT,

            name TEXT,

            token TEXT NOT NULL,

            enabled INTEGER DEFAULT 1,

            created_at TEXT
            DEFAULT CURRENT_TIMESTAMP

        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            action TEXT NOT NULL,

            details TEXT DEFAULT '',

            created_at TEXT
            DEFAULT CURRENT_TIMESTAMP

        )
    """)

    db.commit()

    db.close()


def log_action(
    action,
    details=""
):

    db = get_db()

    db.execute(
        """
        INSERT INTO audit_log
        (action, details)
        VALUES (?, ?)
        """,
        (
            action,
            details
        )
    )

    db.commit()

    db.close()
