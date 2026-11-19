"""Tiny in-memory login throttle (brute-force protection).

Counts failed attempts per (scope, client IP, account name) inside a sliding
window and blocks further tries for a short time. It lives in process memory,
which is exactly right for a single PC server; on serverless hosts each
instance keeps its own counter, which still slows guessing down.
"""
import threading
import time

from flask import g, request

from .. import config

MAX_FAILURES = 8          # failed attempts allowed ...
WINDOW_SECONDS = 10 * 60  # ... inside this window
LOCK_SECONDS = 5 * 60     # then blocked for this long

_lock = threading.Lock()
_state = {}  # key -> {"fails": [timestamps], "blocked_until": float}


def _key(scope, identity):
    # X-Forwarded-For is client-controlled, so it is only trusted on Vercel (which sets it).
    # Behind a tunnel on a PC server, pc_server.py (TRUST_PROXY=1) makes remote_addr the real client.
    if getattr(g, "client_ip", None):
        ip = g.client_ip  # verified by origin_guard (set only when the Vercel front sent the secret)
    elif config.IS_VERCEL:
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip()
    else:
        ip = request.remote_addr or ""
    return f"{scope}|{ip}|{(identity or '').strip().lower()}"


def seconds_blocked(scope, identity):
    """0 if the caller may try; otherwise seconds left until they may retry."""
    now = time.time()
    with _lock:
        st = _state.get(_key(scope, identity))
        if st and st["blocked_until"] > now:
            return int(st["blocked_until"] - now) + 1
    return 0


def record_failure(scope, identity):
    now = time.time()
    with _lock:
        st = _state.setdefault(_key(scope, identity), {"fails": [], "blocked_until": 0.0})
        st["fails"] = [t for t in st["fails"] if now - t < WINDOW_SECONDS] + [now]
        if len(st["fails"]) >= MAX_FAILURES:
            st["blocked_until"] = now + LOCK_SECONDS
            st["fails"] = []
        if len(_state) > 5000:  # keep memory bounded
            for k in [k for k, v in _state.items() if v["blocked_until"] < now and not v["fails"]][:1000]:
                _state.pop(k, None)


def record_success(scope, identity):
    with _lock:
        _state.pop(_key(scope, identity), None)


def reset_all():
    """For tests."""
    with _lock:
        _state.clear()
