def create_entry(habit, value, date):
    """Legacy helper kept for backward compatibility."""
    return {"habit": habit, "value": value, "date": date}


def habit_row_to_dict(row):
    """Convert a sqlite3.Row habit to a plain dict."""
    return dict(row) if row else None


def log_row_to_dict(row):
    """Convert a sqlite3.Row log to a plain dict."""
    return dict(row) if row else None
