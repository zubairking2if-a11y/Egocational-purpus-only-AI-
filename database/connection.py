"""Database connection helpers."""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/offline_pentest.db")

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn
