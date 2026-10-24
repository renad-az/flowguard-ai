import json
import time
import ctypes
from pathlib import Path

from pywinauto import mouse

from powerbi_target import get_report_window
from workspace_store import get_active_workspace


def main():
    workspace = get_active_workspace()

    if not workspace:
        raise RuntimeError("No active workspace.")

    project = Path(__file__).resolve().parents[1]
    calibration_file = (
        project
        / "reports"
        / "refresh_targets"
        / f"{workspace['id']}.json"
    )

    if not calibration_file.is_file():
        raise RuntimeError(
            "No refresh position saved for this workspace."
        )

    configuration = json.loads(
        calibration_file.read_text(encoding="utf-8")
    )

    if configuration.get("version") != 1:
        raise RuntimeError("Unsupported calibration version.")

    if configuration.get("workspace_id") != workspace["id"]:
        raise RuntimeError("Calibration workspace does not match.")

    report = get_report_window()
    report.set_focus()
    time.sleep(1)

    title = report.window_text()

    if title != configuration["report_title"]:
        raise RuntimeError("Report title does not match calibration.")

    rect = report.rectangle()

    expected_size = (
        configuration["window_width"],
        configuration["window_height"],
    )

    if (rect.width(), rect.height()) != expected_size:
        raise RuntimeError(
            "Window size changed. Recalibrate before refreshing."
        )

    x = configuration["relative_x"]
    y = configuration["relative_y"]

    if type(x) is not int or type(y) is not int:
        raise RuntimeError("Invalid saved coordinates.")

    if not (0 <= x < rect.width() and 0 <= y < rect.height()):
        raise RuntimeError("Saved position is outside the window.")

    current_workspace = get_active_workspace()

    if (
        not current_workspace
        or current_workspace["id"] != workspace["id"]
    ):
        raise RuntimeError("Active workspace changed.")

    foreground = ctypes.windll.user32.GetForegroundWindow()

    if foreground != report.handle:
        raise RuntimeError("Report is not the foreground window.")

    print("WORKSPACE:", workspace["name"])
    print("REPORT:", title)

    mouse.click(
        button="left",
        coords=(rect.left + x, rect.top + y),
    )

    print("Refresh click sent using saved calibration.")
    print("Completion is NOT verified. Check Power BI.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print("REFRESH FAILED:", type(error).__name__, str(error))
        raise SystemExit(1)