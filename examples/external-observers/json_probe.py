"""Project a JSON invoice document into the common comparison value."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from probe_protocol import MAX_BYTES, invoice_value, run


def capture() -> dict[str, Any]:
    source = Path("invoices.json")
    try:
        with source.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return invoice_value([], state="missing")
    if len(data) > MAX_BYTES:
        raise ValueError("source limit")
    document = json.loads(data)
    invoices = document["invoices"]
    if not isinstance(invoices, list):
        raise ValueError("invoice list")
    # Storage metadata and object-key/row order are deliberately not semantic.
    return invoice_value([[item["invoice_id"], item["total_cents"]] for item in invoices])


if __name__ == "__main__":
    raise SystemExit(run(capture))
