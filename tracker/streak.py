from datetime import datetime, timedelta


def calculate_streak(logs, reference_date=None):
    """
    Count consecutive completed days ending on or just before reference_date.
    logs: list of dicts with a 'date' key (YYYY-MM-DD).
    """
    if not logs:
        return 0

    if reference_date is None:
        reference_date = datetime.now().date()
    elif isinstance(reference_date, str):
        reference_date = datetime.strptime(reference_date, "%Y-%m-%d").date()

    dates = set()
    for log in logs:
        raw = log["date"] if isinstance(log, dict) else str(log)
        try:
            dates.add(datetime.strptime(raw, "%Y-%m-%d").date())
        except ValueError:
            pass

    if not dates:
        return 0

    # Streak can start from today or yesterday (grace for not yet logged today)
    if reference_date in dates:
        current = reference_date
    elif (reference_date - timedelta(days=1)) in dates:
        current = reference_date - timedelta(days=1)
    else:
        return 0

    streak = 0
    while current in dates:
        streak += 1
        current -= timedelta(days=1)

    return streak


def calculate_best_streak(logs):
    """Return the longest consecutive-day streak in the full log history."""
    if not logs:
        return 0

    dates = sorted({
        datetime.strptime(l["date"], "%Y-%m-%d").date()
        for l in logs
    })

    if not dates:
        return 0

    best = current = 1
    for i in range(1, len(dates)):
        if (dates[i] - dates[i - 1]).days == 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best
