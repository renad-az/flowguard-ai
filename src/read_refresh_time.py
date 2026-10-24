import re

from powerbi_target import get_report_window


TIMESTAMP_PATTERN = re.compile(
    r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}"
    r"[,\s]+\d{1,2}:\d{2}(?::\d{2})?"
    r"(?:\s*[AP]M)?",
    re.IGNORECASE,
)


def read_refresh_time(card_title="Refresh Check Time"):
    report = get_report_window()
    locations = {}

    for control in report.descendants(
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

        if location not in locations:
            locations[location] = set()

        locations[location].add(match.group(0))

    if not locations:
        raise RuntimeError(
            "Refresh timestamp card was not readable "
            "in the active workspace report."
        )

    if len(locations) != 1:
        raise RuntimeError(
            "Timestamp cards found at different locations."
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
        print("Read from the active workspace report.")
        print("No refresh triggered.")

        return 0

    except Exception as error:
        print(
            "READ FAILED:",
            type(error).__name__,
            str(error),
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())