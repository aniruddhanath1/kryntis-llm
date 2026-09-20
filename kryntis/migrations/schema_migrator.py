"""Database and SQLite Schema Migrator."""

import sqlite3
from typing import List

class SchemaMigrator:
    """Executes database schema migrations deterministically."""
    def __init__(self, db_path: str = "data/kryntis.db") -> None:
        self.db_path = db_path

    def run_migration(self, sql_statements: List[str]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for stmt in sql_statements:
                cursor.execute(stmt)
            conn.commit()
