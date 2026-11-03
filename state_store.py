"""Persistent user state. Set DATABASE_URL to use Supabase Postgres."""
import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))


def _connection():
    import psycopg
    return psycopg.connect(os.environ["DATABASE_URL"], sslmode="require", prepare_threshold=None)


_lock_depth = ContextVar("blackbox_state_lock_depth", default=0)


@contextmanager
def locked():
    """Serialize all account/portfolio writers across app and scanner processes."""
    if _lock_depth.get() or not os.getenv("DATABASE_URL"):
        yield
        return
    with _connection() as conn, conn.cursor() as cur:
        cur.execute("select pg_advisory_xact_lock(786714281)")
        token = _lock_depth.set(1)
        try:
            yield
        finally:
            _lock_depth.reset(token)


def with_state_lock(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        with locked():
            return fn(*args, **kwargs)
    return wrapped


def load(kind, path):
    if not os.getenv("DATABASE_URL"):
        try:
            with open(path, encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError):
            return {}
    with _connection() as conn, conn.cursor() as cur:
        cur.execute("select payload from public.blackbox_state where kind = %s", (kind,))
        row = cur.fetchone()
        return row[0] if row else {}


def save(kind, path, data):
    if not os.getenv("DATABASE_URL"):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=1)
        os.replace(tmp, path)
        return
    from psycopg.types.json import Jsonb
    with _connection() as conn, conn.cursor() as cur:
        cur.execute("""insert into public.blackbox_state(kind, payload)
                       values (%s, %s) on conflict (kind)
                       do update set payload = excluded.payload""", (kind, Jsonb(data)))
