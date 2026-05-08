from datetime import datetime, timedelta
from collections import defaultdict
from tracker.storage import get_all_habits, get_all_logs, get_logs_for_habit
from tracker.streak import calculate_streak, calculate_best_streak


def _today():
    return str(datetime.now().date())


def dashboard_stats(user_id):
    habits = get_all_habits(user_id)
    t = _today()
    completed = best = 0
    total_logs = 0

    for h in habits:
        logs = get_logs_for_habit(user_id, h["id"])
        total_logs += len(logs)
        if any(l["date"] == t for l in logs):
            completed += 1
        s = calculate_streak(logs, t)
        if s > best:
            best = s

    n = len(habits)
    return {
        "total_habits": n,
        "completed_today": completed,
        "completion_rate": round(completed / n * 100) if n else 0,
        "best_streak": best,
        "total_logs": total_logs,
    }


def weekly_activity(user_id, habit_id=None):
    today = datetime.now().date()
    result = {str(today - timedelta(days=i)): 0 for i in range(6, -1, -1)}
    logs = get_logs_for_habit(user_id, habit_id) if habit_id else get_all_logs(user_id, days=7)
    for l in logs:
        if l["date"] in result:
            result[l["date"]] += 1
    return result


def category_breakdown(user_id):
    habits = get_all_habits(user_id)
    counts = defaultdict(int)
    for h in habits:
        counts[h["category"]] += 1
    return dict(counts)


def completion_heatmap(user_id, weeks=52):
    today = datetime.now().date()
    start = today - timedelta(weeks=weeks)
    logs = get_all_logs(user_id)

    day_counts = defaultdict(int)
    for l in logs:
        try:
            d = datetime.strptime(l["date"], "%Y-%m-%d").date()
            if d >= start:
                day_counts[str(d)] += 1
        except ValueError:
            pass

    result = []
    cur = start
    while cur <= today:
        result.append({"date": str(cur), "count": day_counts[str(cur)]})
        cur += timedelta(days=1)
    return result


def top_habits(user_id):
    habits = get_all_habits(user_id)
    t = _today()
    rows = []
    for h in habits:
        logs = get_logs_for_habit(user_id, h["id"])
        rows.append({
            **h,
            "current_streak": calculate_streak(logs, t),
            "best_streak": calculate_best_streak(logs),
            "total_completions": len(logs),
        })
    rows.sort(key=lambda x: (-x["current_streak"], -x["total_completions"]))
    return rows


def trend_data(user_id, habit_id, weeks=8):
    today = datetime.now().date()
    logs = get_logs_for_habit(user_id, habit_id)
    result = []
    for i in range(weeks - 1, -1, -1):
        ws = today - timedelta(days=today.weekday() + 7 * i)
        we = ws + timedelta(days=6)
        cnt = sum(1 for l in logs if ws <= datetime.strptime(l["date"], "%Y-%m-%d").date() <= we)
        result.append({
            "week": str(ws),
            "count": cnt,
            "label": "This week" if i == 0 else f"-{i}w",
        })
    return result
