import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "italian_lens.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    image_filename TEXT NOT NULL,
    scene_description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS phrases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
    italian TEXT NOT NULL,
    english TEXT NOT NULL,
    category TEXT
);

CREATE TABLE IF NOT EXISTS vocabulary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    italian TEXT NOT NULL,
    english TEXT NOT NULL,
    part_of_speech TEXT,
    example_it TEXT,
    example_en TEXT,
    first_capture_id INTEGER REFERENCES captures(id) ON DELETE SET NULL,
    times_seen INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    UNIQUE(italian COLLATE NOCASE)
);
"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def save_capture(image_filename, scene_description, phrases, vocabulary):
    """Persist one analyzed photo: the capture row, its extracted phrases,
    and its vocabulary (deduped/merged into the running vocabulary list)."""
    conn = get_connection()
    ts = now_iso()
    cur = conn.execute(
        "INSERT INTO captures (created_at, image_filename, scene_description) VALUES (?, ?, ?)",
        (ts, image_filename, scene_description),
    )
    capture_id = cur.lastrowid

    for p in phrases:
        conn.execute(
            "INSERT INTO phrases (capture_id, italian, english, category) VALUES (?, ?, ?, ?)",
            (capture_id, p["italian"], p["english"], p.get("category")),
        )

    for v in vocabulary:
        existing = conn.execute(
            "SELECT id, times_seen FROM vocabulary WHERE italian = ? COLLATE NOCASE",
            (v["italian"],),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE vocabulary SET times_seen = ?, last_seen_at = ? WHERE id = ?",
                (existing["times_seen"] + 1, ts, existing["id"]),
            )
        else:
            conn.execute(
                """INSERT INTO vocabulary
                   (italian, english, part_of_speech, example_it, example_en,
                    first_capture_id, times_seen, created_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)""",
                (
                    v["italian"], v["english"], v.get("part_of_speech"),
                    v.get("example_it"), v.get("example_en"),
                    capture_id, ts, ts,
                ),
            )

    conn.commit()
    conn.close()
    return capture_id


def list_captures():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM captures ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_capture(capture_id):
    conn = get_connection()
    capture = conn.execute(
        "SELECT * FROM captures WHERE id = ?", (capture_id,)
    ).fetchone()
    if not capture:
        conn.close()
        return None
    phrases = conn.execute(
        "SELECT * FROM phrases WHERE capture_id = ? ORDER BY id", (capture_id,)
    ).fetchall()
    conn.close()
    result = dict(capture)
    result["phrases"] = [dict(p) for p in phrases]
    return result


def list_vocabulary():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM vocabulary ORDER BY last_seen_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_vocabulary(vocab_id):
    conn = get_connection()
    conn.execute("DELETE FROM vocabulary WHERE id = ?", (vocab_id,))
    conn.commit()
    conn.close()
