import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Desktop

from observe_refresh import refresh_dialogs, read_messages
from read_refresh_time import read_refresh_time
from verify_refresh_time import parse_timestamp


def main():
    try:
        desktop = Desktop(backend="uia")

        reports = [
            window
            for window in desktop.windows()
            if window.window_text() == "FlowBI - Power BI Desktop"
        ]

        if len(reports) != 1:
            raise RuntimeError(
                "Expected exactly one FlowBI report."
            )

        report = reports[0]

        if refresh_dialogs(desktop, report):
            print("STOP: A refresh dialog is already open.")
            return 1

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

        started = False
        absent_checks = 0
        read_failures = 0
        possible_failure = False
        printed_messages = set()

        failure_terms = (
            "error",
            "failed",
            "cancelled",
            "canceled",
            "خطأ",
            "فشل",
            "إلغاء",
        )

        while time.monotonic() < deadline:
            try:
                dialogs = refresh_dialogs(desktop, report)
                messages = read_messages(dialogs)

            except Exception as error:
                absent_checks = 0
                read_failures += 1

                print(
                    "OBSERVATION RETRY:",
                    type(error).__name__,
                    flush=True,
                )

                if read_failures >= 3:
                    print("UNKNOWN: Repeated observation failures.")
                    return 1

                time.sleep(1)
                continue

            read_failures = 0

            if dialogs:
                absent_checks = 0

                if not started:
                    started = True
                    print("REFRESH STARTED.", flush=True)

                for message in messages:
                    if message not in printed_messages:
                        printed_messages.add(message)
                        print("STATUS:", message, flush=True)

                    if any(
                        term in message.lower()
                        for term in failure_terms
                    ):
                        possible_failure = True

            elif started:
                absent_checks += 1

                if absent_checks >= 3:
                    if possible_failure:
                        print(
                            "REVIEW: A possible failure message "
                            "was captured. Check Power BI."
                        )
                        return 1

                    if trigger.poll() != 0:
                        print(
                            "UNKNOWN: Trigger script did not "
                            "finish successfully."
                        )
                        return 1

                    after_text = read_refresh_time()
                    after = parse_timestamp(after_text)

                    print("AFTER:", after_text)

                    if after > before:
                        print(
                            "CYCLE OBSERVED: Dialog closed and "
                            "RefreshCheck timestamp advanced."
                        )
                        print(
                            "All-table success is not verified."
                        )
                        return 0

                    print(
                        "UNKNOWN: Dialog closed, but "
                        "timestamp did not advance."
                    )
                    return 1

            time.sleep(0.5)

        print("UNKNOWN: Observation timed out.")
        print("Check Power BI. No automatic retry.")
        return 1

    except Exception as error:
        print(
            "UNKNOWN:",
            type(error).__name__,
            str(error),
        )
        print("Check Power BI. No automatic retry.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())