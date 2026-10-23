import argparse
import json
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path

from openpyxl import load_workbook


def is_empty(value):
    return value is None or (
        isinstance(value, str) and value.strip() == ""
    )


def detect_type(cell):
    if cell.data_type == "f":
        return "formula"

    if cell.data_type == "e":
        return "excel_error"

    value = cell.value

    if isinstance(value, bool):
        return "boolean"

    if isinstance(value, (datetime, date, time)):
        return "date_or_time"

    if isinstance(value, (int, float)):
        return "number"

    if isinstance(value, str):
        return "text"

    return "other"


def inspect_excel(file_path):
    workbook = load_workbook(
        file_path,
        read_only=True,
        data_only=False,
    )

    profile = {
        "assumptions": [
            "The first row is treated as column headers.",
            "Completely empty data rows are excluded.",
            "Missing values are observations, not confirmed errors.",
            "Formulas are identified but not evaluated.",
        ],
        "sheets": [],
    }

    try:
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows()
            header_cells = next(rows, ())

            columns = [
                {
                    "position": index,
                    "name": (
                        str(cell.value)
                        if not is_empty(cell.value)
                        else None
                    ),
                    "missing_count": 0,
                    "types": Counter(),
                }
                for index, cell in enumerate(header_cells, start=1)
            ]

            data_rows = 0

            for row in rows:
                if all(is_empty(cell.value) for cell in row):
                    continue

                data_rows += 1

                for index, column in enumerate(columns):
                    if (
                        index >= len(row)
                        or is_empty(row[index].value)
                    ):
                        column["missing_count"] += 1
                    else:
                        value_type = detect_type(row[index])
                        column["types"][value_type] += 1

            for column in columns:
                column["types"] = dict(column["types"])

                column["missing_percent"] = (
                    round(
                        column["missing_count"] / data_rows * 100,
                        2,
                    )
                    if data_rows
                    else None
                )

            profile["sheets"].append({
                "name": sheet.title,
                "data_rows": data_rows,
                "columns": columns,
            })

    finally:
        workbook.close()

    return profile


def main():
    parser = argparse.ArgumentParser(
        description="Create an Excel column profile without cell values."
    )

    parser.add_argument("file", type=Path)

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/data_profile.json"),
    )

    args = parser.parse_args()
    file_path = args.file.resolve()

    if not file_path.is_file():
        parser.error(f"File not found: {file_path}")

    if file_path.suffix.lower() != ".xlsx":
        parser.error("This version supports .xlsx files only.")

    profile = inspect_excel(file_path)

    output_path = args.output.resolve()

    if output_path == file_path:
        parser.error("Output must not overwrite the source workbook.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Profile saved: {output_path}")
    print(f"Sheets inspected: {len(profile['sheets'])}")
    print("No cell values included. No AI request sent.")


if __name__ == "__main__":
    main()