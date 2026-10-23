import re

from pywinauto import Desktop


def main():
    reports = [
        window
        for window in Desktop(backend="uia").windows()
        if window.window_text() == "FlowBI - Power BI Desktop"
    ]

    if len(reports) != 1:
        print("STOP: Expected exactly one FlowBI report.")
        return

    report = reports[0]

    # نبحث عن نص يحتوي تاريخًا ووقتًا، مثل:
    # 24/10/2026 00:50:53
    pattern = re.compile(
        r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}"
        r"[,\s]+\d{1,2}:\d{2}(?::\d{2})?"
        r"(?:\s*[AP]M)?",
        re.IGNORECASE,
    )

    found = set()
    read_errors = 0

    for control in report.descendants():
        try:
            if not control.is_visible():
                continue

            name = control.element_info.name or ""

            for match in pattern.finditer(name):
                timestamp = match.group(0)

                if timestamp not in found:
                    found.add(timestamp)
                    print("CANDIDATE TIME:", timestamp)
                    print(
                        "CONTROL TYPE:",
                        control.element_info.control_type,
                    )

        except Exception:
            read_errors += 1

    if not found:
        print("NOT FOUND: No readable timestamp captured.")
        print(
            "The card may not expose its value through "
            "Windows accessibility."
        )
    else:
        print(
            "Discovery only. These times are not yet "
            "confirmed as the RefreshCheck card."
        )

    if read_errors:
        print("Controls that could not be inspected:", read_errors)


if __name__ == "__main__":
    main()