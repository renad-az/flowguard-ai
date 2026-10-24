import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from app import FlowGuardApp
from ai_review_window import AIReviewWindow


class FlowGuardDesktop(FlowGuardApp):
    def __init__(self, root):
        super().__init__(root)

        self.review_window = None

        self.ai_button = ttk.Button(
            self.start_button.master,
            text="AI Review",
            command=self.open_ai_review,
        )

        self.ai_button.pack(
            side="left",
            padx=(12, 0),
        )

    def set_busy(self, busy):
        super().set_busy(busy)

        if hasattr(self, "ai_button"):
            self.ai_button.configure(
                state="disabled" if busy else "normal"
            )

    def open_ai_review(self):
        if self.running:
            return

        source = Path(self.source.get())

        if not self.source.get() or not source.is_file():
            messagebox.showwarning(
                "Choose source",
                "Choose an existing Source Excel file first.",
            )
            return

        if (
            self.review_window is not None
            and self.review_window.winfo_exists()
        ):
            self.review_window.lift()
            return

        window = tk.Toplevel(self.root)

        try:
            AIReviewWindow(window, source.resolve())

            self.review_window = window
            window.transient(self.root)

            # يمنع بدء المراقبة من الواجهة أثناء المراجعة
            window.grab_set()

        except Exception as error:
            window.destroy()

            messagebox.showerror(
                "Could not open AI review",
                str(error),
            )

    def close(self):
        if (
            self.review_window is not None
            and self.review_window.winfo_exists()
        ):
            messagebox.showinfo(
                "AI review open",
                "Close the AI review window first.",
            )
            return

        super().close()


def main():
    root = tk.Tk()
    FlowGuardDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
    