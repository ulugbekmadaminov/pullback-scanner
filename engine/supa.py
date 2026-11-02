"""Supabase'ga yozish (ixtiyoriy). SUPABASE_URL va SUPABASE_SERVICE_KEY sirlari bo'lsa ishlaydi.

Service role kaliti faqat GitHub Actions sirlarida turadi — ilovaga hech qachon tushmaydi.
"""
from __future__ import annotations

import os

from .data import clean


def _post(table: str, rows: list[dict], on_conflict: str) -> None:
    import requests
    url, key = os.environ["SUPABASE_URL"].rstrip("/"), os.environ["SUPABASE_SERVICE_KEY"]
    r = requests.post(f"{url}/rest/v1/{table}?on_conflict={on_conflict}", json=clean(rows), timeout=60,
                      headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                               "Prefer": "resolution=merge-duplicates,return=minimal"})
    if r.status_code >= 300:
        raise RuntimeError(f"{table}: {r.status_code} {r.text[:200]}")


def push(summary: dict, rows: list[dict], watch: dict, book: dict, learn: dict) -> None:
    if not (os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        return
    d = summary["date"]
    _post("engine_snapshots", [
        {"day": d, "kind": "summary", "data": summary},
        {"day": d, "kind": "scores", "data": rows},
        {"day": d, "kind": "watchlist", "data": watch},
        {"day": d, "kind": "portfolio", "data": {k: book[k] for k in ("equity", "positions", "trades", "protection")
                                                  if k in book}},
        {"day": d, "kind": "learn", "data": learn},
    ], "day,kind")
    print("Supabase: kunlik natija yozildi")
