"""Project repository (simple SQLite-backed DAO)."""
from .connection import get_connection

class ProjectRepo:
    def list(self):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM projects")
        return cur.fetchall()
