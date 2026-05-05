import sqlite3
import os
import json
import shutil

DB_PATH = "data/habits.db"

CATEGORY_DEFAULTS = {
    "health":       {"color": "#10b981", "icon": "💊"},
    "fitness":      {"color": "#f59e0b", "icon": "💪"},
    "work":         {"color": "#6366f1", "icon": "💼"},
    "learning":     {"color": "#3b82f6", "icon": "📚"},
    "mindfulness":  {"color": "#8b5cf6", "icon": "🧘"},
    "social":       {"color": "#ec4899", "icon": "👥"},
    "finance":      {"color": "#14b8a6", "icon": "💰"},
    "general":      {"color": "#64748b", "icon": "✨"},
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    os.makedirs("data", exist_ok=True)
    conn = get_connection()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS habits (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            description   TEXT    DEFAULT '',
            category      TEXT    DEFAULT 'general',
            frequency     TEXT    DEFAULT 'daily',
            target_value  INTEGER DEFAULT 1,
            unit          TEXT    DEFAULT 'times',
            color         TEXT    DEFAULT '#64748b',
            icon          TEXT    DEFAULT '✨',
            days_of_week  TEXT    DEFAULT '0,1,2,3,4,5,6',
            created_at    TEXT    NOT NULL,
            is_active     INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS habit_logs (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id   INTEGER NOT NULL,
            date       TEXT    NOT NULL,
            value      INTEGER DEFAULT 1,
            completed  INTEGER DEFAULT 1,
            notes      TEXT    DEFAULT '',
            logged_at  TEXT    NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
            UNIQUE(habit_id, date)
        );

        CREATE TABLE IF NOT EXISTS milestones (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id     INTEGER NOT NULL,
            type         TEXT    NOT NULL,
            streak_count INTEGER DEFAULT 0,
            achieved_at  TEXT    NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE,
            UNIQUE(habit_id, type)
        );
    """)
    conn.commit()
    conn.close()
    _migrate_json()


def _migrate_json():
    json_path = "data/habits.json"
    done_path = "data/habits.json.migrated"
    if not os.path.exists(json_path) or os.path.exists(done_path):
        return
    try:
        with open(json_path) as f:
            entries = json.load(f)
        if not entries:
            return

        conn = get_connection()
        c = conn.cursor()
        habit_map = {}

        for entry in entries:
            name = entry["habit"]
            if name in habit_map:
                continue
            nl = name.lower()
            if any(w in nl for w in ["gym", "exercise", "workout", "run", "walk", "fitness"]):
                cat = "fitness"
            elif any(w in nl for w in ["eat", "sleep", "water", "health", "medic", "diet"]):
                cat = "health"
            elif any(w in nl for w in ["read", "study", "learn", "book", "course"]):
                cat = "learning"
            elif any(w in nl for w in ["meditat", "mindful", "pray", "chant", "breathe"]):
                cat = "mindfulness"
            elif any(w in nl for w in ["work", "task", "project", "meeting", "email"]):
                cat = "work"
            else:
                cat = "general"

            d = CATEGORY_DEFAULTS.get(cat, CATEGORY_DEFAULTS["general"])
            c.execute(
                "INSERT OR IGNORE INTO habits (name, category, color, icon, created_at) VALUES (?,?,?,?,?)",
                (name, cat, d["color"], d["icon"], entry["date"]),
            )
            c.execute("SELECT id FROM habits WHERE name = ?", (name,))
            row = c.fetchone()
            if row:
                habit_map[name] = row[0]

        for entry in entries:
            hid = habit_map.get(entry["habit"])
            if hid:
                c.execute(
                    """INSERT OR IGNORE INTO habit_logs (habit_id, date, value, completed, logged_at)
                       VALUES (?,?,?,1,?)""",
                    (hid, entry["date"], entry["value"], entry["date"] + "T00:00:00"),
                )

        conn.commit()
        conn.close()
        shutil.copy(json_path, done_path)
        print(f"[HabitFlow] Migrated {len(entries)} entries from habits.json to SQLite")
    except Exception as e:
        print(f"[HabitFlow] Migration warning: {e}")
