"""
run.py — start the SRMSS web app.

Local use:
    python run.py
then open http://127.0.0.1:5000 and sign in (demo logins on the page):
    admin / depot123   ·   supervisor / super123   ·   clerk / clerk123

When hosted (e.g. Render), the platform sets the PORT environment variable and
the app binds to 0.0.0.0 so it is reachable publicly.
"""

import os

from webapp.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # host 0.0.0.0 makes it reachable when hosted; locally use 127.0.0.1:5000.
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
