import ctypes
import time
from ctypes import wintypes

from powerbi_target import get_report_window


def main():
    report = get_report_window()
    report.set_focus()

    print("Move the mouse over the CENTER of the Refresh icon.")
    print("Do not click. Capturing in 8 seconds...")
    time.sleep(8)

    point = wintypes.POINT()

    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        raise RuntimeError("Could not read mouse position.")

    rect = report.rectangle()

    if not (
        rect.left <= point.x < rect.right
        and rect.top <= point.y < rect.bottom
    ):
        raise RuntimeError("Mouse is outside the report window.")

    print("REPORT:", report.window_text())
    print("WINDOW SIZE:", rect.width(), rect.height())
    print("RELATIVE POSITION:", point.x - rect.left, point.y - rect.top)
    print("Position captured only. No click or refresh triggered.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("CAPTURE FAILED:", str(error))
        raise SystemExit(1)