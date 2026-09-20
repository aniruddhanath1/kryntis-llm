"""Initial database migration v1."""

MIGRATION_V1_SQL = [
    """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        created_at REAL,
        metadata TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp REAL,
        FOREIGN KEY(session_id) REFERENCES sessions(session_id)
    );
    """
]
