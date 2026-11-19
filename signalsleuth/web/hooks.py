"""Template filters, context processor and response hooks."""
import hmac
import ipaddress
import os

from flask import Response, g, request, session

from .. import config, db
from ..services import monetization


def _ymd(val):
    """Safe YYYY-MM-DD from date/datetime/str."""
    if val is None or val == "":
        return ""
    return str(val)[:10]


def _ymdt(val):
    """Safe short datetime display."""
    if val is None or val == "":
        return ""
    return str(val)[:16].replace("T", " ")


def inject_branding():
    """Course-agnostic labels + future ad flags for all templates."""
    try:
        app_name = db.get_setting("app_name", None) or os.environ.get("APP_NAME") or "Signal Sleuth"
        course_name = db.get_setting("course_name", None) or os.environ.get("COURSE_NAME") or "Your course"
    except Exception:
        app_name, course_name = "Signal Sleuth", "Your course"
    return {
        "APP_NAME": app_name,
        "COURSE_NAME": course_name,
        "ADS_ENABLED": monetization.ads_enabled(),
        "AD_SLOT_DASHBOARD": monetization.ad_slot_html("dashboard") if monetization.ads_enabled() else "",
        "MONETIZATION": monetization.player_reward_policy(),
    }


def add_no_cache_headers(response):
    """Never cache player-specific pages (avoids User A seeing User B after login switch)."""
    path = request.path or ""
    sensitive = (
        path.startswith("/dashboard")
        or path.startswith("/play")
        or path.startswith("/game-file")
        or path.startswith("/api/")
        or path.startswith("/admin")
        or path.startswith("/level-feedback")
        or path.startswith("/chapter-feedback")
        or session.get("user_id")
        or session.get("admin_id")
    )
    if sensitive:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Vary"] = "Cookie, Authorization"
    return response


def _is_private_ip(addr):
    try:
        ip = ipaddress.ip_address((addr or "").strip())
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def origin_guard():
    """Internet mode: only the Vercel front (which knows ORIGIN_SECRET) may use the tunnel.

    A request counts as "through the tunnel" when it carries proxy headers or does not come
    from a private/loopback address. Students on the LAN connect directly and are not affected.
    """
    g.client_ip = None
    secret = config.ORIGIN_SECRET
    if not secret:
        return None
    supplied = request.headers.get("X-Origin-Secret", "")
    secret_ok = bool(supplied) and hmac.compare_digest(supplied.encode(), secret.encode())
    if secret_ok:
        # Request came from the Vercel front: trust the client IP it reports.
        g.client_ip = (request.headers.get("X-Client-IP") or "").strip()[:64] or None
        return None
    via_proxy = bool(
        request.headers.get("CF-Connecting-IP")
        or request.headers.get("X-Forwarded-For")
        or request.headers.get("Forwarded")
        or not _is_private_ip(request.remote_addr)
    )
    if via_proxy:
        return Response("Forbidden", status=403, mimetype="text/plain")
    return None  # direct LAN / local request


def register(app):
    app.before_request(origin_guard)
    app.add_template_filter(_ymd, "ymd")
    app.add_template_filter(_ymdt, "ymdt")
    app.context_processor(inject_branding)
    app.after_request(add_no_cache_headers)
