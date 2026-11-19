"""Entry point.

* Vercel looks for the module-level ``app`` in this file.
* Quick local test:   python app.py           (this computer only, http://127.0.0.1:5000)
* PC server (LAN):    python pc_server.py     (or start_server.bat on Windows)
* Gunicorn (Linux):   gunicorn app:app        (or wsgi:app)

The Flask debug server is OFF unless you set FLASK_DEBUG=1, because its debugger
lets anyone who can reach the port run code on your computer.
"""
from signalsleuth import create_app

app = create_app()

if __name__ == "__main__":
    import os

    from signalsleuth import db

    debug = os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes", "on")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print("=" * 60)
    print("Signal Sleuth (development server)")
    print(f"  Open        : http://{host}:{port}")
    print("  Admin login : /admin/login")
    print(f"  Default admin: {db.DEFAULT_ADMIN_USER} / {db.INITIAL_ADMIN_PASS}  (you must change it at first login)")
    print("  For classroom use on a network run:  python pc_server.py")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)
