"""Schema setup. Postgres (prod) and SQLite (local dev) both supported."""
from tracker.db import execute_script, IS_POSTGRES

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


_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    google_id     TEXT UNIQUE,
    name          TEXT,
    avatar_url    TEXT,
    created_at    TIMESTAMP DEFAULT NOW(),
    last_login    TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habits (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);

CREATE TABLE IF NOT EXISTS habit_logs (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    habit_id   INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    value      INTEGER DEFAULT 1,
    completed  INTEGER DEFAULT 1,
    notes      TEXT    DEFAULT '',
    logged_at  TEXT    NOT NULL,
    UNIQUE(habit_id, date)
);
CREATE INDEX IF NOT EXISTS idx_logs_user ON habit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_habit ON habit_logs(habit_id);

CREATE TABLE IF NOT EXISTS milestones (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    habit_id     INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    type         TEXT    NOT NULL,
    streak_count INTEGER DEFAULT 0,
    achieved_at  TEXT    NOT NULL,
    UNIQUE(habit_id, type)
);

CREATE TABLE IF NOT EXISTS password_resets (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash   TEXT    NOT NULL,
    expires_at  TEXT    NOT NULL,
    used        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_resets_user ON password_resets(user_id);
"""

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    google_id     TEXT UNIQUE,
    name          TEXT,
    avatar_url    TEXT,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP,
    last_login    TEXT
);

CREATE TABLE IF NOT EXISTS habits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
CREATE INDEX IF NOT EXISTS idx_habits_user ON habits(user_id);

CREATE TABLE IF NOT EXISTS habit_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    habit_id   INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date       TEXT    NOT NULL,
    value      INTEGER DEFAULT 1,
    completed  INTEGER DEFAULT 1,
    notes      TEXT    DEFAULT '',
    logged_at  TEXT    NOT NULL,
    UNIQUE(habit_id, date)
);
CREATE INDEX IF NOT EXISTS idx_logs_user ON habit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_habit ON habit_logs(habit_id);

CREATE TABLE IF NOT EXISTS milestones (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    habit_id     INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    type         TEXT    NOT NULL,
    streak_count INTEGER DEFAULT 0,
    achieved_at  TEXT    NOT NULL,
    UNIQUE(habit_id, type)
);

CREATE TABLE IF NOT EXISTS password_resets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash   TEXT    NOT NULL,
    expires_at  TEXT    NOT NULL,
    used        INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_resets_user ON password_resets(user_id);
"""


def init_db():
    execute_script(_PG_SCHEMA if IS_POSTGRES else _SQLITE_SCHEMA)
