import json
import os
import tempfile
from pathlib import Path

from powerbi_target import get_report_window
from workspace_store import get_active_workspace


def main():
    workspace = get_active_workspace()

    if not workspace:
        raise RuntimeError("No active workspace.")

    report = get_report_window()
    rect = report.rectangle()

    expected_width = 1942
    expected_height = 1030
    x = 931
    y = 148

    if (rect.width(), rect.height()) != (
        expected_width,
        expected_height,
    ):
        raise RuntimeError(
            "Window size changed. Capture the position again."
        )

    project = Path(__file__).resolve().parents[1]
    folder = project / "reports" / "refresh_targets"
    folder.mkdir(parents=True, exist_ok=True)

    output = folder / f"{workspace['id']}.json"

    configuration = {
        "version": 1,
        "workspace_id": workspace["id"],
        "report_title": report.window_text(),
        "window_width": expected_width,
        "window_height": expected_height,
        "relative_x": x,
        "relative_y": y,
        "method": "manual_mouse_calibration",
    }

    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=folder,
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(configuration, file, indent=2)

        os.replace(temporary, output)

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    print("WORKSPACE:", workspace["name"])
    print("SAVED:", output)
    print("Configuration saved only. No refresh triggered.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("SAVE FAILED:", str(error))
        raise SystemExit(1)