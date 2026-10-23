import subprocess
import sys
import time
from pathlib import Path

from pywinauto import Desktop


def main():
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
    process_id = report.process_id()

    trigger_script = Path(__file__).resolve().with_name(
        "refresh_powerbi.py"
    )

    if not trigger_script.is_file():
        print("STOP: Refresh script not found.")
        return

    seen_messages = set()

    print("Observing refresh dialogs for 30 seconds.", flush=True)

    trigger = subprocess.Popen(
        [sys.executable, str(trigger_script)]
    )

    deadline = time.monotonic() + 30

    try:
        while time.monotonic() < deadline:
            candidates = report.descendants(
                control_type="Window"
            )

            candidates.extend(
                window
                for window in desktop.windows()
                if window.process_id() == process_id
                and window.handle != report.handle
            )

            for dialog in candidates:
                try:
                    title = dialog.window_text() or ""

                    if not (
                        "refresh" in title.lower()
                        or "تحديث" in title
                    ):
                        continue

                    if not dialog.is_visible():
                        continue

                    messages = [
                        item.window_text()
                        for item in dialog.descendants(
                            control_type="Text"
                        )
                        if item.window_text().strip()
                    ]

                    signature = (title, tuple(messages))

                    if signature in seen_messages:
                        continue

                    seen_messages.add(signature)

                    print("\nDIALOG:", title, flush=True)

                    for message in messages[:30]:
                        print("TEXT:", message, flush=True)

                except Exception as error:
                    print(
                        "Dialog changed while reading:",
                        type(error).__name__,
                        flush=True,
                    )

            time.sleep(0.5)

    finally:
        print("\nObservation finished.", flush=True)
        print("Trigger process exit code:", trigger.poll())

        if not seen_messages:
            print("No matching dialog captured.")
            print("This does NOT prove success or failure.")

        print("Refresh completion is not verified yet.")


if __name__ == "__main__":
    main()