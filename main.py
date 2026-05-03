from tracker.logic import add_entry
from tracker.analytics import weekly_summary, show_graph
from tracker.utils import get_int_input

def menu():
    while True:
        print("\n=== Habit Tracker ===")
        print("1. Add Entry")
        print("2. Weekly Summary")
        print("3. Show Graph")
        print("4. Exit")

        choice = input("Choose: ")

        if choice == "1":
            value = get_int_input("Enter value (minutes/water): ")
            if value:
                add_entry(value)
                print("Saved!")

        elif choice == "2":
            total = weekly_summary()
            print(f"Last 7 days total: {total}")

        elif choice == "3":
            show_graph()

        elif choice == "4":
            break

        else:
            print("Invalid choice")

if __name__ == "__main__":
    menu()