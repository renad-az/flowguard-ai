import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from workspace_store import (
    activate_workspace,
    get_active_workspace,
    list_workspaces,
    load_store,
    save_workspace,
)


PROJECT_FOLDER = Path(__file__).resolve().parent.parent


class WorkspaceManager:
    def __init__(self, root):
        self.root = root
        self.workspace_id = None
        self.workspace_ids = {}

        self.selected = tk.StringVar()
        self.name = tk.StringVar()
        self.source = tk.StringVar()
        self.baseline = tk.StringVar()
        self.approved = tk.StringVar()
        self.report_title = tk.StringVar()
        self.status = tk.StringVar(value="Create or choose a workspace")

        root.title("FlowGuard AI — Workspaces")
        root.geometry("900x510")

        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="Workspaces",
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(
            frame,
            text="Independent settings for each data source and report",
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(4, 18),
        )

        self.workspace_picker = ttk.Combobox(
            frame,
            textvariable=self.selected,
            state="readonly",
        )
        self.workspace_picker.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 16),
        )
        self.workspace_picker.bind(
            "<<ComboboxSelected>>",
            self.load_selected,
        )

        ttk.Button(
            frame,
            text="New Workspace",
            command=self.new_workspace,
        ).grid(row=2, column=2, padx=(12, 0), pady=(0, 16))

        ttk.Label(frame, text="Workspace name").grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=8
        )
        ttk.Entry(
            frame,
            textvariable=self.name,
        ).grid(row=3, column=1, columnspan=2, sticky="ew")

        self.add_file_row(
            frame, 4, "Source Excel", self.source, self.choose_source
        )
        self.add_file_row(
            frame, 5, "Reviewed baseline", self.baseline, self.choose_baseline
        )
        self.add_file_row(
            frame, 6, "Approved Excel", self.approved, self.choose_approved
        )

        ttk.Label(frame, text="Power BI window title").grid(
            row=7, column=0, sticky="w", padx=(0, 12), pady=8
        )
        ttk.Entry(
            frame,
            textvariable=self.report_title,
        ).grid(row=7, column=1, columnspan=2, sticky="ew")

        ttk.Label(
            frame,
            text="Use the exact window title, including '- Power BI Desktop'.",
        ).grid(
            row=8,
            column=1,
            columnspan=2,
            sticky="w",
        )

        ttk.Button(
            frame,
            text="Save and Select Workspace",
            command=self.save,
        ).grid(
            row=9,
            column=0,
            columnspan=3,
            sticky="w",
            pady=20,
        )

        ttk.Label(
            frame,
            textvariable=self.status,
            wraplength=800,
        ).grid(row=10, column=0, columnspan=3, sticky="w")

        self.refresh_choices()

        active = get_active_workspace()
        if active is not None:
            self.fill_workspace(active["id"], active)

    def add_file_row(self, frame, row, label, variable, command):
        ttk.Label(frame, text=label).grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=8
        )
        ttk.Entry(
            frame,
            textvariable=variable,
            state="readonly",
        ).grid(row=row, column=1, sticky="ew")
        ttk.Button(
            frame,
            text="Browse",
            command=command,
        ).grid(row=row, column=2, padx=(12, 0))

    def choose_source(self):
        path = filedialog.askopenfilename(
            initialdir=PROJECT_FOLDER / "data" / "incoming",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if path:
            self.source.set(path)

    def choose_baseline(self):
        path = filedialog.askopenfilename(
            initialdir=PROJECT_FOLDER / "reports" / "baselines",
            filetypes=[("JSON file", "*.json")],
        )
        if path:
            self.baseline.set(path)

    def choose_approved(self):
        path = filedialog.asksaveasfilename(
            title="Choose approved workbook destination",
            initialdir=PROJECT_FOLDER / "data" / "approved",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if path:
            self.approved.set(path)

    def refresh_choices(self):
        workspaces = list_workspaces()

        self.workspace_ids = {
            item["name"]: item["id"]
            for item in workspaces
        }

        self.workspace_picker.configure(
            values=list(self.workspace_ids)
        )

    def fill_workspace(self, workspace_id, workspace):
        self.workspace_id = workspace_id
        self.selected.set(workspace["name"])
        self.name.set(workspace["name"])
        self.source.set(workspace["source"])
        self.baseline.set(workspace["baseline"])
        self.approved.set(workspace["approved"])
        self.report_title.set(workspace["report_title"])
        self.status.set("Workspace loaded. Monitoring has not started.")

    def load_selected(self, event=None):
        try:
            workspace_id = self.workspace_ids[self.selected.get()]
            store = load_store()
            workspace = store["workspaces"][workspace_id]

            activate_workspace(workspace_id)
            self.fill_workspace(workspace_id, workspace)

        except Exception as error:
            messagebox.showerror("Could not load workspace", str(error))

    def new_workspace(self):
        self.workspace_id = None

        for variable in (
            self.selected,
            self.name,
            self.source,
            self.baseline,
            self.approved,
            self.report_title,
        ):
            variable.set("")

        self.status.set(
            "New workspace. Existing workspaces remain unchanged."
        )

    def save(self):
        try:
            if not Path(self.source.get()).is_file():
                raise ValueError("Choose an existing source workbook.")

            if not Path(self.baseline.get()).is_file():
                raise ValueError("Choose an existing reviewed baseline.")

            workspace_id = save_workspace(
                name=self.name.get(),
                source=self.source.get(),
                baseline=self.baseline.get(),
                approved=self.approved.get(),
                report_title=self.report_title.get(),
                workspace_id=self.workspace_id,
            )

            self.workspace_id = workspace_id
            self.refresh_choices()
            self.selected.set(self.name.get().strip())

            self.status.set(
                "Workspace saved locally. "
                "No files copied and no monitoring started."
            )

        except Exception as error:
            messagebox.showerror("Could not save workspace", str(error))


def main():
    root = tk.Tk()

    try:
        WorkspaceManager(root)
    except Exception as error:
        messagebox.showerror("Could not open workspaces", str(error))
        root.destroy()
        return

    root.mainloop()


if __name__ == "__main__":
    main()