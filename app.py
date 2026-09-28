"""
AASTMT — Arab Academy for Science, Technology & Maritime Transport
Single-file Flask backend (frontend lives in index.html, served as a static file).

Run:
    pip install flask
    python app.py
Then open http://127.0.0.1:5000

Endpoints
---------
GET  /                  -> serves index.html
GET  /api/health        -> liveness check
GET  /api/colleges      -> list of colleges
GET  /api/stats         -> institution stats (founded, campuses, nations...)
POST /api/admission     -> submit an admission application
GET  /api/applications  -> list submitted applications (admin/demo)
"""

from __future__ import annotations

import os
import re
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, abort
from flask import render_template_string  # noqa: F401  (kept for future templating)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
DB_FILE = BASE_DIR / "applications.db"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder=None)  # we serve the single HTML manually
app.config["JSON_SORT_KEYS"] = False
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # 64 KB body limit — small form payload

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def db_init() -> None:
    with db_connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                reference     TEXT UNIQUE NOT NULL,
                first_name    TEXT NOT NULL,
                last_name     TEXT NOT NULL,
                email         TEXT NOT NULL,
                phone         TEXT NOT NULL,
                country       TEXT NOT NULL,
                college       TEXT NOT NULL,
                message       TEXT,
                ip            TEXT,
                user_agent    TEXT,
                created_at    TEXT NOT NULL
            )
            """
        )
        conn.commit()


db_init()


# ---------------------------------------------------------------------------
# Static data (mirrors the frontend's seed list, but served as JSON)
# ---------------------------------------------------------------------------
COLLEGES = [
    {"code": "C-01", "name": "Maritime Transport & Technology",
     "desc": "Training future marine officers, marine engineers, and port operations leaders with full bridge & engine simulators.",
     "tags": ["Navigation", "Marine Eng.", "Ports"]},
    {"code": "C-02", "name": "Engineering & Technology",
     "desc": "Mechanical, electrical, civil, architectural, and computer engineering — accredited programs with industry partnerships.",
     "tags": ["Mech.", "Civil", "Comp."]},
    {"code": "C-03", "name": "International Transport & Logistics",
     "desc": "Supply chains, freight forwarding, customs, and global trade — preparing the next generation of logistics leaders.",
     "tags": ["Supply", "Trade", "Customs"]},
    {"code": "C-04", "name": "Computing, AI & Information Technology",
     "desc": "AI, data science, cybersecurity, and software engineering — built for the post-quantum era.",
     "tags": ["AI", "Cybersec.", "Data"]},
    {"code": "C-05", "name": "Management & Technology",
     "desc": "Business administration, finance, marketing, and entrepreneurship with a regional focus.",
     "tags": ["MBA", "Finance", "Marketing"]},
    {"code": "C-06", "name": "Pharmacy & Drug Manufacturing",
     "desc": "Modern pharmaceutical sciences with research labs and clinical training facilities.",
     "tags": ["Pharma", "Research"]},
    {"code": "C-07", "name": "Medicine & Dentistry",
     "desc": "AASTMT-operated hospitals and clinics supporting hands-on medical education.",
     "tags": ["MBBS", "Dental"]},
    {"code": "C-08", "name": "Languages, Media & Law",
     "desc": "Translation, international media, communication, and a full law faculty serving the regional market.",
     "tags": ["Law", "Media", "Languages"]},
]

STATS = {
    "founded": 1972,
    "campuses": ["Alexandria (HQ)", "Cairo", "Alamein"],
    "arab_league_members": 22,
    "colleges": len(COLLEGES),
    "domains": ["Maritime", "Engineering", "AI", "Logistics", "Medicine", "Law", "Languages"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[+0-9][0-9\s\-()]{7,}$")
ALLOWED_COUNTRIES = {
    "Egypt", "Saudi Arabia", "UAE", "Kuwait", "Qatar", "Bahrain", "Oman", "Jordan",
    "Lebanon", "Iraq", "Palestine", "Sudan", "Libya", "Tunisia", "Algeria", "Morocco",
    "Mauritania", "Yemen", "Syria", "Somalia", "Comoros", "Djibouti",
}
COLLEGE_NAMES = {c["name"] for c in COLLEGES}


def gen_reference() -> str:
    # AASTMT-YYYYMMDD-XXXXXX
    return "AASTMT-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()


def client_ip() -> str:
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"


def json_error(msg: str, status: int = 400):
    return jsonify({"ok": False, "error": msg}), status


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    if not INDEX_FILE.exists():
        abort(500, description="index.html not found next to app.py")
    # send_from_directory needs the directory, not the file
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/favicon.ico")
def favicon():
    # Tiny inline SVG favicon — neon 'A' on transparent
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#00f0ff"/><stop offset="1" stop-color="#ff006e"/>'
        '</linearGradient></defs>'
        '<rect width="64" height="64" rx="12" fill="#05060a"/>'
        '<path d="M14 50 L32 12 L50 50 M22 36 L42 36" stroke="url(#g)" stroke-width="6" '
        'stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
        '</svg>'
    )
    from flask import Response
    return Response(svg, mimetype="image/svg+xml")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "aastmt", "ts": datetime.now(timezone.utc).isoformat()})


@app.route("/api/colleges", methods=["GET"])
def api_colleges():
    return jsonify({"ok": True, "count": len(COLLEGES), "colleges": COLLEGES})


@app.route("/api/stats", methods=["GET"])
def api_stats():
    return jsonify({"ok": True, "stats": STATS})


@app.route("/api/admission", methods=["POST"])
def api_admission():
    data = request.get_json(silent=True) or {}
    required = ["firstName", "lastName", "email", "phone", "country", "college"]
    missing = [k for k in required if not str(data.get(k, "")).strip()]
    if missing:
        return json_error("Missing required fields: " + ", ".join(missing), 400)

    first = str(data["firstName"]).strip()
    last = str(data["lastName"]).strip()
    email = str(data["email"]).strip()
    phone = str(data["phone"]).strip()
    country = str(data["country"]).strip()
    college = str(data["college"]).strip()
    message = str(data.get("message", "")).strip()

    # Length caps to keep DB tidy
    if len(first) > 60 or len(last) > 60:
        return json_error("Name fields are too long.", 400)
    if not EMAIL_RE.match(email):
        return json_error("Invalid email address.", 400)
    if len(email) > 120:
        return json_error("Email is too long.", 400)
    if not PHONE_RE.match(phone):
        return json_error("Invalid phone number.", 400)
    if country not in ALLOWED_COUNTRIES:
        return json_error("Country must be an Arab League member state.", 400)
    if college not in COLLEGE_NAMES:
        return json_error("Unknown college selection.", 400)
    if len(message) > 2000:
        return json_error("Message is too long (max 2000 chars).", 400)

    ref = gen_reference()
    now = datetime.now(timezone.utc).isoformat()
    try:
        with db_connect() as conn:
            conn.execute(
                """INSERT INTO applications
                   (reference, first_name, last_name, email, phone, country, college, message,
                    ip, user_agent, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ref, first, last, email, phone, country, college, message,
                 client_ip(), (request.headers.get("User-Agent") or "")[:255], now),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        # extremely unlikely (reference collision) — retry once
        ref = gen_reference()
        with db_connect() as conn:
            conn.execute(
                """INSERT INTO applications
                   (reference, first_name, last_name, email, phone, country, college, message,
                    ip, user_agent, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ref, first, last, email, phone, country, college, message,
                 client_ip(), (request.headers.get("User-Agent") or "")[:255], now),
            )
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        return json_error("Database error: " + str(exc), 500)

    return jsonify({
        "ok": True,
        "ref": ref,
        "received_at": now,
        "message": "Application received. The admissions office will contact you shortly."
    })


@app.route("/api/applications", methods=["GET"])
def api_applications():
    """Demo/admin endpoint — list recent applications (no auth by default)."""
    limit = max(1, min(int(request.args.get("limit", 25)), 200))
    with db_connect() as conn:
        rows = conn.execute(
            "SELECT reference, first_name, last_name, email, country, college, created_at "
            "FROM applications ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return jsonify({
        "ok": True,
        "count": len(rows),
        "applications": [dict(r) for r in rows],
    })


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return json_error("Not found", 404)
    return send_from_directory(BASE_DIR, "index.html")  # SPA-style fallback


@app.errorhandler(500)
def server_error(e):
    return json_error("Server error: " + str(e), 500)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"\n  AASTMT server running on http://{host}:{port}\n")
    app.run(host=host, port=port, debug=False, use_reloader=False)
