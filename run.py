"""
run.py — start the SRMSS web app.

    python run.py

then open http://127.0.0.1:5000 and sign in (demo logins on the page):
    admin / depot123   ·   supervisor / super123   ·   clerk / clerk123
"""

from webapp.app import app

if __name__ == "__main__":
    # threaded=False keeps a single thread so the in-memory SQLite connection
    # is used safely; use_reloader=False avoids a double-start in some shells.
    app.run(debug=True, use_reloader=False, threaded=False)
