from pywinauto import Desktop

from workspace_store import get_active_workspace


def get_report_title():
    workspace = get_active_workspace()

    if workspace is None:
        raise RuntimeError(
            "No active workspace. Select one in Workspace Manager."
        )

    title = workspace.get("report_title", "").strip()

    if not title:
        raise RuntimeError(
            "The active workspace has no Power BI window title."
        )

    return title


def get_report_window():
    title = get_report_title()

    matches = [
        window
        for window in Desktop(backend="uia").windows()
        if window.window_text() == title
    ]

    if len(matches) == 0:
        raise RuntimeError(
            f"Report window not found: {title}"
        )

    if len(matches) > 1:
        raise RuntimeError(
            "Multiple report windows match the workspace title. "
            "Close duplicates before continuing."
        )

    return matches[0]


def main():
    try:
        workspace = get_active_workspace()
        report = get_report_window()

        print("WORKSPACE:", workspace["name"])
        print("REPORT:", report.window_text())
        print("HANDLE:", report.handle)
        print("Discovery only. No refresh triggered.")

        return 0

    except Exception as error:
        print("TARGET NOT READY:", str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())