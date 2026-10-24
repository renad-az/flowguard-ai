import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
CHECK_SCRIPT = Path(__file__).resolve().with_name(
    "check_workbook.py"
)


class FlowGuardApp:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.events = queue.Queue()

        root.title("FlowGuard AI")
        root.geometry("850x600")
        root.minsize(700, 500)

        self.source = tk.StringVar()
        self.baseline = tk.StringVar()
        self.status = tk.StringVar(value="Ready")

        container = ttk.Frame(root, padding=24)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)

        ttk.Label(
            container,
            text="FlowGuard AI",
            font=("Segoe UI", 22, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
        )

        ttk.Label(
            container,
            text="Local Excel validation for Power BI",
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(4, 24),
        )

        ttk.Label(
            container,
            text="Source Excel",
        ).grid(row=2, column=0, sticky="w", padx=(0, 12))

        ttk.Entry(
            container,
            textvariable=self.source,
            state="readonly",
        ).grid(row=2, column=1, sticky="ew")

        self.source_button = ttk.Button(
            container,
            text="Browse",
            command=self.choose_source,
        )
        self.source_button.grid(row=2, column=2, padx=(10, 0))

        ttk.Label(
            container,
            text="Reviewed baseline",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=12,
        )

        ttk.Entry(
            container,
            textvariable=self.baseline,
            state="readonly",
        ).grid(row=3, column=1, sticky="ew")

        self.baseline_button = ttk.Button(
            container,
            text="Browse",
            command=self.choose_baseline,
        )
        self.baseline_button.grid(
            row=3,
            column=2,
            padx=(10, 0),
        )

        self.check_button = ttk.Button(
            container,
            text="Check Data",
            command=self.start_check,
        )
        self.check_button.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 12),
        )

        ttk.Label(
            container,
            textvariable=self.status,
        ).grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
        )

        self.log = ScrolledText(
            container,
            height=16,
            font=("Consolas", 10),
            state="disabled",
        )
        self.log.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(12, 0),
        )
        container.rowconfigure(6, weight=1)

        ttk.Label(
            container,
            text=(
                "Checks only: no file approval, AI request, "
                "or Power BI refresh."
            ),
            wraplength=750,
        ).grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.process_events)

    def choose_source(self):
        path = filedialog.askopenfilename(
            title="Choose source Excel",
            initialdir=PROJECT_FOLDER / "data" / "incoming",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if path:
            self.source.set(path)

    def choose_baseline(self):
        path = filedialog.askopenfilename(
            title="Choose reviewed baseline",
            initialdir=PROJECT_FOLDER / "reports" / "baselines",
            filetypes=[("JSON file", "*.json")],
        )
        if path:
            self.baseline.set(path)

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start_check(self):
        if self.running:
            return

        source = self.source.get()
        baseline = self.baseline.get()

        if not source or not baseline:
            messagebox.showwarning(
                "Select files",
                "Choose the source Excel and reviewed baseline.",
            )
            return

        if not Path(source).is_file() or not Path(baseline).is_file():
            messagebox.showerror(
                "File not found",
                "One of the selected files no longer exists.",
            )
            return

        self.running = True
        self.status.set("Checking data…")

        for button in (
            self.check_button,
            self.source_button,
            self.baseline_button,
        ):
            button.configure(state="disabled")

        self.write_log("\n--- Check started ---\n")

        threading.Thread(
            target=self.run_check,
            args=(source, baseline),
            daemon=True,
        ).start()

    def run_check(self, source, baseline):
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(CHECK_SCRIPT),
                    source,
                    baseline,
                ],
                cwd=PROJECT_FOLDER,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
                check=False,
            )

            output = result.stdout

            if result.stderr:
                output += "\n" + result.stderr

            self.events.put(("output", output))
            self.events.put(("done", result.returncode))

        except Exception as error:
            self.events.put(
                ("output", f"Check failed: {error}\n")
            )
            self.events.put(("done", 1))

    def process_events(self):
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "output":
                self.write_log(value)

            elif event == "done":
                self.running = False

                statuses = {
                    0: "PASS — current checks passed",
                    2: "REVIEW — warnings need attention",
                }

                self.status.set(
                    statuses.get(
                        value,
                        "BLOCKED / FAILED — see details",
                    )
                )

                for button in (
                    self.check_button,
                    self.source_button,
                    self.baseline_button,
                ):
                    button.configure(state="normal")

        self.root.after(100, self.process_events)

    def close(self):
        if self.running:
            messagebox.showinfo(
                "Check running",
                "Wait for the current check to finish before closing.",
            )
            return

        self.root.destroy()


def main():
    root = tk.Tk()
    FlowGuardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()