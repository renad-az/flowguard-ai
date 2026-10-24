import ctypes
import json
import time
from pathlib import Path

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
        raise RuntimeError("No saved refresh position for this workspace.")

    configuration = json.loads(
        configuration_file.read_text(encoding="utf-8")
    )

    if configuration.get("version") != 1:
        raise RuntimeError("Unsupported calibration version.")

    if configuration.get("workspace_id") != workspace["id"]:
        raise RuntimeError("Workspace does not match the calibration.")

    report = get_report_window()

    if report.window_text() != configuration["report_title"]:
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
        raise RuntimeError("Saved position is outside the report window.")

    if ctypes.windll.user32.GetForegroundWindow() != report.handle:
        raise RuntimeError("The report is not the foreground window.")

    if not ctypes.windll.user32.SetCursorPos(
        rect.left + x,
        rect.top + y,
    ):
        raise RuntimeError("Could not move the mouse.")

    print("WORKSPACE:", workspace["name"])
    print("POINTER MOVED: Check that it is over the Refresh icon.")
    print("No click or refresh triggered.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("TEST FAILED:", str(error))
        raise SystemExit(1)