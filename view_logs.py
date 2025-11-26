import os
import glob
from pathlib import Path

# Path to logs based on project structure
PROJECT_ROOT = Path(__file__).resolve().parent
LOGS_DIR = PROJECT_ROOT / "rpa_logs" / "execution_logs"


def view_latest_log():
    if not LOGS_DIR.exists():
        print(f"Log directory not found: {LOGS_DIR}")
        return

    # Find all .log files
    log_files = glob.glob(str(LOGS_DIR / "execution_*.log"))

    if not log_files:
        print("No log files found.")
        return

    # Sort by modification time (newest first)
    latest_log = max(log_files, key=os.path.getmtime)

    print(f"\n--- Reading Latest Log: {os.path.basename(latest_log)} ---\n")

    try:
        with open(latest_log, "r", encoding="utf-8") as f:
            content = f.read()
            if content:
                print(content)
            else:
                print("[File is empty]")
    except Exception as e:
        print(f"Error reading log file: {e}")


if __name__ == "__main__":
    view_latest_log()
