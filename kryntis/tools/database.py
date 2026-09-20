"""
Database Tool — executes SQL queries against SQLite or in-memory analytical databases with workspace boundary enforcement.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from kryntis.tools.file_system import _resolve_safe_workspace_path
from kryntis.tools.tool_registry import ToolDefinition, ToolParameter


def execute_sql_query(query: str, db_path: str = ":memory:") -> dict[str, Any]:
    """
    Execute SQL query and return columns and rows.

    Args:
        query: SQL statement (SELECT, CREATE, INSERT, etc.).
        db_path: Path to SQLite DB file or ':memory:' for transient analysis.

    Returns:
        Dictionary with columns, rows, and affected row count.
    """
    try:
        resolved_db: str
        if db_path != ":memory:":
            safe_p = _resolve_safe_workspace_path(db_path)
            resolved_db = str(safe_p)
        else:
            resolved_db = ":memory:"

        conn = sqlite3.connect(resolved_db)
        cursor = conn.cursor()
        cursor.execute(query)

        if cursor.description:
            columns = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
            conn.commit()
            conn.close()
            return {
                "columns": columns,
                "rows": [list(r) for r in rows],
                "row_count": len(rows),
                "status": "success",
            }
        else:
            rowcount = cursor.rowcount
            conn.commit()
            conn.close()
            return {
                "affected_rows": rowcount,
                "status": "success",
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


TOOL_DATABASE_SQL = ToolDefinition(
    name="sql_query",
    description="Executes a SQL query against an analytical database or SQLite file.",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            description="The SQL query statement to execute.",
            required=True,
        ),
        ToolParameter(
            name="db_path",
            type="string",
            description="Path to SQLite DB file (or ':memory:' for transient queries).",
            required=False,
            default=":memory:",
        ),
    ],
    handler=execute_sql_query,
    category="database",
)
