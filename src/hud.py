import os
import threading
import tkinter as tk
from tkinter import messagebox

import psutil


class HUD:
    def __init__(
        self,
        on_send,
        on_voice,
        on_vision,
        on_stop_speaking,
        on_toggle_wake,
    ):
        self._tk_thread = threading.current_thread()
        self.on_send = on_send
        self._phase = 0
        self._mic_level = 0.0
        self._wake_enabled = False
        self.root = tk.Tk()
        self.root.title("J.A.R.V.I.S. | Desktop AI")
        self.root.geometry("960x680")
        self.root.minsize(780, 560)
        self.root.configure(bg="#07111d")

        header = tk.Frame(self.root, bg="#07111d")
        header.pack(fill="x", padx=16, pady=(14, 4))
        self.reactor = tk.Canvas(
            header,
            width=64,
            height=64,
            bg="#07111d",
            highlightthickness=0,
        )
        self.reactor.pack(side="left", padx=(0, 12))
        self.reactor.create_oval(
            7, 7, 57, 57, outline="#1c526e", width=2, tags="ring"
        )
        self.reactor.create_arc(
            7,
            7,
            57,
            57,
            start=0,
            extent=100,
            style="arc",
            outline="#65d9ff",
            width=4,
            tags="pulse",
        )
        title_box = tk.Frame(header, bg="#07111d")
        title_box.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_box,
            text="J.A.R.V.I.S.",
            fg="#65d9ff",
            bg="#07111d",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")
        self.status = tk.Label(
            title_box,
            text="ONLINE • READY",
            fg="#55e6b2",
            bg="#07111d",
            font=("Segoe UI", 10),
        )
        self.status.pack(anchor="w")
        self.metrics = tk.Label(
            title_box,
            text="CPU --%   RAM --%   DISK --%",
            fg="#93b9cc",
            bg="#07111d",
            font=("Segoe UI", 9),
        )
        self.metrics.pack(anchor="w", pady=(3, 0))

        self.log = tk.Text(
            self.root,
            bg="#0b1b2b",
            fg="#d6efff",
            insertbackground="white",
            wrap="word",
            font=("Consolas", 11),
            bd=0,
            padx=12,
            pady=12,
        )
        self.log.pack(fill="both", expand=True, padx=14, pady=10)
        self.log.configure(state="disabled")

        controls = tk.Frame(self.root, bg="#07111d")
        controls.pack(fill="x", padx=14, pady=(0, 5))
        self.entry = tk.Entry(
            controls,
            bg="#102437",
            fg="white",
            insertbackground="white",
            font=("Segoe UI", 11),
            bd=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=9)
        self.entry.bind("<Return>", lambda event: self.send())
        self._button(controls, "SEND", self.send)
        self._button(controls, "RECORD", on_voice)
        self._button(controls, "SCREEN", on_vision)
        self._button(controls, "STOP SPEAKING", on_stop_speaking)
        self._wake_button = self._button(
            controls,
            "WAKE WORD: OFF",
            lambda: on_toggle_wake(not self._wake_enabled),
        )

        mic_row = tk.Frame(self.root, bg="#07111d")
        mic_row.pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(
            mic_row,
            text="MIC LEVEL",
            fg="#93b9cc",
            bg="#07111d",
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(0, 8))
        self.mic_meter = tk.Canvas(
            mic_row,
            width=180,
            height=10,
            bg="#102437",
            highlightthickness=0,
        )
        self.mic_meter.pack(side="left")
        self._mic_bar = self.mic_meter.create_rectangle(
            0, 0, 0, 10, fill="#55e6b2", width=0
        )
        self.add(
            "JARVIS",
            "Interface ready. Type, record speech, or request screen analysis.",
        )
        self._animate()
        self._refresh_metrics()

    def _button(self, parent, label, command):
        button = tk.Button(
            parent,
            text=label,
            command=command,
            bg="#12374d",
            fg="#8ee8ff",
            activebackground="#1c526e",
            activeforeground="white",
            bd=0,
            padx=9,
            pady=8,
        )
        button.pack(side="left", padx=(8, 0))
        return button

    def add(self, who, text):
        self.log.configure(state="normal")
        self.log.insert("end", f"\n{who} > {text}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def send(self):
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self.add("YOU", text)
            self.on_send(text)

    def set_status(self, text):
        text = str(text)
        color = "#ff7585" if "ERROR" in text else "#55e6b2"
        if any(word in text for word in ("LISTENING", "WAKE", "SPEAKING")):
            color = "#ffd166"
        self.status.configure(text=text, fg=color)

    def set_mic_level(self, level):
        self._mic_level = max(0.0, min(1.0, float(level)))
        width = max(1, self.mic_meter.winfo_width())
        self.mic_meter.coords(self._mic_bar, 0, 0, width * self._mic_level, 10)

    def set_wake_state(self, enabled):
        self._wake_enabled = bool(enabled)
        self._wake_button.configure(
            text="WAKE WORD: ON" if self._wake_enabled else "WAKE WORD: OFF",
            fg="#ffd166" if self._wake_enabled else "#8ee8ff",
        )

    def confirm_action(self, description):
        if threading.current_thread() is self._tk_thread:
            return messagebox.askyesno(
                "JARVIS action approval",
                str(description),
                parent=self.root,
            )
        completed = threading.Event()
        outcome = {}

        def show_dialog():
            try:
                outcome["approved"] = messagebox.askyesno(
                    "JARVIS action approval",
                    str(description),
                    parent=self.root,
                )
            except Exception as exc:
                outcome["error"] = exc
            finally:
                completed.set()

        self.root.after(0, show_dialog)
        if not completed.wait(timeout=120):
            return False
        if "error" in outcome:
            raise RuntimeError(f"Could not show action approval dialog: {outcome['error']}")
        return outcome["approved"]

    def dispatch(self, function, *args):
        self.root.after(0, function, *args)

    def _animate(self):
        self._phase = (self._phase + 8) % 360
        self.reactor.itemconfigure("pulse", start=self._phase)
        self.root.after(45, self._animate)

    def _refresh_metrics(self):
        try:
            drive = os.environ.get("SystemDrive", "C:")
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage(drive).percent
            self.metrics.configure(
                text=f"CPU {cpu:.0f}%   RAM {ram:.0f}%   DISK {disk:.0f}%"
            )
        except Exception as exc:
            self.metrics.configure(text=f"SYSTEM MONITOR ERROR: {exc}")
        self.root.after(2000, self._refresh_metrics)

    def run(self):
        self.root.mainloop()
