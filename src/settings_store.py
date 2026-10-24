import json
import os
import tempfile
from pathlib import Path


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
SETTINGS_FILE = PROJECT_FOLDER / "reports" / "settings.json"


def save_settings(source, baseline, approved, refresh):
    values = {
        "source": source,
        "baseline": baseline,
        "approved": approved,
    }

    if any(not value.strip() for value in values.values()):
        raise ValueError("Choose all three files before saving.")

    settings = {
        "version": 1,
        "source": str(Path(source).resolve()),
        "baseline": str(Path(baseline).resolve()),
        "approved": str(Path(approved).resolve()),
        "refresh": bool(refresh),
    }

    if settings["source"] == settings["approved"]:
        raise ValueError("Source and approved must be separate.")

    if settings["baseline"] == settings["approved"]:
        raise ValueError("Approved must not replace the baseline.")

    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=SETTINGS_FILE.parent,
            prefix=".settings-",
            suffix=".json",
            delete=False,
        ) as file:
            temporary = Path(file.name)
            json.dump(
                settings,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(temporary, SETTINGS_FILE)
        temporary = None

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_settings():
    if not SETTINGS_FILE.exists():
        return None

    settings = json.loads(
        SETTINGS_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(settings, dict):
        raise ValueError("Saved settings must be an object.")

    if settings.get("version") != 1:
        raise ValueError("Unsupported settings version.")

    for key in ("source", "baseline", "approved"):
        value = settings.get(key)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Invalid saved setting: {key}")

    if not isinstance(settings.get("refresh"), bool):
        raise ValueError("Invalid saved refresh setting.")

    return settings