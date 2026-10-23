from pywinauto import Desktop


def main():
    windows = [
        window
        for window in Desktop(backend="uia").windows()
        if window.window_text() == "FlowBI - Power BI Desktop"
    ]

    if len(windows) != 1:
        print("STOP: Expected exactly one FlowBI window.")
        return

    window = windows[0]
    window.set_focus()

    matches = []

    for button in window.descendants(control_type="Button"):
        if button.element_info.name != "Refresh":
            continue

        if not button.is_visible() or not button.is_enabled():
            continue

        rectangle = button.rectangle()

        # موضع الزر الظاهر في صورة الاختبار الحالية
        if (
            rectangle.left <= 920 < rectangle.right
            and rectangle.top <= 140 < rectangle.bottom
        ):
            matches.append(button)

    if len(matches) != 1:
        print("STOP: Could not identify one refresh button.")
        print("No button clicked.")
        return

    matches[0].invoke()

    print("Refresh command sent.")
    print("Completion is NOT verified. Check Power BI.")


if __name__ == "__main__":
    main()