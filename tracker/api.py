"""REST API for the mobile app. JWT-authenticated. Prefix: /api"""
from functools import wraps
from flask import Blueprint, request, jsonify
from tracker.auth import (
    decode_jwt, make_jwt, get_user_by_email, verify_password, create_user,
    get_user_by_id, verify_google_token, login_or_create_google_user,
)
from tracker.logic import (
    add_habit, get_habits_with_status, toggle_log,
    get_habit_stats, get_habit_calendar,
)
from tracker.storage import (
    get_habit, update_habit, delete_habit, get_logs_for_habit,
)
from tracker.analytics import (
    dashboard_stats, weekly_activity, category_breakdown,
    completion_heatmap, top_habits, trend_data,
)
from tracker.database import CATEGORY_DEFAULTS

api = Blueprint("api", __name__, url_prefix="/api")


def jwt_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "missing token"}), 401
        token = auth[7:]
        user_id = decode_jwt(token)
        if not user_id:
            return jsonify({"error": "invalid token"}), 401
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "user not found"}), 401
        request.user = user
        return fn(*args, **kwargs)
    return wrapper


# ── Auth ──────────────────────────────────────────────────────────────────────

@api.post("/auth/signup")
def signup():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or None
    if not email or not password or len(password) < 6:
        return jsonify({"error": "email and password (≥6 chars) required"}), 400
    if get_user_by_email(email):
        return jsonify({"error": "email already registered"}), 409
    user_id = create_user(email, password, name)
    user = get_user_by_id(user_id)
    return jsonify({"token": make_jwt(user_id), "user": user.to_dict()}), 201


@api.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    user = verify_password(email, password)
    if not user:
        return jsonify({"error": "invalid credentials"}), 401
    return jsonify({"token": make_jwt(user.id), "user": user.to_dict()})


@api.post("/auth/google")
def google_signin():
    data = request.get_json(silent=True) or {}
    id_token = data.get("id_token")
    if not id_token:
        return jsonify({"error": "id_token required"}), 400
    info = verify_google_token(id_token)
    if not info:
        return jsonify({"error": "invalid Google token"}), 401
    user = login_or_create_google_user(info)
    return jsonify({"token": make_jwt(user.id), "user": user.to_dict()})


@api.get("/auth/me")
@jwt_required
def me():
    return jsonify({"user": request.user.to_dict()})


# ── Habits ────────────────────────────────────────────────────────────────────

@api.get("/habits")
@jwt_required
def list_habits():
    return jsonify({"habits": get_habits_with_status(request.user.id)})


@api.post("/habits")
@jwt_required
def create_habit_route():
    d = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name required"}), 400
    habit_id = add_habit(
        user_id=request.user.id,
        name=name,
        description=d.get("description", ""),
        category=d.get("category", "general"),
        frequency=d.get("frequency", "daily"),
        target_value=int(d.get("target_value", 1) or 1),
        unit=d.get("unit", "times"),
        color=d.get("color"),
        icon=d.get("icon"),
        days_of_week=d.get("days_of_week", "0,1,2,3,4,5,6"),
    )
    return jsonify({"habit": get_habit(request.user.id, habit_id)}), 201


@api.get("/habits/<int:habit_id>")
@jwt_required
def habit_detail(habit_id):
    h = get_habit(request.user.id, habit_id)
    if not h:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "habit": h,
        "stats": get_habit_stats(request.user.id, habit_id),
        "calendar": get_habit_calendar(request.user.id, habit_id, weeks=12),
        "trend": trend_data(request.user.id, habit_id, weeks=8),
        "logs": get_logs_for_habit(request.user.id, habit_id, limit=30),
    })


@api.put("/habits/<int:habit_id>")
@jwt_required
def update_habit_route(habit_id):
    d = request.get_json(silent=True) or {}
    update_habit(request.user.id, habit_id, **d)
    return jsonify({"habit": get_habit(request.user.id, habit_id)})


@api.delete("/habits/<int:habit_id>")
@jwt_required
def delete_habit_route(habit_id):
    delete_habit(request.user.id, habit_id)
    return jsonify({"ok": True})


@api.post("/habits/<int:habit_id>/log")
@jwt_required
def log_route(habit_id):
    logged, streak = toggle_log(request.user.id, habit_id)
    return jsonify({"logged": logged, "streak": streak})


# ── Analytics ─────────────────────────────────────────────────────────────────

@api.get("/analytics")
@jwt_required
def analytics():
    return jsonify({
        "stats": dashboard_stats(request.user.id),
        "weekly": weekly_activity(request.user.id),
        "categories": category_breakdown(request.user.id),
        "heatmap": completion_heatmap(request.user.id, weeks=52),
        "leaders": top_habits(request.user.id),
    })


# ── Meta ──────────────────────────────────────────────────────────────────────

@api.get("/meta/categories")
def meta_categories():
    return jsonify({"categories": CATEGORY_DEFAULTS})
