import argparse
import json
from pathlib import Path
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from inspect_excel import inspect_excel
from compare_profile import compare_profiles


def main():
    parser = argparse.ArgumentParser(
        description="Read an Excel workbook and compare its structure."
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

        # قراءة Excel الآن، بدون الاعتماد على وصف محفوظ قديم
        current_profile = inspect_excel(source_file)

        errors, warnings = compare_profiles(
            current_profile,
            baseline,
        )

        for error in errors:
            print("BLOCKED:", error)

        for warning in warnings:
            print("WARNING:", warning)

        if errors:
            print("\nRESULT: BLOCKED — review structural changes.")
            return 1

        if warnings:
            print("\nRESULT: REVIEW — warnings need attention.")
            return 2

        print("\nRESULT: PASS — no structural changes detected.")
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