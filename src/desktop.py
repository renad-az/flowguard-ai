import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app import FlowGuardApp
from ai_review_window import AIReviewWindow
from correction_window import CorrectionWindow
from settings_store import load_settings, save_settings


class FlowGuardDesktop(FlowGuardApp):
    def __init__(self, root):
        super().__init__(root)

        self.tool_window = None

        self.ai_button = ttk.Button(
            self.start_button.master,
            text="AI Review",
            command=self.open_ai_review,
        )
        self.ai_button.pack(side="left", padx=(12, 0))

        self.correction_button = ttk.Button(
            self.start_button.master,
            text="Corrections",
            command=self.open_corrections,
        )
        self.correction_button.pack(side="left", padx=(8, 0))

        self.save_button = ttk.Button(
            self.start_button.master,
            text="Save Setup",
            command=self.save_setup,
        )
        self.save_button.pack(side="left", padx=(8, 0))

        self.restore_setup()

    def set_busy(self, busy):
        super().set_busy(busy)

        for name in (
            "ai_button",
            "correction_button",
            "save_button",
        ):
            if hasattr(self, name):
                getattr(self, name).configure(
                    state="disabled" if busy else "normal"
                )

    def restore_setup(self):
        try:
            settings = load_settings()

            if settings is None:
                self.status.set("Choose files to set up your workspace")
                return

            self.source.set(settings["source"])
            self.baseline.set(settings["baseline"])
            self.approved.set(settings["approved"])
            self.enable_refresh.set(settings["refresh"])

            missing = [
                label
                for label, path in (
                    ("source", settings["source"]),
                    ("baseline", settings["baseline"]),
                )
                if not Path(path).is_file()
            ]

            if missing:
                self.status.set("Saved setup needs updated file paths")
                self.write_log(
                    "Saved setup loaded, but these files were not found: "
                    + ", ".join(missing)
                    + "\n"
                )
            else:
                self.status.set("Saved setup loaded — ready")
                self.write_log(
                    "Local setup restored. Monitoring has not started.\n"
                )

        except (OSError, ValueError, TypeError) as error:
            self.status.set("Could not load setup — choose files again")
            self.write_log(f"Settings could not be loaded: {error}\n")

    def persist_setup(self):
        save_settings(
            self.source.get(),
            self.baseline.get(),
            self.approved.get(),
            self.enable_refresh.get(),
        )

    def save_setup(self):
        if self.running:
            return

        if not self.validate_files(monitoring=True):
            return

        try:
            self.persist_setup()
            self.status.set("Setup saved locally")
            self.write_log(
                "Setup saved locally. No workbook data stored "
                "in settings. Monitoring has not started.\n"
            )

        except (OSError, ValueError) as error:
            messagebox.showerror("Could not save setup", str(error))

    def start_monitor(self):
        if self.running:
            return

        if not self.validate_files(monitoring=True):
            return

        try:
            self.persist_setup()

        except (OSError, ValueError) as error:
            messagebox.showerror("Could not save setup", str(error))
            return

        super().start_monitor()

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

        source_text = self.source.get()

        if not source_text or not Path(source_text).is_file():
            messagebox.showwarning(
                "Choose source",
                "Choose an existing Source Excel file.",
            )
            return

        if kind == "corrections":
            baseline_text = self.baseline.get()

            if (
                not baseline_text
                or not Path(baseline_text).is_file()
            ):
                messagebox.showwarning(
                    "Choose baseline",
                    "Choose an existing reviewed baseline.",
                )
                return

        window = tk.Toplevel(self.root)

        try:
            if kind == "ai":
                AIReviewWindow(
                    window,
                    Path(source_text).resolve(),
                )
            else:
                CorrectionWindow(
                    window,
                    Path(source_text).resolve(),
                    Path(self.baseline.get()).resolve(),
                )

            self.tool_window = window
            window.transient(self.root)
            window.grab_set()

        except Exception as error:
            window.destroy()
            messagebox.showerror("Could not open tool", str(error))

    def open_ai_review(self):
        self.open_tool("ai")

    def open_corrections(self):
        self.open_tool("corrections")

    def close(self):
        if self.tool_is_open():
            messagebox.showinfo(
                "Tool window open",
                "Close the tool window first.",
            )
            return

        super().close()


def main():
    root = tk.Tk()
    FlowGuardDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()