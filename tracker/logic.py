from datetime import datetime, timedelta
from tracker.storage import (
    get_all_habits, create_habit,
    log_habit, unlog_habit, is_logged, get_logs_for_habit, save_milestone, get_milestones,
)
from tracker.streak import calculate_streak, calculate_best_streak
from tracker.database import CATEGORY_DEFAULTS

MILESTONE_THRESHOLDS = [3, 7, 14, 21, 30, 60, 100, 200, 365]


def today():
    return str(datetime.now().date())


# ── Habit CRUD ────────────────────────────────────────────────────────────────

def add_habit(name, description="", category="general", frequency="daily",
              target_value=1, unit="times", color=None, icon=None,
              days_of_week="0,1,2,3,4,5,6"):
    d = CATEGORY_DEFAULTS.get(category, CATEGORY_DEFAULTS["general"])
    return create_habit(
        name=name, description=description, category=category,
        frequency=frequency, target_value=target_value, unit=unit,
        color=color or d["color"], icon=icon or d["icon"],
        days_of_week=days_of_week,
    )


# ── Dashboard data ─────────────────────────────────────────────────────────────

def get_habits_with_status(date=None):
    if date is None:
        date = today()
    habits = get_all_habits()
    result = []
    for h in habits:
        logs = get_logs_for_habit(h["id"])
        h["streak"] = calculate_streak(logs, date)
        h["logged_today"] = is_logged(h["id"], date)
        result.append(h)
    # Incomplete first, then by streak desc
    result.sort(key=lambda x: (x["logged_today"], -x["streak"]))
    return result


# ── Logging ────────────────────────────────────────────────────────────────────

def toggle_log(habit_id, date=None):
    """Toggle today's log. Returns (logged: bool, streak: int)."""
    if date is None:
        date = today()
    if is_logged(habit_id, date):
        unlog_habit(habit_id, date)
        logs = get_logs_for_habit(habit_id)
        return False, calculate_streak(logs, date)
    else:
        log_habit(habit_id, date)
        logs = get_logs_for_habit(habit_id)
        streak = calculate_streak(logs, date)
        _check_milestones(habit_id, streak)
        return True, streak


def _check_milestones(habit_id, streak):
    existing = {m["type"] for m in get_milestones(habit_id)}
    for t in MILESTONE_THRESHOLDS:
        key = f"streak_{t}"
        if streak >= t and key not in existing:
            save_milestone(habit_id, key, streak)


# ── Stats for detail page ──────────────────────────────────────────────────────

def get_habit_stats(habit_id):
    logs = get_logs_for_habit(habit_id)
    t = today()
    streak = calculate_streak(logs, t)
    best = calculate_best_streak(logs)
    total = len(logs)

    cutoff = str(datetime.now().date() - timedelta(days=30))
    recent = [l for l in logs if l["date"] >= cutoff]
    rate = round(len(recent) / 30 * 100, 1)

    milestones = get_milestones(habit_id)
    achieved = {m["type"] for m in milestones}
    milestone_display = []
    labels = {3: "3 Days", 7: "7 Days", 14: "2 Weeks", 21: "21 Days",
              30: "30 Days", 60: "2 Months", 100: "100 Days", 200: "200 Days", 365: "1 Year"}
    for thresh in MILESTONE_THRESHOLDS:
        key = f"streak_{thresh}"
        milestone_display.append({
            "key": key,
            "label": labels[thresh],
            "achieved": key in achieved,
            "threshold": thresh,
        })

    return {
        "streak": streak,
        "best_streak": best,
        "total_completions": total,
        "completion_rate": rate,
        "milestones": milestone_display,
    }


def get_habit_calendar(habit_id, weeks=12):
    """84-cell calendar grid for heatmap."""
    from datetime import timedelta
    t = datetime.now().date()
    start = t - timedelta(weeks=weeks)
    logs = get_logs_for_habit(habit_id)
    done = {l["date"] for l in logs}

    cells = []
    cur = start
    while cur <= t:
        cells.append({"date": str(cur), "done": str(cur) in done, "wd": cur.weekday()})
        cur += timedelta(days=1)
    return cells
