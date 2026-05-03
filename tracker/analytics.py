from tracker.logic import get_all_entries
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def weekly_summary():
    data = get_all_entries()
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    total = 0

    for entry in data:
        d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        if d >= week_ago:
            total += entry["value"]

    return total

def show_graph():
    data = get_all_entries()

    if not data:
        print("No data available")
        return

    dates = [entry["date"] for entry in data]
    values = [entry["value"] for entry in data]

    plt.plot(dates, values)
    plt.xticks(rotation=45)
    plt.title("Habit Progress")
    plt.tight_layout()
    plt.show()