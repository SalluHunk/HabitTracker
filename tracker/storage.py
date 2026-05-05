from datetime import datetime, timedelta
from tracker.database import get_connection


# ── Habits ────────────────────────────────────────────────────────────────────

def get_all_habits(include_inactive=False):
    conn = get_connection()
    q = "SELECT * FROM habits" + ("" if include_inactive else " WHERE is_active = 1") + " ORDER BY name"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows


def get_habit(habit_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM habits WHERE id = ?", (habit_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_habit(name, description="", category="general", frequency="daily",
                 target_value=1, unit="times", color="#64748b", icon="✨",
                 days_of_week="0,1,2,3,4,5,6"):
    conn = get_connection()
    now = datetime.now().isoformat()
    cur = conn.execute(
        """INSERT INTO habits
           (name, description, category, frequency, target_value, unit, color, icon, days_of_week, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (name, description, category, frequency, target_value, unit, color, icon, days_of_week, now),
    )
    habit_id = cur.lastrowid
    conn.commit()
    conn.close()
    return habit_id


def update_habit(habit_id, **kwargs):
    allowed = {"name", "description", "category", "frequency", "target_value",
               "unit", "color", "icon", "days_of_week", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sql = "UPDATE habits SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=?"
    conn = get_connection()
    conn.execute(sql, [*fields.values(), habit_id])
    conn.commit()
    conn.close()


def delete_habit(habit_id):
    conn = get_connection()
    conn.execute("DELETE FROM habits WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()


# ── Logs ──────────────────────────────────────────────────────────────────────

def log_habit(habit_id, date=None, value=1, notes=""):
    if date is None:
        date = str(datetime.now().date())
    now = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO habit_logs (habit_id, date, value, completed, notes, logged_at)
           VALUES (?,?,?,1,?,?)
           ON CONFLICT(habit_id, date) DO UPDATE SET
               value=excluded.value, completed=1,
               notes=excluded.notes, logged_at=excluded.logged_at""",
        (habit_id, date, value, notes, now),
    )
    conn.commit()
    conn.close()


def unlog_habit(habit_id, date=None):
    if date is None:
        date = str(datetime.now().date())
    conn = get_connection()
    conn.execute("DELETE FROM habit_logs WHERE habit_id=? AND date=?", (habit_id, date))
    conn.commit()
    conn.close()


def is_logged(habit_id, date=None):
    if date is None:
        date = str(datetime.now().date())
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM habit_logs WHERE habit_id=? AND date=?", (habit_id, date)
    ).fetchone()
    conn.close()
    return row is not None


def get_logs_for_habit(habit_id, limit=None):
    conn = get_connection()
    sql = "SELECT * FROM habit_logs WHERE habit_id=? ORDER BY date DESC"
    args = (habit_id,)
    if limit:
        sql += " LIMIT ?"
        args = (habit_id, limit)
    rows = [dict(r) for r in conn.execute(sql, args).fetchall()]
    conn.close()
    return rows


def get_all_logs(days=None):
    conn = get_connection()
    if days:
        cutoff = str(datetime.now().date() - timedelta(days=days))
        rows = conn.execute(
            "SELECT * FROM habit_logs WHERE date>=? ORDER BY date DESC", (cutoff,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM habit_logs ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Milestones ─────────────────────────────────────────────────────────────────

def save_milestone(habit_id, milestone_type, streak_count):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO milestones (habit_id, type, streak_count, achieved_at) VALUES (?,?,?,?)",
        (habit_id, milestone_type, streak_count, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_milestones(habit_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM milestones WHERE habit_id=? ORDER BY streak_count", (habit_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
