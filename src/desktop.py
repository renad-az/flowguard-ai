import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app import FlowGuardApp
from ai_review_window import AIReviewWindow
from correction_window import CorrectionWindow


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

    def set_busy(self, busy):
        super().set_busy(busy)

        for name in ("ai_button", "correction_button"):
            if hasattr(self, name):
                getattr(self, name).configure(
                    state="disabled" if busy else "normal"
                )

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