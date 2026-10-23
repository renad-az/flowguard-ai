import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Excel changes and run validation."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("approved", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    baseline = args.baseline.resolve()
    approved = args.approved.resolve()

    approval_script = Path(__file__).resolve().with_name(
        "approve_workbook.py"
    )

    if not source.is_file():
        parser.error(f"Source file not found: {source}")

    if not baseline.is_file():
        parser.error(f"Baseline not found: {baseline}")

    if source == approved:
        parser.error("Source and approved must be separate files.")

    try:
        last_processed = file_hash(source)
    except OSError as error:
        parser.error(f"Could not read source: {error}")

    candidate = None
    stable_checks = 0
    waiting_message_shown = False

    print("MONITORING:", source.name, flush=True)
    print("Save a change in Excel to trigger validation.", flush=True)
    print("Power BI refresh is not connected yet.", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

    try:
        while True:
            time.sleep(2)

            try:
                current_hash = file_hash(source)
            except OSError:
                candidate = None
                stable_checks = 0

                if not waiting_message_shown:
                    print(
                        "WAITING: Source unavailable; retrying.",
                        flush=True,
                    )
                    waiting_message_shown = True

                continue

            waiting_message_shown = False

            if current_hash == last_processed:
                candidate = None
                stable_checks = 0
                continue

            if current_hash != candidate:
                candidate = current_hash
                stable_checks = 1
                print("CHANGE DETECTED: Waiting for stability.", flush=True)
                continue

            stable_checks += 1

            if stable_checks < 3:
                continue

            print("CHECKING: Running validation and approval.", flush=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(approval_script),
                    str(source),
                    str(baseline),
                    str(approved),
                ],
                check=False,
            )

            if result.returncode == 0:
                print("MONITOR: Approval succeeded.", flush=True)
            else:
                print(
                    "MONITOR: Approval failed or was blocked. "
                    "Review the message, correct the issue, and save again.",
                    flush=True,
                )

            # لا نكرر المحاولة لنفس المحتوى بلا نهاية
            last_processed = candidate
            candidate = None
            stable_checks = 0

    except KeyboardInterrupt:
        print("\nMonitoring stopped.", flush=True)


if __name__ == "__main__":
    main()