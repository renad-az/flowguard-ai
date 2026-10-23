import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from read_refresh_time import read_refresh_time


def parse_timestamp(value):
    formats = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )

    for date_format in formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue

    raise ValueError(
        f"Unsupported timestamp format: {value}"
    )


def main():
    try:
        before_text = read_refresh_time()
        before = parse_timestamp(before_text)

        print("BEFORE:", before_text, flush=True)

        trigger_script = Path(__file__).resolve().with_name(
            "refresh_powerbi.py"
        )

        if not trigger_script.is_file():
            raise RuntimeError("Refresh script not found.")

        trigger = subprocess.Popen(
            [sys.executable, str(trigger_script)]
        )

        deadline = time.monotonic() + 45
        last_read_error = None

        while time.monotonic() < deadline:
            time.sleep(1)

            try:
                after_text = read_refresh_time()
                after = parse_timestamp(after_text)

            except Exception as error:
                last_read_error = type(error).__name__
                continue

            if after > before:
                print("AFTER:", after_text)
                print(
                    "CHECK UPDATED: RefreshCheck timestamp advanced."
                )
                print(
                    "This does not verify all report tables."
                )
                return 0

            if (
                trigger.poll() is not None
                and trigger.returncode != 0
            ):
                print("UNKNOWN: Refresh trigger script failed.")
                return 1

        print("UNKNOWN: No newer readable timestamp within 45 seconds.")

        if last_read_error:
            print("Last card-reading error:", last_read_error)

        print("Check Power BI. No automatic retry.")
        return 1

    except Exception as error:
        print("CHECK FAILED:", type(error).__name__, str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())