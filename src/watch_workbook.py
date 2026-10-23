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
        description="Monitor Excel and optionally trigger Power BI refresh."
    )

    parser.add_argument("source", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("approved", type=Path)

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Trigger the experimental Power BI refresh script.",
    )

    args = parser.parse_args()

    source = args.source.resolve()
    baseline = args.baseline.resolve()
    approved = args.approved.resolve()

    script_folder = Path(__file__).resolve().parent
    approval_script = script_folder / "approve_workbook.py"
    refresh_script = script_folder / "refresh_powerbi.py"

    if not source.is_file():
        parser.error(f"Source not found: {source}")

    if not baseline.is_file():
        parser.error(f"Baseline not found: {baseline}")

    if source == approved:
        parser.error("Source and approved must be separate files.")

    if args.refresh and not refresh_script.is_file():
        parser.error(f"Refresh script not found: {refresh_script}")

    try:
        last_processed = file_hash(source)
    except OSError as error:
        parser.error(f"Could not read source: {error}")

    candidate = None
    stable_checks = 0
    waiting_message_shown = False

    print("MONITORING:", source.name, flush=True)
    print("Refresh trigger enabled:", args.refresh, flush=True)
    print("Refresh completion is not verified automatically.", flush=True)
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
            )

            if approval.returncode != 0:
                print(
                    "MONITOR: Not approved. Refresh skipped.",
                    flush=True,
                )

            else:
                print("MONITOR: Approval succeeded.", flush=True)

                if args.refresh:
                    print(
                        "MONITOR: Starting refresh trigger.",
                        flush=True,
                    )

                    try:
                        refresh = subprocess.run(
                            [
                                sys.executable,
                                str(refresh_script),
                            ],
                            check=False,
                            timeout=60,
                        )

                        if refresh.returncode != 0:
                            print(
                                "MONITOR: Refresh script failed.",
                                flush=True,
                            )
                        else:
                            print(
                                "MONITOR: Refresh script finished. "
                                "Check its messages and Power BI; "
                                "completion is not verified.",
                                flush=True,
                            )

                    except subprocess.TimeoutExpired:
                        print(
                            "MONITOR: Refresh trigger timed out. "
                            "Its outcome is unknown; check Power BI.",
                            flush=True,
                        )

            last_processed = candidate
            candidate = None
            stable_checks = 0

    except KeyboardInterrupt:
        print("\nMonitoring stopped.", flush=True)


if __name__ == "__main__":
    main()