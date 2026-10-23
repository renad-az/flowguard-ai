import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Save a reviewed workbook structure."
    )

    parser.add_argument("profile", type=Path)
    parser.add_argument("output", type=Path)

    args = parser.parse_args()

    try:
        profile = json.loads(
            args.profile.read_text(encoding="utf-8")
        )

        baseline = {
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "assumptions": profile.get("assumptions", []),
            "sheets": [],
        }

        for sheet in profile["sheets"]:
            names = [
                column["name"]
                for column in sheet["columns"]
            ]

            if any(
                not isinstance(name, str) or not name.strip()
                for name in names
            ):
                raise ValueError(
                    f"Missing column names in sheet: {sheet['name']}"
                )

            if len(names) != len(set(names)):
                raise ValueError(
                    f"Duplicate column names in sheet: {sheet['name']}"
                )

            baseline["sheets"].append({
                "name": sheet["name"],
                "columns": [
                    {
                        "name": column["name"],
                        "position": column["position"],
                        "observed_types": sorted(
                            column["types"].keys()
                        ),
                    }
                    for column in sheet["columns"]
                ],
            })

        output_path = args.output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # x يمنع استبدال مرجع موجود بالغلط
        with output_path.open("x", encoding="utf-8") as file:
            json.dump(
                baseline,
                file,
                ensure_ascii=False,
                indent=2,
            )

        print(f"Baseline saved: {output_path}")
        print(f"Sheets: {len(baseline['sheets'])}")
        print("No Excel files modified.")

    except FileExistsError:
        print("BLOCKED: Baseline already exists.")
        print("Use a different filename for a reviewed new version.")

    except (OSError, ValueError, KeyError, TypeError) as error:
        print("BLOCKED: Could not create baseline:", error)


if __name__ == "__main__":
    main()