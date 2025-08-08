import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pynput import mouse, keyboard

class AutoClickerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Autoclicker")
        self.resizable(False, False)

        # Variables
        self.clicking = False
        self.click_thread = None

        self.hours = tk.StringVar(value="0")
        self.minutes = tk.StringVar(value="0")
        self.seconds = tk.StringVar(value="1")
        self.milliseconds = tk.StringVar(value="0")

        self.mode = tk.StringVar(value="mouse")  # mouse or keyboard
        self.mouse_button = tk.StringVar(value="left")
        self.keyboard_key = tk.StringVar(value="a")
        self.hotkey = tk.StringVar(value="F6")

        self.listener = None
        self.current_keys = set()
        self.hotkey_pressed_last = False  # to avoid repeated toggling while holding keys

        self.listening_hotkey = False
        self.listening_keypress = False
        self.keypress_keys = set()
        self.hotkey_confirmed = True
        self.keypress_confirmed = True

        self.create_widgets()
        self.start_hotkey_listener()
        self.update_mode_ui()
        self.minsize(self.winfo_width(), self.winfo_height())

    def create_widgets(self):
        frm = ttk.Frame(self, padding=15)
        frm.pack()

        # Interval inputs
        ttk.Label(frm, text="Time between actions:").grid(row=0, column=0, sticky="w")
        interval_frame = ttk.Frame(frm)
        interval_frame.grid(row=1, column=0, pady=5)

        self._create_labeled_entry(interval_frame, "Hours (0-23):", self.hours, 0, 0, 3)
        self._create_labeled_entry(interval_frame, "Minutes (0-59):", self.minutes, 0, 1, 2)
        self._create_labeled_entry(interval_frame, "Seconds (0-59):", self.seconds, 0, 2, 2)
        self._create_labeled_entry(interval_frame, "Milliseconds (0-999):", self.milliseconds, 0, 3, 4)

        # Mode select
        ttk.Label(frm, text="Action Type:").grid(row=2, column=0, sticky="w")
        mode_frame = ttk.Frame(frm)
        mode_frame.grid(row=3, column=0, pady=5)
        ttk.Radiobutton(mode_frame, text="Mouse Click", variable=self.mode, value="mouse", command=self.update_mode_ui).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="Keyboard Key", variable=self.mode, value="keyboard", command=self.update_mode_ui).pack(side="left", padx=5)

        # Mouse options
        self.mouse_frame = ttk.Frame(frm)
        self.mouse_frame.grid(row=4, column=0, sticky="w")
        ttk.Label(self.mouse_frame, text="Mouse Button:").pack(side="left")
        ttk.Radiobutton(self.mouse_frame, text="Left", variable=self.mouse_button, value="left").pack(side="left", padx=5)
        ttk.Radiobutton(self.mouse_frame, text="Right", variable=self.mouse_button, value="right").pack(side="left", padx=5)

        # Keyboard key picker
        self.keyboard_frame = ttk.Frame(frm)
        self.keyboard_frame.grid(row=5, column=0, sticky="w")
        ttk.Label(self.keyboard_frame, text="Key to Press:").grid(row=0, column=0, sticky="w")
        self.keypress_entry = ttk.Entry(self.keyboard_frame, textvariable=self.keyboard_key, width=20, state="readonly", justify="center")
        self.keypress_entry.grid(row=0, column=1)
        self.keypress_entry.bind("<Button-1>", self.begin_listen_keypress)
        self.keypress_confirm_btn = ttk.Button(self.keyboard_frame, text="Confirm", command=self.confirm_keypress, state="disabled")
        self.keypress_confirm_btn.grid(row=0, column=2, padx=5)

        # Hotkey picker
        ttk.Label(frm, text="Start/Stop Hotkey:").grid(row=6, column=0, sticky="w", pady=(10,0))
        hotkey_frame = ttk.Frame(frm)
        hotkey_frame.grid(row=7, column=0, sticky="w")
        self.hotkey_entry = ttk.Entry(hotkey_frame, textvariable=self.hotkey, width=20, state="readonly", justify="center")
        self.hotkey_entry.grid(row=0, column=0)
        self.hotkey_entry.bind("<Button-1>", self.begin_listen_hotkey)
        self.confirm_hotkey_btn = ttk.Button(hotkey_frame, text="Confirm", command=self.confirm_hotkey, state="disabled")
        self.confirm_hotkey_btn.grid(row=0, column=1, padx=5)

        # Start/Stop button
        self.toggle_btn = ttk.Button(frm, text="Start", command=self.toggle_clicking)
        self.toggle_btn.grid(row=8, column=0, pady=15, ipadx=20)

        # Status label
        self.status_label = ttk.Label(frm, text="Click the hotkey box, then press any key(s) to set hotkey.")
        self.status_label.grid(row=9, column=0, sticky="w")

    def _create_labeled_entry(self, parent, text, var, row, col, width):
        label = ttk.Label(parent, text=text)
        label.grid(row=row, column=col*2, sticky="e", padx=(0,3))
        entry = ttk.Entry(parent, textvariable=var, width=width)
        entry.grid(row=row, column=col*2+1, sticky="w", padx=(0,10))
        if text.startswith("Hours"):
            self.hours_entry = entry
        elif text.startswith("Minutes"):
            self.minutes_entry = entry
        elif text.startswith("Seconds"):
            self.seconds_entry = entry
        elif text.startswith("Milliseconds"):
            self.milliseconds_entry = entry

    def update_mode_ui(self):
        if self.mode.get() == "mouse":
            self.mouse_frame.grid()
            self.keyboard_frame.grid_remove()
        else:
            self.mouse_frame.grid_remove()
            self.keyboard_frame.grid()

    # Hotkey picker methods
    def begin_listen_hotkey(self, event=None):
        if self.listening_hotkey:
            return
        self.listening_hotkey = True
        self.hotkey_confirmed = False
        self.status_label.config(text="Press desired hotkey combination for start/stop...")
        self.confirm_hotkey_btn.config(state="normal")
        self.toggle_btn.config(state="disabled")

        self.current_keys.clear()
        self.hotkey_entry.config(state="normal")
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.config(state="readonly")

        def on_press(key):
            self.current_keys.add(key)
            self.update_hotkey_entry()
            return True

        def on_release(key):
            return True

        self.temp_listener_hotkey = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.temp_listener_hotkey.start()

    def update_hotkey_entry(self):
        modifiers = []
        keys = []

        for k in self.current_keys:
            name = self.key_to_string(k)
            if name in ("ctrl", "shift", "alt", "cmd"):
                modifiers.append(name.title())
            else:
                keys.append(name.upper())

        mod_order = ["Ctrl", "Alt", "Shift", "Cmd"]
        modifiers = [m for m in mod_order if m in modifiers]

        combo = "+".join(modifiers + keys)
        if combo == "":
            combo = "..."

        self.hotkey_entry.config(state="normal")
        self.hotkey_entry.delete(0, tk.END)
        self.hotkey_entry.insert(0, combo)
        self.hotkey_entry.config(state="readonly")

        self.hotkey.set(combo.lower())

    def confirm_hotkey(self):
        if self.listening_hotkey:
            self.listening_hotkey = False
            if hasattr(self, 'temp_listener_hotkey') and self.temp_listener_hotkey.is_alive():
                self.temp_listener_hotkey.stop()

            if self.hotkey.get() in ("", "..."):
                messagebox.showwarning("Hotkey Not Set", "Please press a valid hotkey combination before confirming.")
                self.status_label.config(text="Press desired hotkey combination for start/stop...")
                self.confirm_hotkey_btn.config(state="normal")
                return

            self.hotkey_confirmed = True
            self.status_label.config(text=f"Start/Stop Hotkey set to: {self.hotkey.get().upper()}")
            self.confirm_hotkey_btn.config(state="disabled")
            self.toggle_btn.config(state="normal")

    # Keyboard key to press picker methods
    def begin_listen_keypress(self, event=None):
        if self.listening_keypress:
            return
        self.listening_keypress = True
        self.keypress_confirmed = False
        self.status_label.config(text="Press the key to repeat... Then confirm.")
        self.keypress_confirm_btn.config(state="normal")
        self.toggle_btn.config(state="disabled")

        self.keypress_keys.clear()
        self.keypress_entry.config(state="normal")
        self.keypress_entry.delete(0, tk.END)
        self.keypress_entry.config(state="readonly")

        def on_press(key):
            self.keypress_keys.add(key)
            self.update_keypress_entry()
            return True

        def on_release(key):
            return True

        self.temp_listener_keypress = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.temp_listener_keypress.start()

    def update_keypress_entry(self):
        if not self.keypress_keys:
            display = "..."
            keystr = ""
        else:
            non_mods = [k for k in self.keypress_keys if self.key_to_string(k) not in ("ctrl","shift","alt","cmd")]
            key_to_show = (non_mods or list(self.keypress_keys))[-1]
            display = self.key_to_string(key_to_show).upper()
            keystr = self.key_to_string(key_to_show).lower()

        self.keypress_entry.config(state="normal")
        self.keypress_entry.delete(0, tk.END)
        self.keypress_entry.insert(0, display)
        self.keypress_entry.config(state="readonly")

        self.keyboard_key.set(keystr)

    def confirm_keypress(self):
        if self.listening_keypress:
            self.listening_keypress = False
            if hasattr(self, 'temp_listener_keypress') and self.temp_listener_keypress.is_alive():
                self.temp_listener_keypress.stop()

            if self.keyboard_key.get() == "":
                messagebox.showwarning("Key Not Set", "Please press a valid key before confirming.")
                self.status_label.config(text="Press the key to repeat... Then confirm.")
                self.keypress_confirm_btn.config(state="normal")
                return

            self.keypress_confirmed = True
            self.status_label.config(text=f"Key to press repeatedly set to: {self.keyboard_key.get().upper()}")
            self.keypress_confirm_btn.config(state="disabled")
            self.toggle_btn.config(state="normal")

    def toggle_clicking(self):
        if not self.hotkey_confirmed:
            messagebox.showinfo("Confirm Hotkey", "Please confirm your start/stop hotkey before starting.")
            return

        if self.mode.get() == "keyboard" and not self.keypress_confirmed:
            messagebox.showinfo("Confirm Key", "Please confirm the keyboard key to press before starting.")
            return

        if self.clicking:
            self.stop_clicking()
        else:
            self.start_clicking()

    def start_clicking(self):
        interval = self.get_interval_seconds()
        if interval is None:
            return

        self.clicking = True
        self.toggle_btn.config(text="Stop")
        self.status_label.config(text="Running... Press hotkey or button to stop.")
        self.click_thread = threading.Thread(target=self.click_loop, daemon=True)
        self.click_thread.start()

    def stop_clicking(self):
        self.clicking = False
        self.toggle_btn.config(text="Start")
        self.status_label.config(text="Stopped.")

    def click_loop(self):
        mouse_controller = mouse.Controller()
        keyboard_controller = keyboard.Controller()

        while self.clicking:
            if self.mode.get() == "mouse":
                button = mouse.Button.left if self.mouse_button.get() == "left" else mouse.Button.right
                mouse_controller.click(button)
            else:
                key_str = self.keyboard_key.get()
                key_to_press = self.string_to_key(key_str)
                if key_to_press:
                    keyboard_controller.press(key_to_press)
                    keyboard_controller.release(key_to_press)
                else:
                    self.status_label.config(text="Invalid keyboard key set. Stopping.")
                    self.clicking = False
                    break
            interval = self.get_interval_seconds()
            time.sleep(interval)

    def string_to_key(self, key_str):
        special_keys = {
            "ctrl": keyboard.Key.ctrl,
            "shift": keyboard.Key.shift,
            "alt": keyboard.Key.alt,
            "cmd": keyboard.Key.cmd,
            "space": keyboard.Key.space,
            "enter": keyboard.Key.enter,
            "backspace": keyboard.Key.backspace,
            "tab": keyboard.Key.tab,
            "esc": keyboard.Key.esc,
            "up": keyboard.Key.up,
            "down": keyboard.Key.down,
            "left": keyboard.Key.left,
            "right": keyboard.Key.right,
            "delete": keyboard.Key.delete,
            "home": keyboard.Key.home,
            "end": keyboard.Key.end,
            "pageup": keyboard.Key.page_up,
            "pagedown": keyboard.Key.page_down,
            "f1": keyboard.Key.f1,
            "f2": keyboard.Key.f2,
            "f3": keyboard.Key.f3,
            "f4": keyboard.Key.f4,
            "f5": keyboard.Key.f5,
            "f6": keyboard.Key.f6,
            "f7": keyboard.Key.f7,
            "f8": keyboard.Key.f8,
            "f9": keyboard.Key.f9,
            "f10": keyboard.Key.f10,
            "f11": keyboard.Key.f11,
            "f12": keyboard.Key.f12,
        }
        if key_str in special_keys:
            return special_keys[key_str]
        elif len(key_str) == 1:
            return keyboard.KeyCode.from_char(key_str)
        else:
            return None

    def get_interval_seconds(self):
        try:
            h = int(self.hours.get())
            m = int(self.minutes.get())
            s = int(self.seconds.get())
            ms = int(self.milliseconds.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers in all time fields.")
            return None

        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59 and 0 <= ms <= 999):
            messagebox.showerror("Invalid Input", "Please enter values within allowed ranges.")
            return None

        total_seconds = h * 3600 + m * 60 + s + ms / 1000
        if total_seconds <= 0:
            total_seconds = 0.001
        return total_seconds

    def start_hotkey_listener(self):
        def on_press(key):
            self.current_keys.add(key)
            if self.is_hotkey_pressed():
                if not self.hotkey_pressed_last:
                    self.toggle_clicking()
                    self.hotkey_pressed_last = True
            return True

        def on_release(key):
            if key in self.current_keys:
                self.current_keys.remove(key)
            self.hotkey_pressed_last = False
            return True

        self.listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self.listener.start()

    def is_hotkey_pressed(self):
        combo = [part.strip().lower() for part in self.hotkey.get().split('+')]

        name_to_keys = {
            "ctrl": {keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
            "shift": {keyboard.Key.shift_l, keyboard.Key.shift_r},
            "alt": {keyboard.Key.alt_l, keyboard.Key.alt_r},
            "cmd": {keyboard.Key.cmd_l, keyboard.Key.cmd_r, keyboard.Key.cmd},
            "space": {keyboard.Key.space},
            "enter": {keyboard.Key.enter},
            "backspace": {keyboard.Key.backspace},
            "tab": {keyboard.Key.tab},
            "esc": {keyboard.Key.esc},
            "up": {keyboard.Key.up},
            "down": {keyboard.Key.down},
            "left": {keyboard.Key.left},
            "right": {keyboard.Key.right},
            "delete": {keyboard.Key.delete},
            "home": {keyboard.Key.home},
            "end": {keyboard.Key.end},
            "pageup": {keyboard.Key.page_up},
            "pagedown": {keyboard.Key.page_down},
            "f1": {keyboard.Key.f1},
            "f2": {keyboard.Key.f2},
            "f3": {keyboard.Key.f3},
            "f4": {keyboard.Key.f4},
            "f5": {keyboard.Key.f5},
            "f6": {keyboard.Key.f6},
            "f7": {keyboard.Key.f7},
            "f8": {keyboard.Key.f8},
            "f9": {keyboard.Key.f9},
            "f10": {keyboard.Key.f10},
            "f11": {keyboard.Key.f11},
            "f12": {keyboard.Key.f12},
        }

        pressed_chars = set()
        for k in self.current_keys:
            if isinstance(k, keyboard.KeyCode) and k.char:
                pressed_chars.add(k.char.lower())

        for part in combo:
            if part in name_to_keys:
                if not any(k in self.current_keys for k in name_to_keys[part]):
                    return False
            else:
                if part not in pressed_chars:
                    return False
        return True

    def key_to_string(self, key):
        if isinstance(key, keyboard.KeyCode):
            return key.char if key.char else ""
        elif isinstance(key, keyboard.Key):
            key_map = {
                keyboard.Key.ctrl_l: "ctrl",
                keyboard.Key.ctrl_r: "ctrl",
                keyboard.Key.shift_l: "shift",
                keyboard.Key.shift_r: "shift",
                keyboard.Key.alt_l: "alt",
                keyboard.Key.alt_r: "alt",
                keyboard.Key.cmd_l: "cmd",
                keyboard.Key.cmd_r: "cmd",
                keyboard.Key.space: "space",
                keyboard.Key.enter: "enter",
                keyboard.Key.backspace: "backspace",
                keyboard.Key.tab: "tab",
                keyboard.Key.esc: "esc",
                keyboard.Key.up: "up",
                keyboard.Key.down: "down",
                keyboard.Key.left: "left",
                keyboard.Key.right: "right",
                keyboard.Key.delete: "delete",
                keyboard.Key.home: "home",
                keyboard.Key.end: "end",
                keyboard.Key.page_up: "pageup",
                keyboard.Key.page_down: "pagedown",
                keyboard.Key.f1: "f1",
                keyboard.Key.f2: "f2",
                keyboard.Key.f3: "f3",
                keyboard.Key.f4: "f4",
                keyboard.Key.f5: "f5",
                keyboard.Key.f6: "f6",
                keyboard.Key.f7: "f7",
                keyboard.Key.f8: "f8",
                keyboard.Key.f9: "f9",
                keyboard.Key.f10: "f10",
                keyboard.Key.f11: "f11",
                keyboard.Key.f12: "f12",
            }
            return key_map.get(key, "")
        return ""

if __name__ == "__main__":
    app = AutoClickerApp()
    app.mainloop()
