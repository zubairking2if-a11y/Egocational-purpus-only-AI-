"""Relational engine helper (placeholder)."""
def init_db(conn):
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS projects (id INTEGER PRIMARY KEY, name TEXT)''')
    conn.commit()
