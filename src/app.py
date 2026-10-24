import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


PROJECT_FOLDER = Path(__file__).resolve().parent.parent
SCRIPT_FOLDER = Path(__file__).resolve().parent
STOP_FILE = PROJECT_FOLDER / "reports" / "monitor.stop"


class FlowGuardApp:
    def __init__(self, root):
        self.root = root
        self.events = queue.Queue()
        self.running = False
        self.mode = None
        self.owns_monitor = False

        self.source = tk.StringVar()
        self.baseline = tk.StringVar()
        self.approved = tk.StringVar()
        self.enable_refresh = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready")

        root.title("FlowGuard AI")
        root.geometry("950x720")
        root.minsize(780, 600)

        frame = ttk.Frame(root, padding=24)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            text="FlowGuard AI",
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")

        ttk.Label(
            frame,
            text="Local Excel validation and guarded Power BI refresh",
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(4, 20),
        )

        self.file_buttons = []

        self.add_file_row(
            frame, 2, "Source Excel",
            self.source, self.choose_source,
        )
        self.add_file_row(
            frame, 3, "Reviewed baseline",
            self.baseline, self.choose_baseline,
        )
        self.add_file_row(
            frame, 4, "Approved Excel",
            self.approved, self.choose_approved,
        )

        self.refresh_checkbox = ttk.Checkbutton(
            frame,
            text="Enable experimental Power BI refresh",
            variable=self.enable_refresh,
        )
        self.refresh_checkbox.grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            pady=12,
        )

        actions = ttk.Frame(frame)
        actions.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 12),
        )

        self.check_button = ttk.Button(
            actions,
            text="Check Data",
            command=self.start_check,
        )
        self.check_button.pack(side="left", padx=(0, 8))

        self.start_button = ttk.Button(
            actions,
            text="Start Monitoring",
            command=self.start_monitor,
        )
        self.start_button.pack(side="left", padx=(0, 8))

        self.stop_button = ttk.Button(
            actions,
            text="Stop",
            command=self.request_stop,
            state="disabled",
        )
        self.stop_button.pack(side="left")

        ttk.Label(
            frame,
            textvariable=self.status,
        ).grid(row=7, column=0, columnspan=3, sticky="w")

        self.log = ScrolledText(
            frame,
            height=20,
            font=("Consolas", 10),
            state="disabled",
        )
        self.log.grid(
            row=8,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(12, 0),
        )
        frame.rowconfigure(8, weight=1)

        ttk.Label(
            frame,
            text=(
                "Stop waits for the current cycle. "
                "Refresh evidence does not verify every report table. "
                "AI review and automatic corrections are not connected."
            ),
            wraplength=850,
        ).grid(
            row=9,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 0),
        )

        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.process_events)

    def add_file_row(self, frame, row, label, variable, command):
        ttk.Label(frame, text=label).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 12),
            pady=6,
        )

        ttk.Entry(
            frame,
            textvariable=variable,
            state="readonly",
        ).grid(row=row, column=1, sticky="ew")

        button = ttk.Button(
            frame,
            text="Browse",
            command=command,
        )
        button.grid(row=row, column=2, padx=(10, 0))
        self.file_buttons.append(button)

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

    def choose_approved(self):
        path = filedialog.asksaveasfilename(
            title="Choose approved Excel destination",
            initialdir=PROJECT_FOLDER / "data" / "approved",
            initialfile="FlowBI_Project_Management.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )
        if path:
            self.approved.set(path)

    def validate_files(self, monitoring=False):
        for label, value in (
            ("Source Excel", self.source.get()),
            ("Reviewed baseline", self.baseline.get()),
        ):
            if not value or not Path(value).is_file():
                messagebox.showerror(
                    "Select files",
                    f"Choose an existing {label} file.",
                )
                return False

        if monitoring:
            if not self.approved.get():
                messagebox.showerror(
                    "Select destination",
                    "Choose the approved Excel destination.",
                )
                return False

            source = Path(self.source.get()).resolve()
            baseline = Path(self.baseline.get()).resolve()
            approved = Path(self.approved.get()).resolve()

            if approved in (source, baseline):
                messagebox.showerror(
                    "Invalid destination",
                    "Approved must be separate from source and baseline.",
                )
                return False

        return True

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_busy(self, busy):
        self.running = busy
        state = "disabled" if busy else "normal"

        for button in (
            self.check_button,
            self.start_button,
            *self.file_buttons,
        ):
            button.configure(state=state)

        self.refresh_checkbox.configure(state=state)

        if not busy:
            self.stop_button.configure(state="disabled")

    def launch(self, mode, command):
        self.mode = mode
        self.owns_monitor = False
        self.set_busy(True)
        self.status.set(
            "Starting monitor…" if mode == "monitor" else "Checking…"
        )
        self.write_log(f"\n--- {mode.upper()} STARTED ---\n")

        threading.Thread(
            target=self.run_process,
            args=(command,),
            daemon=True,
        ).start()

    def run_process(self, command):
        try:
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "utf-8"
            environment["PYTHONUNBUFFERED"] = "1"

            with subprocess.Popen(
                command,
                cwd=PROJECT_FOLDER,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
            ) as process:
                for line in process.stdout:
                    self.events.put(("output", line))

                self.events.put(("done", process.wait()))

        except Exception as error:
            self.events.put(("output", f"Process failed: {error}\n"))
            self.events.put(("done", 1))

    def start_check(self):
        if self.running or not self.validate_files():
            return

        self.launch(
            "check",
            [
                sys.executable,
                "-u",
                str(SCRIPT_FOLDER / "check_workbook.py"),
                self.source.get(),
                self.baseline.get(),
            ],
        )

    def start_monitor(self):
        if self.running or not self.validate_files(monitoring=True):
            return

        if self.enable_refresh.get():
            confirmed = messagebox.askokcancel(
                "Experimental refresh",
                "Open the FlowBI report, maximize Power BI, "
                "select Home, and keep Refresh Check Time visible.\n\n"
                "The current trigger depends on your tested layout. "
                "Continue?",
            )
            if not confirmed:
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

    def request_stop(self):
        if not self.running or not self.owns_monitor:
            return

        try:
            STOP_FILE.parent.mkdir(parents=True, exist_ok=True)
            STOP_FILE.touch()

            self.status.set("Stopping after the current cycle…")
            self.stop_button.configure(state="disabled")

        except OSError as error:
            messagebox.showerror("Stop request failed", str(error))

    def process_events(self):
        while True:
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break

            if event == "output":
                self.write_log(value)

                if (
                    self.mode == "monitor"
                    and value.startswith("MONITORING:")
                ):
                    self.owns_monitor = True
                    self.status.set("Monitoring")
                    self.stop_button.configure(state="normal")

            elif event == "done":
                mode = self.mode
                self.owns_monitor = False
                self.set_busy(False)

                if mode == "check":
                    self.status.set({
                        0: "PASS — current checks passed",
                        2: "REVIEW — see details",
                    }.get(value, "BLOCKED / FAILED — see details"))
                else:
                    self.status.set(
                        "Stopped"
                        if value == 0
                        else "Stopped — review required; see log"
                    )

                self.mode = None

        self.root.after(100, self.process_events)

    def close(self):
        if self.running:
            if self.mode == "monitor" and self.owns_monitor:
                self.request_stop()
                messagebox.showinfo(
                    "Stopping safely",
                    "Stop requested. Wait for Stopped, "
                    "then close the window.",
                )
            else:
                messagebox.showinfo(
                    "Please wait",
                    "Wait for the current operation to finish.",
                )
            return

        self.root.destroy()


def main():
    root = tk.Tk()
    FlowGuardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()