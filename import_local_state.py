"""One-time import of existing local accounts and portfolios into a new database.

Run only after applying supabase_schema.sql and setting DATABASE_URL and APP_SECRET.
Refuses to replace nonempty database state.
"""
import os
from pathlib import Path
from state_store import load, save

HERE = Path(__file__).resolve().parent
if not os.getenv("DATABASE_URL") or not os.getenv("APP_SECRET"):
    raise SystemExit("Set DATABASE_URL and APP_SECRET first")
payloads = {}
for kind, filename in (("accounts", "app_accounts.json"), ("users", "app_users.json")):
    path = HERE / "logs" / filename
    if load(kind, str(path)):
        raise SystemExit(f"Database {kind} already contains data; import stopped")
    import json
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    payloads[kind] = (str(path), data)
for kind, (path, data) in payloads.items():
    save(kind, path, data)
    print(f"Imported {len(data)} {kind}")
