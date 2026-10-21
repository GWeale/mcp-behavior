"""Read the same invoice projection from SQLite without a core import."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from probe_protocol import MAX_ROWS, invoice_value, run


def capture() -> dict[str, Any]:
    source = Path("invoices.sqlite").resolve()
    if not source.exists():
        return invoice_value([], state="missing")
    with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True, timeout=1)) as connection:
        connection.execute("PRAGMA query_only = ON")
        cursor = connection.execute(
            "SELECT invoice_id, total_cents FROM invoices "
            "ORDER BY invoice_id COLLATE BINARY LIMIT 1001"
        )
        rows = cursor.fetchmany(MAX_ROWS + 1)
    return invoice_value([list(row) for row in rows])


if __name__ == "__main__":
    raise SystemExit(run(capture))
