import argparse
import json
from pathlib import Path


def compare_profiles(profile, baseline):
    errors = []
    warnings = []

    current_sheets = {
        sheet["name"]: sheet
        for sheet in profile["sheets"]
    }

    baseline_sheets = {
        sheet["name"]: sheet
        for sheet in baseline["sheets"]
    }

    for sheet_name, old_sheet in baseline_sheets.items():
        if sheet_name not in current_sheets:
            errors.append(f"Missing sheet: {sheet_name}")
            continue

        current_sheet = current_sheets[sheet_name]

        current_columns = {}

        for column in current_sheet["columns"]:
            name = column["name"]

            if not isinstance(name, str) or not name.strip():
                errors.append(
                    f"{sheet_name}: Unnamed column at "
                    f"position {column['position']}"
                )
                continue

            if name in current_columns:
                errors.append(
                    f"{sheet_name}: Duplicate column name '{name}'"
                )

            current_columns[name] = column

        old_columns = {
            column["name"]: column
            for column in old_sheet["columns"]
        }

        for column_name, old_column in old_columns.items():
            if column_name not in current_columns:
                errors.append(
                    f"{sheet_name}: Missing column '{column_name}'"
                )
                continue

            current_column = current_columns[column_name]

            old_types = set(old_column["observed_types"])
            current_types = set(current_column["types"])
            new_types = current_types - old_types

            if old_types and new_types:
                errors.append(
                    f"{sheet_name}.{column_name}: "
                    f"New value types: {', '.join(sorted(new_types))}"
                )

            elif not old_types and current_types:
                warnings.append(
                    f"{sheet_name}.{column_name}: "
                    "Previously empty column now contains values; "
                    "review its intended type."
                )

            if (
                current_column["position"]
                != old_column["position"]
            ):
                warnings.append(
                    f"{sheet_name}.{column_name}: "
                    "Column position changed."
                )

        for column_name in current_columns:
            if column_name not in old_columns:
                warnings.append(
                    f"{sheet_name}: Added column '{column_name}'"
                )

    for sheet_name in current_sheets:
        if sheet_name not in baseline_sheets:
            warnings.append(f"Added sheet: {sheet_name}")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(
        description="Compare an Excel profile with its baseline."
    )

    parser.add_argument("profile", type=Path)
    parser.add_argument("baseline", type=Path)
    args = parser.parse_args()

    try:
        profile = json.loads(
            args.profile.read_text(encoding="utf-8")
        )

        baseline = json.loads(
            args.baseline.read_text(encoding="utf-8")
        )

        if baseline.get("version") != 1:
            raise ValueError("Unsupported baseline version.")

        errors, warnings = compare_profiles(profile, baseline)

        for error in errors:
            print("BLOCKED:", error)

        for warning in warnings:
            print("WARNING:", warning)

        if errors:
            print("\nRESULT: BLOCKED — review structural changes.")

        elif warnings:
            print("\nRESULT: REVIEW — warnings need attention.")

        else:
            print("\nRESULT: PASS — no structural changes detected.")

        print("Comparison only. No files modified or refresh triggered.")

    except (OSError, ValueError, KeyError, TypeError) as error:
        print("BLOCKED: Could not compare profiles:", error)


if __name__ == "__main__":
    main()