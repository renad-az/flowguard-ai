import argparse
from pathlib import Path

from openpyxl import load_workbook


def inspect_excel(file_path):
    workbook = load_workbook(file_path, read_only=True)

    try:
        print(f"File: {file_path.name}")

        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, ())

            nonempty_rows = sum(
                1
                for row in rows
                if any(value is not None for value in row)
            )

            print(f"\nSheet: {sheet.title}")
            print(f"Data rows: {nonempty_rows}")
            print("First row:", list(headers))

    finally:
        workbook.close()


def main():
    parser = argparse.ArgumentParser(
        description="Inspect the structure of an Excel workbook."
    )

    parser.add_argument("file", type=Path)
    args = parser.parse_args()

    file_path = args.file.resolve()

    if not file_path.is_file():
        parser.error(f"File not found: {file_path}")

    if file_path.suffix.lower() != ".xlsx":
        parser.error("This version supports .xlsx files only.")

    inspect_excel(file_path)


if __name__ == "__main__":
    main()