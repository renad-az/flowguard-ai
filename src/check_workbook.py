import argparse
import json
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from inspect_excel import inspect_excel
from compare_profile import compare_profiles


def find_excel_errors(source_file):
    errors = []
    seen_cells = set()
    formula_count = 0

    # نفحص الخلايا الأصلية، ثم نتائج الصيغ المحفوظة
    for cached_values in (False, True):
        workbook = load_workbook(
            source_file,
            read_only=True,
            data_only=cached_values,
        )

        try:
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if (
                            not cached_values
                            and cell.data_type == "f"
                        ):
                            formula_count += 1

                        if cell.data_type != "e":
                            continue

                        location = (sheet.title, cell.coordinate)

                        if location in seen_cells:
                            continue

                        seen_cells.add(location)

                        errors.append(
                            f"{sheet.title}!{cell.coordinate}: "
                            f"Excel error {cell.value}"
                        )

        finally:
            workbook.close()

    return errors, formula_count


def main():
    parser = argparse.ArgumentParser(
        description="Check Excel structure and stored cell errors."
    )

    parser.add_argument("file", type=Path)
    parser.add_argument("baseline", type=Path)
    args = parser.parse_args()

    source_file = args.file.resolve()

    if not source_file.is_file():
        parser.error(f"File not found: {source_file}")

    if source_file.suffix.lower() != ".xlsx":
        parser.error("This version supports .xlsx files only.")

    try:
        baseline = json.loads(
            args.baseline.read_text(encoding="utf-8")
        )

        if baseline.get("version") != 1:
            raise ValueError("Unsupported baseline version.")

        current_profile = inspect_excel(source_file)

        errors, warnings = compare_profiles(
            current_profile,
            baseline,
        )

        cell_errors, formula_count = find_excel_errors(
            source_file
        )

        errors.extend(cell_errors)

        if formula_count:
            warnings.append(
                f"Found {formula_count} formulas. "
                "Stored results were checked, but formulas "
                "were not recalculated. Results may be stale "
                "or unavailable."
            )

        for error in errors:
            print("BLOCKED:", error)

        for warning in warnings:
            print("WARNING:", warning)

        if errors:
            print("\nRESULT: BLOCKED — review detected issues.")
            return 1

        if warnings:
            print("\nRESULT: REVIEW — warnings need attention.")
            return 2

        print(
            "\nRESULT: PASS — structure matches and "
            "no stored Excel cell errors detected."
        )
        return 0

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        BadZipFile,
        InvalidFileException,
    ) as error:
        print("BLOCKED: Could not complete inspection:", error)
        return 1

    finally:
        print("No data copied, modified, or refreshed.")


if __name__ == "__main__":
    raise SystemExit(main())