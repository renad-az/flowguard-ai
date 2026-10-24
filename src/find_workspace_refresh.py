import time

from pywinauto import Desktop

from powerbi_target import get_report_window


def rectangle_key(control):
    rect = control.rectangle()

    return (
        rect.left,
        rect.top,
        rect.right,
        rect.bottom,
    )


def inside_queries(control):
    parent = control.parent()

    for _ in range(8):
        if parent is None:
            return False

        name = (parent.element_info.name or "").strip()

        if name in ("Queries", "الاستعلامات"):
            return True

        parent = parent.parent()

    return False


def find_refresh_buttons(report):
    desktop = Desktop(backend="uia")
    found = {}

    for candidate in report.descendants(control_type="Button"):
        name = (candidate.element_info.name or "").strip()

        # نستبعد جزء القائمة المنسدلة Refresh Refresh
        if name not in ("Refresh", "تحديث"):
            continue

        if not candidate.is_visible() or not candidate.is_enabled():
            continue

        if not inside_queries(candidate):
            continue

        left, top, right, bottom = rectangle_key(candidate)

        if right <= left or bottom <= top:
            continue

        x = (left + right) // 2
        y = (top + bottom) // 2

        # نفحص العنصر الموجود فعليًا أمام المستخدم
        hit = desktop.from_point(x, y)

        for _ in range(6):
            if hit is None:
                break

            if hit.element_info.control_type == "Button":
                break

            hit = hit.parent()

        if hit is None:
            continue

        hit_name = (hit.element_info.name or "").strip()

        if hit_name not in ("Refresh", "تحديث"):
            continue

        if hit.process_id() != candidate.process_id():
            continue

        if not inside_queries(hit):
            continue

        if rectangle_key(hit) != rectangle_key(candidate):
            continue

        found[rectangle_key(hit)] = hit

    return list(found.values())


def main():
    try:
        report = get_report_window()
        report.set_focus()
        time.sleep(1)

        matches = find_refresh_buttons(report)

        print("REPORT:", report.window_text())
        print("VERIFIED BUTTONS:", len(matches))

        for button in matches:
            print("NAME:", button.element_info.name)
            print("RECTANGLE:", button.rectangle())

        if len(matches) == 1:
            print("One visible refresh target identified.")
        else:
            print("STOP: No unique target. No guessing.")

        print("Discovery only. No button invoked.")
        return 0 if len(matches) == 1 else 1

    except Exception as error:
        print("DISCOVERY FAILED:", type(error).__name__, str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
