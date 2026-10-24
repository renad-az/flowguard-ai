import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

from monitor_lock import (
    MonitorAlreadyRunningError,
    monitor_lock,
)


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def watch(source, baseline, approved, enable_refresh):
    script_folder = Path(__file__).resolve().parent
    approval_script = script_folder / "approve_workbook.py"
    refresh_script = script_folder / "run_refresh_cycle.py"

    last_processed = file_hash(source)
    candidate = None
    stable_checks = 0
    waiting_message_shown = False

    print("MONITORING:", source.name, flush=True)
    print("Single-instance lock acquired.", flush=True)
    print("Refresh cycle enabled:", enable_refresh, flush=True)
    print("Unknown refresh outcome stops monitoring.", flush=True)
    print("Press Ctrl+C to stop.", flush=True)

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

            print(
                "CHANGE DETECTED: Waiting for stability.",
                flush=True,
            )
            continue

        stable_checks += 1

        if stable_checks < 3:
            continue

        print("CHECKING: Running validation.", flush=True)

        approval = subprocess.run(
            [
                sys.executable,
                str(approval_script),
                str(source),
                str(baseline),
                str(approved),
            ],
            check=False,
            timeout=120,
        )

        if approval.returncode != 0:
            print(
                "MONITOR: Not approved. Refresh skipped.",
                flush=True,
            )

        else:
            print("MONITOR: Approval succeeded.", flush=True)

            if enable_refresh:
                print(
                    "MONITOR: Starting observed refresh cycle.",
                    flush=True,
                )

                refresh = subprocess.run(
                    [
                        sys.executable,
                        str(refresh_script),
                    ],
                    check=False,
                    timeout=120,
                )

                if refresh.returncode != 0:
                    print(
                        "MONITOR STOPPED: Refresh outcome "
                        "needs review. No automatic retry.",
                        flush=True,
                    )
                    print(
                        "Check Power BI before restarting. "
                        "The approved file remains published.",
                        flush=True,
                    )
                    return 1

                print(
                    "MONITOR: Dialog closure and newer "
                    "check timestamp observed.",
                    flush=True,
                )
                print(
                    "All-table success is not verified.",
                    flush=True,
                )

        last_processed = candidate
        candidate = None
        stable_checks = 0


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Excel with guarded Power BI refresh."
    )

    parser.add_argument("source", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("approved", type=Path)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    source = args.source.resolve()
    baseline = args.baseline.resolve()
    approved = args.approved.resolve()

    script_folder = Path(__file__).resolve().parent

    if not source.is_file():
        parser.error(f"Source not found: {source}")

    if not baseline.is_file():
        parser.error(f"Baseline not found: {baseline}")

    if source == approved:
        parser.error("Source and approved must be separate files.")

    if not (script_folder / "approve_workbook.py").is_file():
        parser.error("Approval script not found.")

    if (
        args.refresh
        and not (script_folder / "run_refresh_cycle.py").is_file()
    ):
        parser.error("Refresh cycle script not found.")

    try:
        with monitor_lock():
            return watch(
                source,
                baseline,
                approved,
                args.refresh,
            )

    except MonitorAlreadyRunningError:
        print("STOP: Another monitor is already running.")
        return 1

    except subprocess.TimeoutExpired:
        print(
            "MONITOR STOPPED: Subprocess timed out. "
            "Outcome unknown; check Power BI and files."
        )
        return 1

    except KeyboardInterrupt:
        print(
            "\nMonitoring stopped. If refresh was running, "
            "check Power BI before restarting."
        )
        return 0

    except OSError as error:
        print("MONITOR STOPPED:", error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())