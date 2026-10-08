"""Small desktop interface for Raman spectrum analysis."""
from pathlib import Path
from datetime import datetime
import queue
import threading
import math
import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

import raman_batch as core

APP_VERSION = "1.2"


def set_windows_app_id():
    """Give Windows a stable identity for the taskbar icon."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "RamanAnalyzer.Desktop.1.2"
            )
        except (AttributeError, OSError):
            pass


def application_dir():
    """Return the folder containing the packaged app or source files."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resource_dir():
    """Return the folder containing resources bundled by PyInstaller."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def default_input_dir():
    """Prefer the bundled demonstration spectra when they are available."""
    example_dir = application_dir() / "examples" / "synthetic_data"
    return example_dir if example_dir.is_dir() else core.DEFAULT_INPUT_DIR


def default_save_dir():
    """Use the desktop when present, otherwise the user's home folder."""
    desktop = Path.home() / "Desktop"
    return desktop if desktop.is_dir() else Path.home()


def open_result(path):
    """Open the completed workbook, preferring Excel on macOS."""
    path = str(Path(path).resolve())
    if sys.platform == "darwin":
        result = subprocess.run(
            ["open", "-a", "Microsoft Excel", path],
            capture_output=True, text=True,
        )
        if result.returncode:
            subprocess.run(["open", path], check=True, capture_output=True)
    elif sys.platform == "win32":
        os.startfile(path)
    else:
        subprocess.run(["xdg-open", path], check=True, capture_output=True)


def parse_axis_limits(lower, upper):
    try:
        lower, upper = float(lower), float(upper)
    except (ValueError, TypeError):
        raise ValueError("X-axis limits must be numbers.") from None
    if not (math.isfinite(lower) and math.isfinite(upper)) or lower >= upper:
        raise ValueError("Enter finite X-axis limits with minimum less than maximum.")
    return lower, upper


def run_analysis(input_dir, save_dir, subtract_baseline, emit, x_min=1000, x_max=3000):
    """Run without touching GUI widgets; report events through emit."""
    x_min, x_max = parse_axis_limits(x_min, x_max)
    files = sorted(
        (p for p in input_dir.iterdir()
         if p.is_file() and p.suffix.lower() == ".txt"),
        key=lambda p: p.name,
    )
    if not files:
        raise ValueError("No TXT files found directly inside the selected folder.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    excel_path = save_dir / f"Raman_Analysis_{timestamp}.xlsx"
    emit("log", f"Found {len(files)} files.\nBaseline subtraction: {subtract_baseline}\n")
    model, params = core.build_model()
    records, curves = [], {}
    for index, file_path in enumerate(files, start=1):
        emit("log", f"Analyzing: {file_path.name}\n")
        try:
            record = core.analyze_one_file(
                file_path, model, params, curves,
                core.FIT_MIN, core.FIT_MAX, core.BASELINE_LAM, core.BASELINE_P,
                subtract_baseline=subtract_baseline,
            )
            records.append(record)
            emit("log", f"Success: {file_path.name}\n")
        except Exception as error:
            records.append({"file": file_path.name, "status": "failed",
                            "baseline_subtracted": "Yes" if subtract_baseline else "No",
                            "error": str(error)})
            emit("log", f"Failed: {file_path.name}: {error}\n")
        emit("progress", (index, len(files)))
    emit("log", "Writing Excel workbook...\n")
    core.export_workbook(records, curves, files, excel_path, x_min, x_max)
    success = sum(r["status"] == "success" for r in records)
    return excel_path, success, len(records) - success


class RamanApp:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.events = queue.Queue()
        root.title(f"Raman Analyzer {APP_VERSION}")
        self.app_icon = None
        png_icon_path = resource_dir() / "assets" / "raman-analyzer-icon.png"
        if png_icon_path.is_file():
            try:
                self.app_icon = tk.PhotoImage(file=str(png_icon_path))
                root.iconphoto(True, self.app_icon)
            except tk.TclError:
                pass
        root.geometry("800x580")
        root.minsize(700, 500)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.input_path = tk.StringVar(value=str(default_input_dir()))
        self.save_path = tk.StringVar(value=str(default_save_dir()))
        self.subtract = tk.BooleanVar(value=True)
        self.x_min = tk.StringVar(value="1000")
        self.x_max = tk.StringVar(value="3000")
        self.status = tk.StringVar(value=f"Ready — version {APP_VERSION}")
        panel = ttk.Frame(root, padding=18)
        panel.pack(fill="both", expand=True)
        panel.columnconfigure(1, weight=1)
        panel.rowconfigure(7, weight=1)
        self.controls = []
        for row, label, variable in (
            (0, "Data folder", self.input_path),
            (1, "Save folder", self.save_path),
        ):
            ttk.Label(panel, text=label).grid(row=row, column=0, sticky="w", pady=6)
            entry = ttk.Entry(panel, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", padx=10)
            button = ttk.Button(panel, text="Browse...",
                                command=lambda v=variable: self.browse(v))
            button.grid(row=row, column=2)
            self.controls.extend([entry, button])
        checkbox = ttk.Checkbutton(panel, text="Subtract baseline (ALS)", variable=self.subtract)
        checkbox.grid(row=2, column=0, sticky="w", pady=(12, 4))
        self.controls.append(checkbox)
        limits = ttk.Frame(panel)
        limits.grid(row=2, column=1, columnspan=2, sticky="e")
        for label, variable in (("X min", self.x_min), ("X max", self.x_max)):
            ttk.Label(limits, text=label).pack(side="left", padx=(10, 4))
            entry = ttk.Entry(limits, textvariable=variable, width=9)
            entry.pack(side="left")
            self.controls.append(entry)
        ttk.Label(panel, text="Unchecked: fit raw intensity with a constant background.\n"
                  "X min / X max change chart display only (cm^-1). Fit range stays 1000-3000.\n"
                  "Peaks: D, G, 2D | TXT: one header, two tab-separated columns.",
                  wraplength=730).grid(row=3, column=0, columnspan=3, sticky="w", pady=6)
        button = ttk.Button(panel, text="Run analysis", command=self.start)
        button.grid(row=4, column=0, sticky="w", pady=10)
        self.controls.append(button)
        ttk.Label(panel, textvariable=self.status).grid(row=4, column=1, columnspan=2, sticky="w")
        self.progress = ttk.Progressbar(panel, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=6)
        ttk.Label(panel, text="Results and messages").grid(row=6, column=0, columnspan=3, sticky="w")
        self.log = ScrolledText(panel, height=15, wrap="word", state="disabled")
        self.log.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(6, 0))
        root.after(100, self.poll)

    def browse(self, variable):
        folder = filedialog.askdirectory(parent=self.root, title="Select folder", mustexist=True)
        if folder:
            variable.set(folder)

    def append(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self):
        if self.running:
            return
        if not self.input_path.get().strip() or not self.save_path.get().strip():
            messagebox.showerror("Missing folder", "Select both folders.")
            return
        input_dir = Path(self.input_path.get()).expanduser()
        save_dir = Path(self.save_path.get()).expanduser()
        if not input_dir.is_dir() or not save_dir.is_dir():
            messagebox.showerror("Invalid folder", "Both selected folders must exist.")
            return
        try:
            x_min, x_max = parse_axis_limits(self.x_min.get(), self.x_max.get())
        except ValueError as error:
            messagebox.showerror("Invalid axis limits", str(error))
            return
        self.running = True
        for control in self.controls:
            control.configure(state="disabled")
        self.progress["value"] = 0
        self.status.set("Running...")
        self.append("\n--- New analysis ---\n")
        subtract = self.subtract.get()
        threading.Thread(target=self.worker, args=(input_dir, save_dir, subtract, x_min, x_max), daemon=False).start()

    def worker(self, input_dir, save_dir, subtract, x_min, x_max):
        try:
            result = run_analysis(input_dir, save_dir, subtract,
                                  lambda kind, value: self.events.put((kind, value)), x_min, x_max)
            self.events.put(("done", result))
        except Exception as error:
            self.events.put(("error", str(error)))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self.append(value)
                elif kind == "progress":
                    count, total = value
                    self.progress.configure(maximum=total, value=count)
                    self.status.set(f"Processed {count}/{total}")
                else:
                    self.running = False
                    for control in self.controls:
                        control.configure(state="normal")
                    if kind == "done":
                        path, success, failed = value
                        self.status.set(f"Finished: {success} succeeded, {failed} failed")
                        self.append(f"\n{self.status.get()}\nExcel: {path}\n")
                        try:
                            open_result(path)
                        except Exception as error:
                            self.append(f"Workbook saved, but automatic opening failed: {error}\n")
                    else:
                        self.status.set("Failed")
                        self.append(f"Error: {value}\n")
                        messagebox.showerror("Analysis failed", value)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        if self.running:
            messagebox.showinfo("Analysis running", "Please wait for the current analysis to finish.")
        else:
            self.root.destroy()


if __name__ == "__main__":
    set_windows_app_id()
    root = tk.Tk()
    RamanApp(root)
    root.mainloop()
