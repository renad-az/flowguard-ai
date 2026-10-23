import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Desktop

from observe_refresh import refresh_dialogs, read_messages
from read_refresh_time import read_refresh_time
from verify_refresh_time import parse_timestamp


def read_time_with_retry(timeout=8):
    deadline = time.monotonic() + timeout
    last_error = None

    while time.monotonic() < deadline:
        try:
            text = read_refresh_time()
            return text, parse_timestamp(text)

        except Exception as error:
            last_error = error
            time.sleep(0.5)

    raise RuntimeError(
        f"Timestamp remained unreadable: {last_error}"
    )


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

        # إظهار التقرير قبل محاولة قراءة البطاقة
        report.set_focus()
        time.sleep(1)

        if refresh_dialogs(desktop, report):
            print("STOP: A refresh dialog is already open.")
            return 1

        before_text, before = read_time_with_retry()
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
                            "REVIEW: Possible failure message captured."
                        )
                        return 1

                    if trigger.poll() != 0:
                        print(
                            "UNKNOWN: Trigger did not finish "
                            "successfully."
                        )
                        return 1

                    report.set_focus()

                    # ننتظر إتاحة البطاقة بعد إغلاق نافذة التحديث
                    after_text, after = read_time_with_retry()

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
                        "UNKNOWN: Timestamp did not advance."
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