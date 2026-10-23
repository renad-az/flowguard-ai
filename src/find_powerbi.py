from pywinauto import Desktop


def main():
    matches = []

    for window in Desktop(backend="uia").windows():
        title = window.window_text()

        if "Power BI Desktop" in title:
            matches.append(window)

    if not matches:
        print("NOT FOUND: Open your report in Power BI Desktop.")
        return

    for window in matches:
        print("FOUND:", window.window_text())
        print("HANDLE:", window.handle)

    if len(matches) > 1:
        print("Multiple windows found. We must select the correct report.")

    print("Discovery only. No buttons clicked.")


if __name__ == "__main__":
    main()