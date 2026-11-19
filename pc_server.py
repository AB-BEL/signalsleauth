"""Signal Sleuth PC server (production-grade, runs on your own computer).

    python pc_server.py            (Windows: double-click start_server.bat)

Serves the whole app (students, admin, mobile API) with Waitress, which is
stable and thread-based, unlike Flask's built-in development server.

Settings (in .env, all optional):
    HOST=0.0.0.0        listen on the network (use 127.0.0.1 for this PC only)
    PORT=8000
    THREADS=8           simultaneous requests
    TRUST_PROXY=0       set 1 ONLY when a tunnel/reverse proxy on this PC forwards
                        traffic (Cloudflare Tunnel, nginx); makes client IPs correct
"""
import os
import socket
import sys

# Friendly console on Windows (emoji-free, but keep UTF-8 safe)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def lan_addresses():
    """Best-effort list of this computer's LAN IPv4 addresses."""
    found = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127.") and ip not in found:
                found.append(ip)
    except OSError:
        pass
    try:  # the address used for outgoing traffic is usually the right one
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127.") and ip not in found:
            found.insert(0, ip)
    except OSError:
        pass
    return found


def main():
    try:
        import waitress
    except ImportError:
        print("Waitress is not installed. Run:  pip install -r requirements-pc.txt")
        return 1

    from signalsleuth import config, db  # importing config loads .env, so do it before reading settings

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    threads = int(os.environ.get("THREADS", "8"))
    trust_proxy = os.environ.get("TRUST_PROXY", "0").strip().lower() in ("1", "true", "yes", "on")

    try:
        config.validate()
    except RuntimeError as exc:
        print("\nSETUP PROBLEM:", exc)
        print("Run setup_windows.bat (or: python scripts/pc_setup.py) first.")
        return 1

    ok, err = db.ping()
    if not ok:
        print("\nCannot reach the database:", err)
        print("Is MariaDB/MySQL running? Check MYSQL_* values in .env,")
        print("then run:  python scripts/pc_setup.py --check")
        return 1

    from app import app  # creates the app and makes sure the schema exists

    print("=" * 64)
    print(" Signal Sleuth PC server is running")
    print("-" * 64)
    print(f"  On this computer : http://localhost:{port}")
    if host in ("0.0.0.0", "::"):
        ips = lan_addresses()
        for ip in ips:
            print(f"  Students (LAN)   : http://{ip}:{port}")
        if not ips:
            print("  (could not detect the LAN address; run  ipconfig  to find it)")
    if config.ORIGIN_SECRET:
        print("  Internet mode    : ON (tunnel traffic must come from your Vercel proxy project)")
        if not trust_proxy:
            print("  WARNING          : set TRUST_PROXY=1 in .env so visitor IPs are recorded correctly")
    print(f"  Admin login      : /admin/login   (user: {db.DEFAULT_ADMIN_USER})")
    print(f"  Storage          : {config.UPLOAD_DIR}")
    print("  Stop the server  : press Ctrl+C or close this window")
    print("=" * 64, flush=True)

    kwargs = dict(
        host=host,
        port=port,
        threads=threads,
        max_request_body_size=config.MAX_CONTENT_LENGTH + 1024 * 1024,
        ident="SignalSleuth",
        channel_timeout=120,
    )
    if trust_proxy:
        kwargs.update(trusted_proxy="127.0.0.1", trusted_proxy_headers={"x-forwarded-for", "x-forwarded-proto"},
                      clear_untrusted_proxy_headers=True)
    waitress.serve(app, **kwargs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
