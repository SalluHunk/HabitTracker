import io
import csv
import json
from datetime import datetime

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_file,
)

from tracker.database import init_db, CATEGORY_DEFAULTS
from tracker.logic import (
    add_habit, get_habits_with_status, toggle_log,
    get_habit_stats, get_habit_calendar,
)
from tracker.storage import (
    get_all_habits, get_habit, update_habit, delete_habit,
    get_logs_for_habit, get_all_logs,
)
from tracker.analytics import (
    dashboard_stats, weekly_activity, category_breakdown,
    completion_heatmap, top_habits, trend_data,
)

app = Flask(__name__)
init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _greeting():
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    habits = get_habits_with_status()
    stats  = dashboard_stats()
    return render_template(
        "index.html",
        habits=habits,
        stats=stats,
        today=str(datetime.now().date()),
        greeting=_greeting(),
        categories=CATEGORY_DEFAULTS,
    )


# ── Habit CRUD ─────────────────────────────────────────────────────────────────

@app.route("/habits/create", methods=["POST"])
def create_habit_route():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("dashboard"))
    add_habit(
        name=name,
        description=request.form.get("description", ""),
        category=request.form.get("category", "general"),
        frequency=request.form.get("frequency", "daily"),
        target_value=int(request.form.get("target_value", 1) or 1),
        unit=request.form.get("unit", "times"),
        color=request.form.get("color") or None,
        icon=request.form.get("icon", "").strip() or None,
        days_of_week=request.form.get("days_of_week", "0,1,2,3,4,5,6"),
    )
    return redirect(url_for("dashboard"))


@app.route("/habits/<int:habit_id>")
def habit_detail(habit_id):
    habit = get_habit(habit_id)
    if not habit:
        return redirect(url_for("dashboard"))
    stats    = get_habit_stats(habit_id)
    calendar = get_habit_calendar(habit_id, weeks=12)
    logs     = get_logs_for_habit(habit_id, limit=30)
    trend    = trend_data(habit_id, weeks=8)
    return render_template(
        "habit_detail.html",
        habit=habit,
        stats=stats,
        calendar=calendar,
        logs=logs,
        trend=json.dumps(trend),
        categories=CATEGORY_DEFAULTS,
    )


@app.route("/habits/<int:habit_id>/edit", methods=["POST"])
def edit_habit(habit_id):
    update_habit(
        habit_id,
        name=request.form.get("name", "").strip(),
        description=request.form.get("description", ""),
        category=request.form.get("category", "general"),
        frequency=request.form.get("frequency", "daily"),
        target_value=int(request.form.get("target_value", 1) or 1),
        unit=request.form.get("unit", "times"),
        color=request.form.get("color", "#64748b"),
        icon=request.form.get("icon", "✨").strip() or "✨",
    )
    return redirect(url_for("habit_detail", habit_id=habit_id))


@app.route("/habits/<int:habit_id>/delete", methods=["POST"])
def delete_habit_route(habit_id):
    delete_habit(habit_id)
    return redirect(url_for("dashboard"))


# ── One-tap logging (AJAX) ────────────────────────────────────────────────────

@app.route("/habits/<int:habit_id>/log", methods=["POST"])
def log_route(habit_id):
    logged, streak = toggle_log(habit_id)
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"logged": logged, "streak": streak})
    return redirect(url_for("dashboard"))


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.route("/analytics")
def analytics():
    stats    = dashboard_stats()
    heatmap  = completion_heatmap(weeks=52)
    cats     = category_breakdown()
    leaders  = top_habits()
    weekly   = weekly_activity()
    return render_template(
        "analytics.html",
        stats=stats,
        heatmap=json.dumps(heatmap),
        categories_data=json.dumps(cats),
        top_habits=leaders,
        weekly=json.dumps(weekly),
        categories=CATEGORY_DEFAULTS,
    )


# ── Export ────────────────────────────────────────────────────────────────────

@app.route("/export/csv")
def export_csv():
    habits    = get_all_habits(include_inactive=True)
    habit_map = {h["id"]: h["name"] for h in habits}
    logs      = get_all_logs()

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["Habit", "Category", "Date", "Value", "Completed", "Notes", "Logged At"])
    for l in logs:
        h_name = habit_map.get(l["habit_id"], "Unknown")
        h_cat  = next((h["category"] for h in habits if h["id"] == l["habit_id"]), "")
        w.writerow([h_name, h_cat, l["date"], l["value"],
                    "Yes" if l["completed"] else "No",
                    l.get("notes", ""), l.get("logged_at", "")])

    buf.seek(0)
    fname = f"habitflow_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(
        io.BytesIO(buf.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=fname,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
