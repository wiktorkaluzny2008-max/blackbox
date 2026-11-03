"""Demand-driven news refresh with a per-process 15 minute cooldown."""
import threading
import time

_lock = threading.Lock()
_running = False
_last_attempt = None


def request_refresh():
    global _running, _last_attempt
    with _lock:
        if _running:
            return 'refreshing'
        now = time.monotonic()
        if _last_attempt is not None and now - _last_attempt < 900:
            return 'news_unavailable'
        _running = True
        _last_attempt = now
        threading.Thread(target=_refresh, daemon=True).start()
        return 'refreshing'


def _refresh():
    global _running
    try:
        from sentiment_scanner import run_scan
        run_scan()
    except Exception:
        pass
    finally:
        with _lock:
            _running = False
