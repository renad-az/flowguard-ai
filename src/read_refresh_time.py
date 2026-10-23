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

    locations = {}

    for control in reports[0].descendants(
        control_type="DataItem"
    ):
        if not control.is_visible():
            continue

        name = (control.element_info.name or "").strip()

        if not name.startswith(card_title + ","):
            continue

        match = TIMESTAMP_PATTERN.search(name)

        if match is None:
            continue

        rectangle = control.rectangle()

        if (
            rectangle.right <= rectangle.left
            or rectangle.bottom <= rectangle.top
        ):
            continue

        location = (
            rectangle.left,
            rectangle.top,
            rectangle.right,
            rectangle.bottom,
        )

        timestamp = match.group(0)

        if location not in locations:
            locations[location] = set()

        locations[location].add(timestamp)

    if not locations:
        raise RuntimeError(
            "Refresh Check Time card was not readable. "
            "Check its title and visibility."
        )

    if len(locations) != 1:
        raise RuntimeError(
            "Timestamp cards found at different locations. "
            "Cannot select one safely."
        )

    times = next(iter(locations.values()))

    if len(times) != 1:
        raise RuntimeError(
            "Conflicting timestamps detected. Try again."
        )

    return next(iter(times))


def main():
    try:
        timestamp = read_refresh_time()

        print("REFRESH CHECK TIME:", timestamp)
        print("Read only. No refresh triggered.")

    except Exception as error:
        print(
            "READ FAILED:",
            type(error).__name__,
            str(error),
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()