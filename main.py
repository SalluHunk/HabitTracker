import io
import os
import csv
import json
from datetime import datetime

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_file, flash,
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user,
)

from tracker.database import init_db, CATEGORY_DEFAULTS
from tracker.auth import (
    get_user_by_id, get_user_by_email, create_user, verify_password,
    verify_google_token, login_or_create_google_user, GOOGLE_CLIENT_ID,
    create_password_reset, verify_reset_code, update_password,
)
from tracker.email_util import send_email
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
from tracker.api import api

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")
init_db()

# ── Login manager ─────────────────────────────────────────────────────────────

login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to continue."


@login_manager.user_loader
def load_user(user_id):
    return get_user_by_id(int(user_id))


# Register API blueprint
app.register_blueprint(api)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _greeting():
    h = datetime.now().hour
    if h < 12:
        return "Good morning"
    if h < 17:
        return "Good afternoon"
    return "Good evening"


# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = verify_password(email, password)
        if user:
            login_user(user, remember=True)
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()
        if not email or not password or len(password) < 6:
            flash("Email and password (at least 6 characters) required.", "error")
        elif get_user_by_email(email):
            flash("An account with that email already exists.", "error")
        else:
            user_id = create_user(email, password, name or None)
            login_user(get_user_by_id(user_id), remember=True)
            return redirect(url_for("dashboard"))
    return render_template("signup.html", google_client_id=GOOGLE_CLIENT_ID)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = get_user_by_email(email)
        if user and user.get("password_hash"):
            code = create_password_reset(user["id"])
            send_email(
                email,
                "HabitFlow password reset code",
                f"Your HabitFlow password reset code is:\n\n{code}\n\n"
                f"This code expires in 15 minutes. If you didn't request this, ignore this email.",
            )
        flash("If that email exists, we've sent a reset code. Check your inbox.", "success")
        return redirect(url_for("reset_password_route", email=email))
    return render_template("forgot_password.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password_route():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    email = request.values.get("email", "")
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        code = request.form.get("code", "").strip()
        new_pw = request.form.get("new_password", "")
        if len(new_pw) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("reset_password.html", email=email)
        user_id = verify_reset_code(email, code)
        if not user_id:
            flash("Invalid or expired code.", "error")
            return render_template("reset_password.html", email=email)
        update_password(user_id, new_pw)
        flash("Password updated. Please sign in.", "success")
        return redirect(url_for("login"))
    return render_template("reset_password.html", email=email)


@app.route("/auth/google", methods=["POST"])
def google_login():
    """Receives the ID token from Google Sign-In button (web)."""
    id_token = request.form.get("credential") or request.json.get("credential")
    info = verify_google_token(id_token)
    if not info:
        flash("Google sign-in failed.", "error")
        return redirect(url_for("login"))
    user = login_or_create_google_user(info)
    login_user(user, remember=True)
    return redirect(url_for("dashboard"))


@app.route("/profile")
@login_required
def profile():
    stats = dashboard_stats(current_user.id)
    return render_template("profile.html", stats=stats, user=current_user)


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
@login_required
def dashboard():
    habits = get_habits_with_status(current_user.id)
    stats  = dashboard_stats(current_user.id)
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
@login_required
def create_habit_route():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("dashboard"))
    add_habit(
        user_id=current_user.id,
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
@login_required
def habit_detail(habit_id):
    habit = get_habit(current_user.id, habit_id)
    if not habit:
        return redirect(url_for("dashboard"))
    stats    = get_habit_stats(current_user.id, habit_id)
    calendar = get_habit_calendar(current_user.id, habit_id, weeks=12)
    logs     = get_logs_for_habit(current_user.id, habit_id, limit=30)
    trend    = trend_data(current_user.id, habit_id, weeks=8)
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
@login_required
def edit_habit(habit_id):
    update_habit(
        current_user.id, habit_id,
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
@login_required
def delete_habit_route(habit_id):
    delete_habit(current_user.id, habit_id)
    return redirect(url_for("dashboard"))


# ── One-tap logging (AJAX) ────────────────────────────────────────────────────

@app.route("/habits/<int:habit_id>/log", methods=["POST"])
@login_required
def log_route(habit_id):
    logged, streak = toggle_log(current_user.id, habit_id)
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"logged": logged, "streak": streak})
    return redirect(url_for("dashboard"))


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.route("/analytics")
@login_required
def analytics():
    stats    = dashboard_stats(current_user.id)
    heatmap  = completion_heatmap(current_user.id, weeks=52)
    cats     = category_breakdown(current_user.id)
    leaders  = top_habits(current_user.id)
    weekly   = weekly_activity(current_user.id)
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
@login_required
def export_csv():
    habits    = get_all_habits(current_user.id, include_inactive=True)
    habit_map = {h["id"]: h["name"] for h in habits}
    logs      = get_all_logs(current_user.id)

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
