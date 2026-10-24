import ctypes
import json
import time
from pathlib import Path

from pywinauto import mouse

from powerbi_target import get_report_window
from workspace_store import get_active_workspace


def main():
    workspace = get_active_workspace()

    if not workspace:
        raise RuntimeError("No active workspace.")

    project = Path(__file__).resolve().parents[1]
    configuration_file = (
        project
        / "reports"
        / "refresh_targets"
        / f"{workspace['id']}.json"
    )

    if not configuration_file.is_file():
        raise RuntimeError("No refresh calibration for this workspace.")

    configuration = json.loads(
        configuration_file.read_text(encoding="utf-8")
    )

    if configuration.get("version") != 1:
        raise RuntimeError("Unsupported calibration version.")

    if configuration.get("workspace_id") != workspace["id"]:
        raise RuntimeError("Calibration belongs to another workspace.")

    report = get_report_window()
    report_title = report.window_text()

    if report_title != configuration["report_title"]:
        raise RuntimeError("Report title does not match the calibration.")

    report.set_focus()
    time.sleep(1)

    rect = report.rectangle()

    if (rect.width(), rect.height()) != (
        configuration["window_width"],
        configuration["window_height"],
    ):
        raise RuntimeError(
            "Window size changed. Capture the refresh position again."
        )

    x = configuration["relative_x"]
    y = configuration["relative_y"]

    if not (0 <= x < rect.width() and 0 <= y < rect.height()):
        raise RuntimeError("Saved position is outside the report.")

    for dialog in report.descendants(control_type="Window"):
        if dialog.is_visible():
            raise RuntimeError(
                "A report dialog is open. Close it before refreshing."
            )

    current_workspace = get_active_workspace()

    if not current_workspace or current_workspace["id"] != workspace["id"]:
        raise RuntimeError("Active workspace changed. Refresh cancelled.")

    if ctypes.windll.user32.GetForegroundWindow() != report.handle:
        raise RuntimeError("The report is not the foreground window.")

    mouse.click(
        button="left",
        coords=(rect.left + x, rect.top + y),
    )

    print("WORKSPACE:", workspace["name"])
    print("REPORT:", report_title)
    print("Refresh click sent using saved calibration.")
    print("Completion is NOT verified. Check Power BI.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("REFRESH NOT SENT:", type(error).__name__, str(error))
        raise SystemExit(1)