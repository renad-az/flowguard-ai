import argparse
import hashlib
import json
import os
import tempfile
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook


def main():
    parser = argparse.ArgumentParser(
        description="Create and verify a separate corrected workbook."
    )

    parser.add_argument("source", type=Path)
    parser.add_argument("preview", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--confirm", action="store_true")

    args = parser.parse_args()

    if not args.confirm:
        parser.error("Review the preview, then use --confirm.")

    source = args.source.resolve()
    preview_path = args.preview.resolve()
    output = args.output.resolve()

    if output in (source, preview_path):
        parser.error("Output must be a separate file.")

    if output.suffix.lower() != ".xlsx":
        parser.error("Output must use .xlsx.")

    if output.exists():
        parser.error("Output already exists. Choose a new filename.")

    workbook = None
    temporary = None

    try:
        plan = json.loads(
            preview_path.read_text(encoding="utf-8")
        )

        if plan.get("version") != 1:
            raise ValueError("Unsupported preview version.")

        source_bytes = source.read_bytes()
        source_hash = hashlib.sha256(source_bytes).hexdigest()

        if source_hash != plan["source_sha256"]:
            raise ValueError(
                "Source changed since preview. Create a new preview."
            )

        candidates = plan["candidates"]

        if not candidates:
            raise ValueError("No corrections in this preview.")

        workbook = load_workbook(
            BytesIO(source_bytes),
            data_only=False,
        )

        original_sheets = list(workbook.sheetnames)
        expected_values = {}
        seen = set()

        for candidate in candidates:
            if candidate["action"] != "trim_outer_spaces":
                raise ValueError("Unsupported correction.")

            sheet_name = candidate["sheet"]
            coordinate = candidate["cell"]
            column_name = candidate["column"]

            if sheet_name not in workbook.sheetnames:
                raise ValueError("Preview sheet not found.")

            sheet = workbook[sheet_name]
            cell = sheet[coordinate]

            if cell.row < 2:
                raise ValueError("Header corrections are not allowed.")

            if sheet.cell(1, cell.column).value != column_name:
                raise ValueError("Preview column does not match.")

            key = (sheet_name, cell.coordinate)

            if key in seen:
                raise ValueError("Duplicate correction.")

            seen.add(key)

            if (
                cell.data_type != "s"
                or not isinstance(cell.value, str)
            ):
                raise ValueError("Only text cells can be trimmed.")

            trimmed = cell.value.strip()

            if not trimmed or trimmed == cell.value:
                raise ValueError("Candidate is not a valid trim.")

            cell.value = trimmed
            expected_values[key] = trimmed

        output.parent.mkdir(parents=True, exist_ok=True)

        # نغلق الملف المؤقت قبل استخدامه مع مكتبة Excel
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            prefix=".trim-pending-",
            suffix=".xlsx",
            delete=False,
        ) as file:
            temporary = Path(file.name)

        workbook.save(str(temporary))
        workbook.close()
        workbook = None

        # فحص سلامة الأرشيف الذي يتكون منه ملف xlsx
        with ZipFile(temporary, "r") as archive:
            bad_member = archive.testzip()

            if bad_member is not None:
                raise ValueError("Workbook archive integrity failed.")

        # إعادة فتح النسخة والتأكد من الخلايا المصححة
        verified = load_workbook(
            temporary,
            read_only=True,
            data_only=False,
        )

        try:
            if verified.sheetnames != original_sheets:
                raise ValueError("Worksheet list changed unexpectedly.")

            for (sheet_name, coordinate), expected in expected_values.items():
                if verified[sheet_name][coordinate].value != expected:
                    raise ValueError(
                        f"Correction verification failed: "
                        f"{sheet_name}!{coordinate}"
                    )
        finally:
            verified.close()

        if hashlib.sha256(source.read_bytes()).hexdigest() != source_hash:
            raise ValueError(
                "Source changed during correction. Preview again."
            )

        # نشر الملف المكتمل بدون استبدال وجهة موجودة
        # يحتاج نظام ملفات يدعم hard links، مثل NTFS
        os.link(temporary, output)

        print("CORRECTED COPY:", output)
        print("Cells trimmed:", len(seen))
        print("Archive and corrected-cell checks passed.")
        print("Original source and approved workbook unchanged.")
        print("No Power BI refresh triggered.")
        return 0

    except FileExistsError:
        print("CORRECTION FAILED: Output already exists.")
        return 1

    except Exception as error:
        print("CORRECTION FAILED:", type(error).__name__, str(error))
        return 1

    finally:
        if workbook is not None:
            workbook.close()

        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())