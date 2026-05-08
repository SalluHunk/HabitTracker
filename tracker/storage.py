"""Per-user data layer. Every query filters by user_id."""
from datetime import datetime, timedelta
from tracker.db import query_one, query_all, execute, insert_returning_id


# ── Habits ────────────────────────────────────────────────────────────────────

def get_all_habits(user_id, include_inactive=False):
    q = "SELECT * FROM habits WHERE user_id = ?"
    if not include_inactive:
        q += " AND is_active = 1"
    q += " ORDER BY name"
    return query_all(q, (user_id,))


def get_habit(user_id, habit_id):
    return query_one(
        "SELECT * FROM habits WHERE id = ? AND user_id = ?",
        (habit_id, user_id),
    )


def create_habit(user_id, name, description="", category="general", frequency="daily",
                 target_value=1, unit="times", color="#64748b", icon="✨",
                 days_of_week="0,1,2,3,4,5,6"):
    now = datetime.now().isoformat()
    return insert_returning_id(
        """INSERT INTO habits
           (user_id, name, description, category, frequency, target_value, unit, color, icon, days_of_week, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, name, description, category, frequency, target_value, unit, color, icon, days_of_week, now),
    )


def update_habit(user_id, habit_id, **kwargs):
    allowed = {"name", "description", "category", "frequency", "target_value",
               "unit", "color", "icon", "days_of_week", "is_active"}
    fields = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not fields:
        return
    sql = "UPDATE habits SET " + ", ".join(f"{k}=?" for k in fields) + " WHERE id=? AND user_id=?"
    execute(sql, [*fields.values(), habit_id, user_id])


def delete_habit(user_id, habit_id):
    execute("DELETE FROM habits WHERE id=? AND user_id=?", (habit_id, user_id))


# ── Logs ──────────────────────────────────────────────────────────────────────

def log_habit(user_id, habit_id, date=None, value=1, notes=""):
    if date is None:
        date = str(datetime.now().date())
    now = datetime.now().isoformat()
    execute(
        """INSERT INTO habit_logs (user_id, habit_id, date, value, completed, notes, logged_at)
           VALUES (?,?,?,?,1,?,?)
           ON CONFLICT(habit_id, date) DO UPDATE SET
               value=EXCLUDED.value, completed=1,
               notes=EXCLUDED.notes, logged_at=EXCLUDED.logged_at""",
        (user_id, habit_id, date, value, notes, now),
    )


def unlog_habit(user_id, habit_id, date=None):
    if date is None:
        date = str(datetime.now().date())
    execute(
        "DELETE FROM habit_logs WHERE habit_id=? AND date=? AND user_id=?",
        (habit_id, date, user_id),
    )


def is_logged(user_id, habit_id, date=None):
    if date is None:
        date = str(datetime.now().date())
    row = query_one(
        "SELECT id FROM habit_logs WHERE habit_id=? AND date=? AND user_id=?",
        (habit_id, date, user_id),
    )
    return row is not None


def get_logs_for_habit(user_id, habit_id, limit=None):
    sql = "SELECT * FROM habit_logs WHERE habit_id=? AND user_id=? ORDER BY date DESC"
    args = [habit_id, user_id]
    if limit:
        sql += " LIMIT ?"
        args.append(limit)
    return query_all(sql, tuple(args))


def get_all_logs(user_id, days=None):
    if days:
        cutoff = str(datetime.now().date() - timedelta(days=days))
        return query_all(
            "SELECT * FROM habit_logs WHERE user_id=? AND date>=? ORDER BY date DESC",
            (user_id, cutoff),
        )
    return query_all(
        "SELECT * FROM habit_logs WHERE user_id=? ORDER BY date DESC",
        (user_id,),
    )


# ── Milestones ─────────────────────────────────────────────────────────────────

def save_milestone(user_id, habit_id, milestone_type, streak_count):
    execute(
        """INSERT INTO milestones (user_id, habit_id, type, streak_count, achieved_at)
           VALUES (?,?,?,?,?)
           ON CONFLICT(habit_id, type) DO NOTHING""",
        (user_id, habit_id, milestone_type, streak_count, datetime.now().isoformat()),
    )


def get_milestones(user_id, habit_id):
    return query_all(
        "SELECT * FROM milestones WHERE habit_id=? AND user_id=? ORDER BY streak_count",
        (habit_id, user_id),
    )
