
import string
import random
import re
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, abort, jsonify, flash, url_for
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "url_shortener_secret_2025"
DATABASE = "urls.db"

CHARS = string.ascii_letters + string.digits        # base-62
VALID_CODE_RE = re.compile(r'^[A-Za-z0-9_-]+$')    # only alphanumeric, dash, underscore


# DB helpers 
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # enables ON DELETE CASCADE
    return conn


def init_db():
    """Create tables whether or not the DB file already exists."""
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS links (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            code       TEXT NOT NULL UNIQUE,
            original   TEXT NOT NULL,
            title      TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS clicks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id    INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
            clicked_at TEXT NOT NULL
        );
    """)
    db.commit()
    db.close()
    print("[DB] Database ready.")


def generate_code(length=6):
    return "".join(random.choices(CHARS, k=length))


#  Routes 
@app.route("/")
def index():
    db = get_db()
    links = db.execute("""
        SELECT l.*, COUNT(c.id) as total_clicks
        FROM links l
        LEFT JOIN clicks c ON c.link_id = l.id
        GROUP BY l.id
        ORDER BY l.created_at DESC
    """).fetchall()
    db.close()
    return render_template("index.html", links=links,
                           base_url=request.host_url.rstrip("/"))


@app.route("/shorten", methods=["POST"])
def shorten():
    original = request.form.get("url", "").strip()
    title    = request.form.get("title", "").strip() or None
    custom   = request.form.get("custom", "").strip()

    if not original:
        flash("Please enter a URL.", "error")
        return redirect(url_for("index"))

    if not original.startswith(("http://", "https://")):
        original = "https://" + original

    # Validate custom code if provided
    if custom:
        if not VALID_CODE_RE.match(custom):
            flash("Custom code can only contain letters, numbers, hyphens, and underscores.", "error")
            return redirect(url_for("index"))
        if len(custom) > 20:
            flash("Custom code must be 20 characters or fewer.", "error")
            return redirect(url_for("index"))

    db = get_db()

    # Check duplicate original
    existing = db.execute("SELECT code FROM links WHERE original=?", (original,)).fetchone()
    if existing:
        flash(f"Already shortened! Code: {existing['code']}", "info")
        db.close()
        return redirect(url_for("index"))

    # Check custom code not already taken
    if custom and db.execute("SELECT id FROM links WHERE code=?", (custom,)).fetchone():
        flash(f"Custom code '{custom}' is already taken. Try another.", "error")
        db.close()
        return redirect(url_for("index"))

    # Use custom code or generate a unique one
    code = custom if custom else generate_code()
    while not custom and db.execute("SELECT id FROM links WHERE code=?", (code,)).fetchone():
        code = generate_code()

    db.execute(
        "INSERT INTO links (code, original, title, created_at) VALUES (?,?,?,?)",
        (code, original, title, datetime.now().isoformat())
    )
    db.commit()
    db.close()
    flash(f"Shortened! Your link: {request.host_url}{code}", "success")
    return redirect(url_for("index"))


@app.route("/<code>")
def redirect_link(code):
    db = get_db()
    link = db.execute("SELECT * FROM links WHERE code=?", (code,)).fetchone()
    if not link:
        db.close()
        abort(404)
    db.execute("INSERT INTO clicks (link_id, clicked_at) VALUES (?,?)",
               (link["id"], datetime.now().isoformat()))
    db.commit()
    original = link["original"]
    db.close()
    return redirect(original, code=302)


@app.route("/delete/<int:link_id>", methods=["POST"])
def delete_link(link_id):
    db = get_db()
    db.execute("DELETE FROM links WHERE id=?", (link_id,))  # CASCADE deletes clicks too
    db.commit()
    db.close()
    flash("Link deleted.", "info")
    return redirect(url_for("index"))


@app.route("/stats/<code>")
def stats(code):
    db = get_db()
    link = db.execute("SELECT * FROM links WHERE code=?", (code,)).fetchone()
    if not link:
        db.close()
        abort(404)
    total = db.execute("SELECT COUNT(*) FROM clicks WHERE link_id=?", (link["id"],)).fetchone()[0]
    db.close()
    return render_template("stats.html", link=link, total=total,
                           base_url=request.host_url.rstrip("/"))


# API: time-series clicks
@app.route("/api/clicks/<code>")
def api_clicks(code):
    db = get_db()
    link = db.execute("SELECT id FROM links WHERE code=?", (code,)).fetchone()
    if not link:
        db.close()
        return jsonify({"error": "not found"}), 404

    labels, counts = [], []
    for i in range(13, -1, -1):
        day = (date.today() - timedelta(days=i)).isoformat()
        cnt = db.execute(
            "SELECT COUNT(*) FROM clicks WHERE link_id=? AND clicked_at LIKE ?",
            (link["id"], f"{day}%")
        ).fetchone()[0]
        labels.append(day[5:])   # MM-DD
        counts.append(cnt)
    db.close()
    return jsonify({"labels": labels, "clicks": counts})


@app.route("/api/top")
def api_top():
    db = get_db()
    rows = db.execute("""
        SELECT l.code, l.title, l.original, COUNT(c.id) as clicks
        FROM links l LEFT JOIN clicks c ON c.link_id = l.id
        GROUP BY l.id ORDER BY clicks DESC LIMIT 5
    """).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
