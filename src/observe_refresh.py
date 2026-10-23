import subprocess
import sys
import time
import traceback
from pathlib import Path

from pywinauto import Desktop


def refresh_dialogs(desktop, report):
    candidates = report.descendants(control_type="Window")

    candidates.extend(
        window
        for window in desktop.windows()
        if window.process_id() == report.process_id()
        and window.handle != report.handle
    )

    dialogs = []

    for window in candidates:
        title = window.window_text().strip()

        if (
            title.lower() == "refresh"
            or title == "تحديث"
        ) and window.is_visible():
            dialogs.append(window)

    return dialogs


def read_messages(dialogs):
    messages = []

    for dialog in dialogs:
        for control in dialog.descendants(control_type="Text"):
            message = control.window_text().strip()

            if message:
                messages.append(message)

    return messages


def main():
    trigger = None

    try:
        desktop = Desktop(backend="uia")

        reports = [
            window
            for window in desktop.windows()
            if window.window_text() == "FlowBI - Power BI Desktop"
        ]

        if len(reports) != 1:
            print("STOP: Expected exactly one FlowBI report.")
            return

        report = reports[0]

        trigger_script = Path(__file__).resolve().with_name(
            "refresh_powerbi.py"
        )

        if not trigger_script.is_file():
            print("STOP: Refresh script not found.")
            return

        if refresh_dialogs(desktop, report):
            print("STOP: A refresh dialog is already open.")
            print("No new refresh command sent.")
            return

        trigger = subprocess.Popen(
            [sys.executable, str(trigger_script)]
        )

        deadline = time.monotonic() + 40
        started = False
        absent_checks = 0
        consecutive_errors = 0
        printed_messages = set()

        while time.monotonic() < deadline:
            try:
                dialogs = refresh_dialogs(desktop, report)
                messages = read_messages(dialogs)

            except Exception as error:
                consecutive_errors += 1

                # فشل الرصد ليس دليلًا على اختفاء النافذة
                absent_checks = 0

                print(
                    "OBSERVATION RETRY:",
                    consecutive_errors,
                    "|",
                    type(error).__name__,
                    flush=True,
                )

                if consecutive_errors >= 3:
                    traceback.print_exc()
                    print(
                        "UNKNOWN: Repeated observation failures."
                    )
                    print("Check Power BI. No automatic retry.")
                    return

                time.sleep(1)
                continue

            consecutive_errors = 0

            if dialogs:
                absent_checks = 0

                if not started:
                    started = True
                    print(
                        "REFRESH STARTED: Dialog detected.",
                        flush=True,
                    )

                for message in messages:
                    if message not in printed_messages:
                        printed_messages.add(message)
                        print("STATUS:", message, flush=True)

            elif started:
                absent_checks += 1

                if absent_checks >= 3:
                    print("DIALOG CLOSED: No longer visible.")
                    print(
                        "OUTCOME: Unverified. "
                        "Dialog closure alone does not prove success."
                    )
                    return

            time.sleep(0.5)

        if started:
            print("TIMEOUT: Refresh dialog did not finish in time.")
        else:
            print("UNKNOWN: No refresh dialog was captured.")

        print("Check Power BI. No automatic retry.")

    except Exception:
        traceback.print_exc()
        print("Refresh outcome is unknown. Check Power BI.")

    finally:
        if trigger is not None:
            print("Trigger script exit code:", trigger.poll())


if __name__ == "__main__":
    main()