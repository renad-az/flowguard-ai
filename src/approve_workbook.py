import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4
from zipfile import BadZipFile

from openpyxl.utils.exceptions import InvalidFileException

from inspect_excel import inspect_excel
from compare_profile import compare_profiles
from check_workbook import find_excel_errors


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(
        description="Validate and safely approve an Excel workbook."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("approved", type=Path)
    args = parser.parse_args()

    source = args.source.resolve()
    baseline_path = args.baseline.resolve()
    approved = args.approved.resolve()
    temporary = None

    try:
        if not source.is_file():
            raise ValueError("Source file not found.")

        if source.suffix.lower() != ".xlsx":
            raise ValueError("Source must be an .xlsx file.")

        if approved.suffix.lower() != ".xlsx":
            raise ValueError("Approved file must use .xlsx.")

        if approved in (source, baseline_path):
            raise ValueError("Approved path must be a separate file.")

        if approved.exists() and source.samefile(approved):
            raise ValueError("Source and approved refer to the same file.")

        baseline = json.loads(
            baseline_path.read_text(encoding="utf-8")
        )

        if baseline.get("version") != 1:
            raise ValueError("Unsupported baseline version.")

        approved.parent.mkdir(parents=True, exist_ok=True)

        # النسخة المؤقتة تكون بجانب الملف المعتمد
        with tempfile.NamedTemporaryFile(
            dir=approved.parent,
            prefix=".pending-",
            suffix=".xlsx",
            delete=False,
        ) as file:
            temporary = Path(file.name)

        original_hash = file_hash(source)
        shutil.copyfile(source, temporary)
        snapshot_hash = file_hash(temporary)

        if (
            snapshot_hash != original_hash
            or file_hash(source) != snapshot_hash
        ):
            raise ValueError(
                "Source changed during copying. Save and retry."
            )

        # نفحص نفس النسخة التي سنعتمدها
        profile = inspect_excel(temporary)
        errors, warnings = compare_profiles(profile, baseline)

        cell_errors, formula_count = find_excel_errors(temporary)
        errors.extend(cell_errors)

        if formula_count:
            warnings.append(
                "Formulas require review; recalculation is not verified."
            )

        for error in errors:
            print("BLOCKED:", error)

        for warning in warnings:
            print("WARNING:", warning)

        if errors or warnings:
            print("NOT APPROVED: Existing approved file unchanged.")
            return 1

        if file_hash(source) != snapshot_hash:
            raise ValueError(
                "Source changed during validation. Run again."
            )

        if approved.exists():
            backup_folder = approved.parent / "backups"
            backup_folder.mkdir(exist_ok=True)

            backup = backup_folder / (
                f"{approved.stem}-{uuid4().hex}.xlsx"
            )

            shutil.copy2(approved, backup)
            print("Previous approved version backed up.")

        # استبدال الملف مرة واحدة بعد اكتمال الفحص
        os.replace(temporary, approved)
        temporary = None

        print("APPROVED: Validated workbook published.")
        print("Power BI refresh has NOT been triggered.")
        return 0

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        BadZipFile,
        InvalidFileException,
    ) as error:
        print("NOT APPROVED:", error)
        return 1

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())