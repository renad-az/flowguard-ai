import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app import FlowGuardApp
from ai_review_window import AIReviewWindow
from correction_window import CorrectionWindow
from workspace_manager import WorkspaceManager
from workspace_store import get_active_workspace


SCRIPT_FOLDER = Path(__file__).resolve().parent


class FlowGuardDesktop(FlowGuardApp):
    def __init__(self, root):
        super().__init__(root)

        self.tool_window = None
        self.loaded_workspace = None

        actions = self.start_button.master

        self.ai_button = ttk.Button(
            actions,
            text="AI Review",
            command=self.open_ai_review,
        )
        self.ai_button.pack(side="left", padx=(12, 0))

        self.correction_button = ttk.Button(
            actions,
            text="Corrections",
            command=self.open_corrections,
        )
        self.correction_button.pack(side="left", padx=(8, 0))

        self.workspace_button = ttk.Button(
            actions,
            text="Workspaces",
            command=self.open_workspaces,
        )
        self.workspace_button.pack(side="left", padx=(8, 0))

        self.root.geometry("1050x720")

        self.workspace_label = ttk.Label(
            actions.master,
            text="",
            font=("Segoe UI", 10, "bold"),
        )
        self.workspace_label.grid(
            row=10,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )

        self.restore_workspace()
        self.set_busy(False)

    def set_busy(self, busy):
        super().set_busy(busy)

        for name in (
            "ai_button",
            "correction_button",
            "workspace_button",
        ):
            if hasattr(self, name):
                getattr(self, name).configure(
                    state="disabled" if busy else "normal"
                )

        # File paths are managed together through Workspaces.
        for button in self.file_buttons:
            button.configure(state="disabled")

    def restore_workspace(self):
        self.loaded_workspace = None
        self.enable_refresh.set(False)

        for variable in (
            self.source,
            self.baseline,
            self.approved,
        ):
            variable.set("")

        try:
            workspace = get_active_workspace()

            if workspace is None:
                self.workspace_label.configure(
                    text="Workspace: None — choose Workspaces"
                )
                self.status.set("Choose a workspace")
                return

            self.loaded_workspace = workspace
            self.source.set(workspace["source"])
            self.baseline.set(workspace["baseline"])
            self.approved.set(workspace["approved"])

            self.workspace_label.configure(
                text=f"Workspace: {workspace['name']}"
            )

            missing = [
                label
                for label in ("source", "baseline")
                if not Path(workspace[label]).is_file()
            ]

            if missing:
                self.status.set("Workspace needs updated file paths")
                self.write_log(
                    "Files not found: "
                    + ", ".join(missing)
                    + "\n"
                )
            else:
                self.status.set("Workspace loaded — ready")

            self.write_log(
                f"Workspace loaded: {workspace['name']}\n"
                "Monitoring has not started. "
                "Refresh is disabled until selected.\n"
            )

        except Exception as error:
            self.workspace_label.configure(
                text="Workspace: Could not load"
            )
            self.status.set("Could not load workspace")
            self.write_log(f"Workspace error: {error}\n")

    def workspace_matches(self):
        try:
            if self.loaded_workspace is None:
                raise RuntimeError("Choose a workspace first.")

            if get_active_workspace() != self.loaded_workspace:
                raise RuntimeError(
                    "Workspace settings changed. Open Workspaces "
                    "and close it to reload the selected workspace."
                )

            for label, variable in (
                ("source", self.source),
                ("baseline", self.baseline),
                ("approved", self.approved),
            ):
                if variable.get() != self.loaded_workspace[label]:
                    raise RuntimeError(
                        "Displayed files do not match the workspace. "
                        "Reload it through Workspaces."
                    )

            return True

        except Exception as error:
            messagebox.showerror(
                "Workspace needs review",
                str(error),
                parent=self.root,
            )
            return False

    def open_workspaces(self):
        if self.running or self.tool_is_open():
            return

        window = tk.Toplevel(self.root)
        self.tool_window = window

        try:
            WorkspaceManager(window)
            window.transient(self.root)
            window.grab_set()

            self.root.wait_window(window)
            self.restore_workspace()

        except Exception as error:
            if window.winfo_exists():
                window.destroy()

            self.restore_workspace()
            messagebox.showerror(
                "Could not open workspaces",
                str(error),
                parent=self.root,
            )

        finally:
            self.tool_window = None

    def start_check(self):
        if self.running or not self.workspace_matches():
            return

        super().start_check()

    def start_monitor(self):
        if self.running or not self.workspace_matches():
            return

        if not self.validate_files(monitoring=True):
            return

        workspace = self.loaded_workspace

        if self.enable_refresh.get():
            if not workspace.get("report_title", "").strip():
                messagebox.showerror(
                    "Report required",
                    "Set the Power BI window title in Workspaces.",
                    parent=self.root,
                )
                return

            calibration = (
                SCRIPT_FOLDER.parent
                / "reports"
                / "refresh_targets"
                / f"{workspace['id']}.json"
            )

            if not calibration.is_file():
                messagebox.showerror(
                    "Calibration required",
                    "Capture and save the Refresh position "
                    "for this workspace first.",
                    parent=self.root,
                )
                return

            confirmed = messagebox.askokcancel(
                "Start with Power BI refresh",
                f"Report: {workspace['report_title']}\n\n"
                "Keep Home selected, use the calibrated window "
                "size and ribbon layout, and keep Refresh Check "
                "Time visible.\n\n"
                "Keep other workspace-manager windows closed "
                "while monitoring.\n\n"
                "Continue?",
                parent=self.root,
            )

            if not confirmed:
                return

        if not self.workspace_matches():
            return

        command = [
            sys.executable,
            "-u",
            str(SCRIPT_FOLDER / "watch_workbook.py"),
            self.source.get(),
            self.baseline.get(),
            self.approved.get(),
        ]

        if self.enable_refresh.get():
            command.append("--refresh")

        self.launch("monitor", command)

    def tool_is_open(self):
        return (
            self.tool_window is not None
            and self.tool_window.winfo_exists()
        )

    def open_tool(self, kind):
        if self.running:
            return

        if self.tool_is_open():
            self.tool_window.lift()
            return

        if not self.workspace_matches():
            return

        if not self.validate_files():
            return

        window = tk.Toplevel(self.root)

        try:
            if kind == "ai":
                AIReviewWindow(
                    window,
                    Path(self.source.get()).resolve(),
                )
            else:
                CorrectionWindow(
                    window,
                    Path(self.source.get()).resolve(),
                    Path(self.baseline.get()).resolve(),
                )

            self.tool_window = window
            window.transient(self.root)
            window.grab_set()

        except Exception as error:
            window.destroy()
            messagebox.showerror(
                "Could not open tool",
                str(error),
                parent=self.root,
            )

    def open_ai_review(self):
        self.open_tool("ai")

    def open_corrections(self):
        self.open_tool("corrections")

    def close(self):
        if self.tool_is_open():
            messagebox.showinfo(
                "Tool window open",
                "Close the tool window first.",
                parent=self.root,
            )
            return

        super().close()


def main():
    root = tk.Tk()
    FlowGuardDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()