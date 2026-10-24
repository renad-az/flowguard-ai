import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Desktop

from observe_refresh import refresh_dialogs, read_messages
from powerbi_target import get_report_window
from read_refresh_time import read_refresh_time
from verify_refresh_time import parse_timestamp
from workspace_store import get_active_workspace


def ensure_same_workspace(expected):
    current = get_active_workspace()

    if current != expected:
        raise RuntimeError(
            "Active workspace or its settings changed during the cycle."
        )


def read_time_with_retry(workspace, timeout=8):
    deadline = time.monotonic() + timeout
    last_error = None

    while time.monotonic() < deadline:
        ensure_same_workspace(workspace)

        try:
            text = read_refresh_time()
            parsed = parse_timestamp(text)

            ensure_same_workspace(workspace)
            return text, parsed

        except Exception as error:
            last_error = error
            time.sleep(0.5)

    raise RuntimeError(
        f"Timestamp remained unreadable: {last_error}"
    )


def main():
    try:
        workspace = get_active_workspace()

        if not workspace:
            raise RuntimeError("No active workspace.")

        desktop = Desktop(backend="uia")
        report = get_report_window()
        report_handle = report.handle

        print("WORKSPACE:", workspace["name"], flush=True)
        print("REPORT:", report.window_text(), flush=True)

        report.set_focus()
        time.sleep(1)

        if refresh_dialogs(desktop, report):
            print("STOP: A refresh dialog is already open.")
            return 1

        before_text, before = read_time_with_retry(workspace)
        print("BEFORE:", before_text, flush=True)

        trigger_script = Path(__file__).resolve().with_name(
            "refresh_powerbi.py"
        )

        if not trigger_script.is_file():
            raise RuntimeError("Refresh script not found.")

        ensure_same_workspace(workspace)

        if get_report_window().handle != report_handle:
            raise RuntimeError("The report window changed.")

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
            ensure_same_workspace(workspace)

            trigger_result = trigger.poll()

            if trigger_result is not None and trigger_result != 0:
                print("UNKNOWN: Refresh trigger failed.")
                print("Check Power BI. No automatic retry.")
                return 1

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
                    raise RuntimeError(
                        "Repeated observation failures."
                    )

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
                            "REVIEW: Possible failure message captured."
                        )
                        return 1

                    if trigger.poll() != 0:
                        print(
                            "UNKNOWN: Trigger completion was not confirmed."
                        )
                        return 1

                    ensure_same_workspace(workspace)

                    if get_report_window().handle != report_handle:
                        raise RuntimeError(
                            "The report window changed."
                        )

                    report.set_focus()

                    after_text, after = read_time_with_retry(
                        workspace
                    )

                    print("AFTER:", after_text, flush=True)

                    if after > before:
                        print(
                            "CYCLE OBSERVED: Dialog closed and "
                            "RefreshCheck timestamp advanced."
                        )
                        print("All-table success is not verified.")
                        return 0

                    print("UNKNOWN: Timestamp did not advance.")
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
            flush=True,
        )
        print("Check Power BI. No automatic retry.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())