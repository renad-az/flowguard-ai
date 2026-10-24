from pywinauto import Desktop
from powerbi_target import get_report_window


def main():
    report = get_report_window()
    report.set_focus()

    print("REPORT:", report.window_text())

    desktop = Desktop(backend="uia")
    count = 0

    for control in report.descendants(control_type="Button"):
        name = (control.element_info.name or "").strip()

        if "refresh" not in name.lower() and "تحديث" not in name:
            continue

        count += 1
        print(f"\nCANDIDATE {count}")
        print("Name:", repr(name))
        print("Visible:", control.is_visible())
        print("Enabled:", control.is_enabled())

        rect = control.rectangle()
        print("Rectangle:", rect)

        parent = control.parent()

        for level in range(1, 6):
            if parent is None:
                break

            print(
                f"Parent {level}:",
                repr(parent.element_info.name),
                "| Type:",
                parent.element_info.control_type,
            )
            parent = parent.parent()

        if rect.right > rect.left and rect.bottom > rect.top:
            x = (rect.left + rect.right) // 2
            y = (rect.top + rect.bottom) // 2

            try:
                hit = desktop.from_point(x, y)

                for level in range(4):
                    if hit is None:
                        break

                    print(
                        f"At center, level {level}:",
                        repr(hit.element_info.name),
                        "| Type:",
                        hit.element_info.control_type,
                        "| Rectangle:",
                        hit.rectangle(),
                    )
                    hit = hit.parent()

            except Exception as error:
                print("Center inspection failed:", type(error).__name__, str(error))

    print("\nCandidates found:", count)
    print("Discovery only. No buttons clicked.")


if __name__ == "__main__":
    main()