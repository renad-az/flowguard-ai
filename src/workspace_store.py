import json
import os
import tempfile
from pathlib import Path
from uuid import uuid4


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
WORKSPACES_FILE = PROJECT_FOLDER / "reports" / "workspaces.json"


def load_store():
    if not WORKSPACES_FILE.exists():
        return {
            "version": 1,
            "active_workspace": None,
            "workspaces": {},
        }

    store = json.loads(
        WORKSPACES_FILE.read_text(encoding="utf-8")
    )

    if not isinstance(store, dict):
        raise ValueError("Workspace store must be an object.")

    if store.get("version") != 1:
        raise ValueError("Unsupported workspace store version.")

    if not isinstance(store.get("workspaces"), dict):
        raise ValueError("Invalid workspace collection.")

    active = store.get("active_workspace")

    if active is not None and active not in store["workspaces"]:
        raise ValueError("Active workspace does not exist.")

    return store


def write_store(store):
    WORKSPACES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=WORKSPACES_FILE.parent,
            prefix=".workspaces-",
            suffix=".json",
            delete=False,
        ) as file:
            temporary = Path(file.name)

            json.dump(
                store,
                file,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(temporary, WORKSPACES_FILE)
        temporary = None

    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def list_workspaces():
    store = load_store()

    return [
        {
            "id": workspace_id,
            "name": workspace["name"],
        }
        for workspace_id, workspace in store["workspaces"].items()
    ]


def get_active_workspace():
    store = load_store()
    workspace_id = store["active_workspace"]

    if workspace_id is None:
        return None

    return {
        "id": workspace_id,
        **store["workspaces"][workspace_id],
    }


def save_workspace(
    name,
    source,
    baseline,
    approved,
    report_title="",
    workspace_id=None,
):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("A workspace name is required.")

    paths = {
        "source": source,
        "baseline": baseline,
        "approved": approved,
    }

    for label, value in paths.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"A {label} path is required.")

    normalized = {
        key: str(Path(value).resolve())
        for key, value in paths.items()
    }

    if len(set(normalized.values())) != 3:
        raise ValueError(
            "Source, baseline and approved must be separate files."
        )

    if not isinstance(report_title, str):
        raise ValueError("Report title must be text.")

    store = load_store()

    if workspace_id is not None:
        if workspace_id not in store["workspaces"]:
            raise ValueError("Workspace not found.")

    for existing_id, workspace in store["workspaces"].items():
        if (
            existing_id != workspace_id
            and workspace["name"].casefold() == name.strip().casefold()
        ):
            raise ValueError("Another workspace already uses this name.")

    if workspace_id is None:
        workspace_id = uuid4().hex
        policies = []
    else:
        policies = store["workspaces"][workspace_id].get(
            "correction_policies",
            [],
        )

    store["workspaces"][workspace_id] = {
        "name": name.strip(),
        **normalized,
        "report_title": report_title.strip(),
        "correction_policies": policies,
    }

    store["active_workspace"] = workspace_id
    write_store(store)

    return workspace_id


def activate_workspace(workspace_id):
    store = load_store()

    if workspace_id not in store["workspaces"]:
        raise ValueError("Workspace not found.")

    store["active_workspace"] = workspace_id
    write_store(store)