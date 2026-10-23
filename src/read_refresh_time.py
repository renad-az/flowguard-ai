import re

from pywinauto import Desktop


TIMESTAMP_PATTERN = re.compile(
    r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}"
    r"[,\s]+\d{1,2}:\d{2}(?::\d{2})?"
    r"(?:\s*[AP]M)?",
    re.IGNORECASE,
)


def read_refresh_time(
    report_title="FlowBI - Power BI Desktop",
    card_title="Refresh Check Time",
):
    reports = [
        window
        for window in Desktop(backend="uia").windows()
        if window.window_text() == report_title
    ]

    if len(reports) != 1:
        raise RuntimeError(
            "Expected exactly one matching Power BI report."
        )

    times = set()
    matching_cards = 0

    for control in reports[0].descendants(
        control_type="DataItem"
    ):
        if not control.is_visible():
            continue

        name = (control.element_info.name or "").strip()

        if not name.startswith(card_title + ","):
            continue

        match = TIMESTAMP_PATTERN.search(name)

        if match is not None:
            matching_cards += 1
            times.add(match.group(0))

    if not times:
        raise RuntimeError(
            "Refresh Check Time card was not readable. "
            "Check its title and visibility."
        )

    if matching_cards != 1:
        raise RuntimeError(
            "Multiple timestamp card elements found. "
            "Cannot select one safely."
        )

    return times.pop()


def main():
    try:
        timestamp = read_refresh_time()
        print("REFRESH CHECK TIME:", timestamp)
        print("Read only. No refresh triggered.")

    except Exception as error:
        print("READ FAILED:", type(error).__name__, str(error))
        raise SystemExit(1)


if __name__ == "__main__":
    main()