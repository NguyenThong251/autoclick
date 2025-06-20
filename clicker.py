import pyautogui
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time
import random
import keyboard
import threading
import json
import os
from datetime import datetime

# Cấu hình PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

class GameMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Maker - Multi Action")
        self.root.geometry("900x750")
        self.root.configure(bg="#f0f0f0")
        self.is_running = False
        self.is_selecting = False
        self.is_recording = False
        self.preview_window = None
        self.thread = None
        self.key_actions = {}  # {key: [{name: str, coords: [(x, y, delay, click_type), ...]}, ...]}
        self.current_key = tk.StringVar(value="1")
        self.current_action_name = tk.StringVar(value="Action 1")
        self.last_click_time = None
        self.current_active_key = None  # Phím đang lặp hành động

        # Biến lưu trữ
        self.interval_var = tk.DoubleVar(value=1.0)
        self.random_mode_var = tk.BooleanVar(value=False)
        self.click_count_var = tk.IntVar(value=0)
        self.stop_key_var = tk.StringVar(value="q")
        self.new_x_var = tk.IntVar(value=0)
        self.new_y_var = tk.IntVar(value=0)
        self.new_delay_var = tk.DoubleVar(value=0.1)
        self.click_type_var = tk.StringVar(value="left")
        self.new_key_var = tk.StringVar(value="1")
        self.new_action_name_var = tk.StringVar(value="Action 1")

        # Style cho giao diện
        style = ttk.Style()
        style.configure("TButton", padding=6, font=("Arial", 10))
        style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        style.configure("TEntry", font=("Arial", 10))
        style.configure("TCheckbutton", background="#f0f0f0", font=("Arial", 10))

        # Container chính
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Tiêu đề
        ttk.Label(main_frame, text="Game Maker - Multi Action", font=("Arial", 16, "bold"), background="#f0f0f0").pack(pady=10)

        # Frame cấu hình chung
        config_frame = ttk.LabelFrame(main_frame, text="Cấu hình chung", padding="10")
        config_frame.pack(fill="x", pady=5)

        ttk.Label(config_frame, text="Khoảng thời gian giữa các chu kỳ (giây):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(config_frame, textvariable=self.interval_var).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(config_frame, text="Số chu kỳ click (0 = vô hạn):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(config_frame, textvariable=self.click_count_var).grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Checkbutton(config_frame, text="Click ngẫu nhiên trên màn hình", variable=self.random_mode_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(config_frame, text="Phím dừng chương trình:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(config_frame, textvariable=self.stop_key_var, width=5).grid(row=3, column=1, sticky="w", pady=2)

        # Frame quản lý phím và hành động
        key_action_frame = ttk.LabelFrame(main_frame, text="Quản lý phím và hành động", padding="10")
        key_action_frame.pack(fill="x", pady=5)

        ttk.Label(key_action_frame, text="Phím:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(key_action_frame, textvariable=self.new_key_var, width=5).grid(row=0, column=1, sticky="w", pady=2)
        ttk.Button(key_action_frame, text="Thêm phím", command=self.add_key).grid(row=0, column=2, padx=5, pady=2)
        ttk.Button(key_action_frame, text="Xóa phím", command=self.delete_key).grid(row=0, column=3, padx=5, pady=2)

        ttk.Label(key_action_frame, text="Chọn phím:").grid(row=1, column=0, sticky="w", pady=2)
        self.key_menu = ttk.OptionMenu(key_action_frame, self.current_key, "1", command=self.update_action_menu)
        self.key_menu.grid(row=1, column=1, columnspan=2, sticky="w", pady=2)

        ttk.Label(key_action_frame, text="Tên hành động:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(key_action_frame, textvariable=self.new_action_name_var).grid(row=2, column=1, sticky="ew", pady=2)
        ttk.Button(key_action_frame, text="Thêm hành động", command=self.add_action).grid(row=2, column=2, padx=5, pady=2)
        ttk.Button(key_action_frame, text="Xóa hành động", command=self.delete_action).grid(row=2, column=3, padx=5, pady=2)

        ttk.Label(key_action_frame, text="Chọn hành động:").grid(row=3, column=0, sticky="w", pady=2)
        self.action_menu = ttk.OptionMenu(key_action_frame, self.current_action_name, "Action 1", command=self.update_coord_listbox)
        self.action_menu.grid(row=3, column=1, columnspan=2, sticky="w", pady=2)

        # Frame quản lý tọa độ
        coord_frame = ttk.LabelFrame(main_frame, text="Quản lý tọa độ", padding="10")
        coord_frame.pack(fill="both", expand=True, pady=5)

        self.coord_listbox = tk.Listbox(coord_frame, height=10, font=("Arial", 10))
        self.coord_listbox.pack(fill="both", expand=True, pady=10)
        self.coord_listbox.bind("<Delete>", self.delete_coord)

        # Frame thêm tọa độ
        new_coord_frame = ttk.Frame(coord_frame)
        new_coord_frame.pack(fill="x", pady=5)

        ttk.Label(new_coord_frame, text="X:").grid(row=0, column=0, padx=10)
        ttk.Entry(new_coord_frame, textvariable=self.new_x_var, width=10).grid(row=0, column=1)
        ttk.Label(new_coord_frame, text="Y:").grid(row=0, column=2, padx=10)
        ttk.Entry(new_coord_frame, textvariable=self.new_y_var, width=10).grid(row=0, column=3)
        ttk.Label(new_coord_frame, text="Delay (giây):").grid(row=0, column=4, padx=10)
        ttk.Entry(new_coord_frame, textvariable=self.new_delay_var, width=10).grid(row=0, column=5)

        ttk.Label(new_coord_frame, text="Loại click:").grid(row=1, column=0, padx=10, pady=5)
        ttk.OptionMenu(new_coord_frame, self.click_type_var, "left", "left", "right", "middle").grid(row=1, column=1, columnspan=2, pady=5)
        ttk.Button(new_coord_frame, text="Thêm tọa độ", command=self.add_coordinate).grid(row=1, column=3, padx=10, pady=5)
        ttk.Button(new_coord_frame, text="Chọn bằng chuột", command=self.start_mouse_selection).grid(row=1, column=4, padx=10, pady=5)
        ttk.Button(new_coord_frame, text="Ghi hành động", command=self.start_recording).grid(row=1, column=5, padx=10, pady=5)

        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=10)

        ttk.Button(control_frame, text="Xem trước vị trí", command=self.preview_coordinates).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Bắt đầu", command=self.start_clicking).pack(side="left", padx=5)
        ttk.Button(control_frame, text="Dừng", command=self.stop_clicking).pack(side="left", padx=5)

        # Frame lưu/tải cấu hình
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill="x", pady=5)

        ttk.Button(file_frame, text="Lưu cấu hình", command=self.save_config).pack(side="left", padx=5)
        ttk.Button(file_frame, text="Tải cấu hình", command=self.load_config).pack(side="left", padx=5)

        # Frame trạng thái
        status_frame = ttk.LabelFrame(main_frame, text="Trạng thái", padding="10")
        status_frame.pack(fill="x", pady=5)

        self.status_label = ttk.Label(status_frame, text="Trạng thái: Đang dừng", foreground="red")
        self.status_label.pack(pady=2)
        self.mouse_pos_label = ttk.Label(status_frame, text="Tọa độ chuột: (0, 0)")
        self.mouse_pos_label.pack(pady=2)

        self.update_mouse_position()
        self.update_key_menu()

    def update_mouse_position(self):
        if not self.is_running and not self.is_selecting and not self.is_recording:
            x, y = pyautogui.position()
            self.mouse_pos_label.config(text=f"Tọa độ chuột: ({x}, {y})")
            self.new_x_var.set(x)
            self.new_y_var.set(y)
        self.root.after(100, self.update_mouse_position)

    def add_key(self):
        key = self.new_key_var.get().strip()
        if not key:
            messagebox.showerror("Lỗi", "Phím không được để trống!")
            return
        if len(key) != 1:
            messagebox.showerror("Lỗi", "Phím phải là một ký tự!")
            return
        if key in self.key_actions:
            messagebox.showwarning("Cảnh báo", f"Phím '{key}' đã tồn tại!")
            return
        self.key_actions[key] = []
        self.update_key_menu()
        self.current_key.set(key)
        self.update_action_menu()
        self.new_key_var.set(str(int(key) + 1 if key.isdigit() else "1"))
        messagebox.showinfo("Thành công", f"Đã thêm phím '{key}'!")

    def delete_key(self):
        key = self.current_key.get()
        if key in self.key_actions:
            del self.key_actions[key]
            self.update_key_menu()
            self.current_key.set(list(self.key_actions.keys())[0] if self.key_actions else "1")
            self.update_action_menu()
            messagebox.showinfo("Thành công", f"Đã xóa phím '{key}'!")

    def update_key_menu(self):
        menu = self.key_menu["menu"]
        menu.delete(0, "end")
        for key in sorted(self.key_actions.keys()):
            menu.add_command(label=key, command=lambda k=key: self.current_key.set(k))
        if not self.key_actions:
            menu.add_command(label="1", command=lambda: self.current_key.set("1"))

    def add_action(self):
        name = self.new_action_name_var.get().strip()
        if not name:
            messagebox.showerror("Lỗi", "Tên hành động không được để trống!")
            return
        key = self.current_key.get()
        if key not in self.key_actions:
            self.key_actions[key] = []
        if any(action["name"] == name for action in self.key_actions[key]):
            messagebox.showwarning("Cảnh báo", f"Hành động '{name}' đã tồn tại trong phím {key}!")
            return
        self.key_actions[key].append({"name": name, "coords": []})
        self.update_action_menu()
        self.current_action_name.set(name)
        self.update_coord_listbox()
        self.new_action_name_var.set(f"Action {len(self.key_actions[key]) + 1}")
        messagebox.showinfo("Thành công", f"Đã thêm hành động '{name}' cho phím '{key}'!")

    def delete_action(self):
        key = self.current_key.get()
        name = self.current_action_name.get()
        if key in self.key_actions:
            self.key_actions[key] = [action for action in self.key_actions[key] if action["name"] != name]
            self.update_action_menu()
            self.current_action_name.set(self.key_actions[key][0]["name"] if self.key_actions[key] else "Action 1")
            self.update_coord_listbox()
            messagebox.showinfo("Thành công", f"Đã xóa hành động '{name}' của phím '{key}'!")

    def update_action_menu(self, *args):
        menu = self.action_menu["menu"]
        menu.delete(0, "end")
        key = self.current_key.get()
        if key in self.key_actions:
            for action in sorted(self.key_actions[key], key=lambda x: x["name"]):
                menu.add_command(label=action["name"], command=lambda n=action["name"]: self.current_action_name.set(n))
        if not self.key_actions.get(key, []):
            menu.add_command(label="Action 1", command=lambda: self.current_action_name.set("Action 1"))
        self.update_coord_listbox()

    def update_coord_listbox(self):
        self.coord_listbox.delete(0, tk.END)
        key = self.current_key.get()
        name = self.current_action_name.get()
        if key in self.key_actions:
            for action in self.key_actions[key]:
                if action["name"] == name:
                    for x, y, delay, click_type in action["coords"]:
                        self.coord_listbox.insert(tk.END, f"X: {x}, Y: {y}, Delay: {delay:.2f}s, Click: {click_type}")

    def add_coordinate(self):
        x = self.new_x_var.get()
        y = self.new_y_var.get()
        delay = self.new_delay_var.get()
        click_type = self.click_type_var.get()
        if delay < 0:
            messagebox.showerror("Lỗi", "Delay không thể âm!")
            return
        key = self.current_key.get()
        name = self.current_action_name.get()
        if key not in self.key_actions:
            self.key_actions[key] = []
        for action in self.key_actions[key]:
            if action["name"] == name:
                action["coords"].append((x, y, delay, click_type))
                break
        else:
            self.key_actions[key].append({"name": name, "coords": [(x, y, delay, click_type)]})
        self.update_coord_listbox()
        self.new_x_var.set(0)
        self.new_y_var.set(0)
        messagebox.showinfo("Thành công", f"Đã thêm tọa độ ({x}, {y}) vào hành động '{name}'!")

    def start_mouse_selection(self):
        if self.is_running or self.is_selecting or self.is_recording:
            messagebox.showwarning("Cảnh báo", "Vui lòng dừng chương trình, chế độ chọn hoặc ghi trước!")
            return
        self.is_selecting = True
        self.status_label.config(text="Trạng thái: Chọn tọa độ (nhấn Esc để dừng)", foreground="blue")
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Chọn tọa độ bằng chuột - Game Maker")
        self.preview_window.attributes("-alpha", 0.8)
        self.preview_window.attributes("-topmost", True)
        screen_width, screen_height = pyautogui.size()
        canvas = tk.Canvas(self.preview_window, width=screen_width, height=screen_height, bg="black")
        canvas.pack()
        canvas.create_text(10, 10, text="Nhấn chuột trái để chọn tọa độ, Esc để dừng", fill="white", anchor="nw")
        key = self.current_key.get()
        name = self.current_action_name.get()
        if key in self.key_actions:
            for action in self.key_actions[key]:
                if action["name"] == name:
                    for x, y, _, _ in action["coords"]:
                        canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        canvas.bind("<Button-1>", self.add_coord_click)
        threading.Thread(target=self.check_escape_key, daemon=True).start()

    def add_coord_click(self, event):
        if self.is_selecting:
            x, y = pyautogui.position()
            delay = self.new_delay_var.get()
            click_type = self.click_type_var.get()
            key = self.current_key.get()
            name = self.current_action_name.get()
            if key not in self.key_actions:
                self.key_actions[key] = []
            for action in self.key_actions[key]:
                if action["name"] == name:
                    action["coords"].append((x, y, delay, click_type))
                    break
            else:
                self.key_actions[key].append({"name": name, "coords": [(x, y, delay, click_type)]})
            self.update_coord_listbox()
            if self.preview_window:
                canvas = self.preview_window.winfo_children()[0]
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
            messagebox.showinfo("Thành công", f"Đã thêm tọa độ ({x}, {y}) vào hành động '{name}'!")

    def start_recording(self):
        if self.is_running or self.is_selecting or self.is_recording:
            messagebox.showwarning("Cảnh báo", "Vui lòng dừng chương trình, chế độ chọn hoặc ghi trước!")
            return
        self.is_recording = True
        self.status_label.config(text="Trạng thái: Đang ghi hành vi (nhấn Esc để dừng)", foreground="purple")
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Ghi hành vi chuột - Game Maker")
        self.preview_window.attributes("-alpha", 0.8)
        self.preview_window.attributes("-topmost", True)
        screen_width, screen_height = pyautogui.size()
        canvas = tk.Canvas(self.preview_window, width=screen_width, height=screen_height, bg="black")
        canvas.pack()
        canvas.create_text(10, 10, text="Nhấn chuột để ghi hành vi, Esc để dừng", fill="white", anchor="nw")
        key = self.current_key.get()
        name = self.current_action_name.get()
        if key in self.key_actions:
            for action in self.key_actions[key]:
                if action["name"] == name:
                    for x, y, _, _ in action["coords"]:
                        canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        canvas.bind("<Button-1>", lambda e: self.record_click("left"))
        canvas.bind("<Button-2>", lambda e: self.record_click("middle"))
        canvas.bind("<Button-3>", lambda e: self.record_click("right"))
        self.last_click_time = time.time()
        threading.Thread(target=self.check_escape_key, daemon=True).start()

    def record_click(self, click_type):
        if self.is_recording:
            x, y = pyautogui.position()
            current_time = time.time()
            delay = current_time - self.last_click_time if self.last_click_time else 0.1
            self.last_click_time = current_time
            key = self.current_key.get()
            name = self.current_action_name.get()
            if key not in self.key_actions:
                self.key_actions[key] = []
            for action in self.key_actions[key]:
                if action["name"] == name:
                    action["coords"].append((x, y, delay, click_type))
                    break
            else:
                self.key_actions[key].append({"name": name, "coords": [(x, y, delay, click_type)]})
            self.update_coord_listbox()
            if self.preview_window:
                canvas = self.preview_window.winfo_children()[0]
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
            messagebox.showinfo("Thành công", f"Đã ghi tọa độ ({x}, {y}) vào hành động '{name}'!")

    def check_escape_key(self):
        while self.is_selecting or self.is_recording:
            if keyboard.is_pressed("esc"):
                self.is_selecting = False
                self.is_recording = False
                if self.preview_window:
                    self.preview_window.destroy()
                    self.preview_window = None
                self.status_label.config(text="Trạng thái: Đang dừng", foreground="red")
                break
            time.sleep(0.05)

    def delete_coord(self, event=None):
        selected = self.coord_listbox.curselection()
        if selected:
            key = self.current_key.get()
            name = self.current_action_name.get()
            if key in self.key_actions:
                for action in self.key_actions[key]:
                    if action["name"] == name:
                        action["coords"].pop(selected[0])
                        self.update_coord_listbox()
                        messagebox.showinfo("Thành công", "Đã xóa tọa độ!")
                        break

    def preview_coordinates(self):
        key = self.current_key.get()
        name = self.current_action_name.get()
        coords = []
        if key in self.key_actions:
            for action in self.key_actions[key]:
                if action["name"] == name:
                    coords = action["coords"]
                    break
        if not coords and not self.random_mode_var.get():
            messagebox.showwarning("Cảnh báo", "Chưa có tọa độ nào để xem trước!")
            return
        if self.preview_window:
            self.preview_window.destroy()
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title(f"Xem trước vị trí click - Hành động {name} (Phím {key})")
        self.preview_window.attributes("-alpha", 0.8)
        self.preview_window.attributes("-topmost", True)
        screen_width, screen_height = pyautogui.size()
        canvas = tk.Canvas(self.preview_window, width=screen_width, height=screen_height, bg="black")
        canvas.pack()
        for x, y, _, _ in coords:
            canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        canvas.create_text(10, 10, text="Đóng cửa sổ này để dừng xem trước", fill="white", anchor="nw")

    def handle_key_press(self, key):
        if key.name in self.key_actions:
            self.current_active_key = key.name
        elif key.name == self.stop_key_var.get():
            self.stop_clicking()

    def auto_click(self):
        interval = self.interval_var.get()
        click_count = self.click_count_var.get()
        random_mode = self.random_mode_var.get()
        stop_key = self.stop_key_var.get()

        self.root.withdraw()
        self.status_label.config(text="Trạng thái: Đang chạy", foreground="green")
        time.sleep(3)

        # Đăng ký sự kiện nhấn phím
        for key in self.key_actions:
            keyboard.on_press_key(key, self.handle_key_press)
        keyboard.on_press_key(stop_key, self.handle_key_press)

        count = 0
        while self.is_running:
            try:
                # Thực hiện hành động của phím đang active
                if self.current_active_key and self.current_active_key in self.key_actions:
                    for action in self.key_actions[self.current_active_key]:
                        for x, y, delay, click_type in action["coords"]:
                            if not self.is_running or self.current_active_key != self.current_active_key:
                                break
                            pyautogui.click(x, y, button=click_type)
                            time.sleep(delay)
                        if not self.is_running or self.current_active_key != self.current_active_key:
                            break

                # Chế độ ngẫu nhiên (nếu bật)
                if random_mode and self.is_running:
                    screen_width, screen_height = pyautogui.size()
                    coords = [(random.randint(0, screen_width), random.randint(0, screen_height), 0.1, "left") for _ in range(3)]
                    for x, y, delay, click_type in coords:
                        if not self.is_running:
                            break
                        pyautogui.click(x, y, button=click_type)
                        time.sleep(delay)

                count += 1
                if click_count != 0 and count >= click_count:
                    self.stop_clicking()
                    break

                time.sleep(0.01)  # Độ trễ nhỏ để tăng độ nhạy phím

            except pyautogui.FailSafeException:
                self.stop_clicking()
                messagebox.showwarning("Cảnh báo", "Game Maker dừng do chuột di chuyển vào góc trên trái (failsafe).")
                break
            except Exception as e:
                self.stop_clicking()
                messagebox.showerror("Lỗi", f"Lỗi xảy ra: {e}")
                break

        # Hủy đăng ký sự kiện phím
        for key in self.key_actions:
            keyboard.unhook_key(key)
        keyboard.unhook_key(stop_key)
        self.root.deiconify()
        self.status_label.config(text="Trạng thái: Đã dừng", foreground="red")

    def start_clicking(self):
        if not self.is_running and not self.is_selecting and not self.is_recording:
            try:
                if self.interval_var.get() <= 0:
                    messagebox.showerror("Lỗi", "Khoảng thời gian phải lớn hơn 0!")
                    return
                if self.click_count_var.get() < 0:
                    messagebox.showerror("Lỗi", "Số chu kỳ click không thể âm!")
                    return
                if len(self.stop_key_var.get()) != 1:
                    messagebox.showerror("Lỗi", "Phím dừng phải là một ký tự!")
                    return
                if not self.random_mode_var.get() and not any(actions for actions in self.key_actions.values()):
                    messagebox.showerror("Lỗi", "Vui lòng thêm ít nhất một tọa độ hoặc bật chế độ ngẫu nhiên!")
                    return
                if self.stop_key_var.get() in self.key_actions:
                    messagebox.showerror("Lỗi", f"Phím dừng '{self.stop_key_var.get()}' trùng với phím hành động!")
                    return
                self.is_running = True
                self.thread = threading.Thread(target=self.auto_click, daemon=True)
                self.thread.start()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi xảy ra: {e}")
                self.is_running = False
                self.root.deiconify()

    def stop_clicking(self):
        self.is_running = False
        self.is_selecting = False
        self.is_recording = False
        self.current_active_key = None
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
        self.root.deiconify()
        self.status_label.config(text="Trạng thái: Đã dừng", foreground="red")

    def save_config(self):
        config = {
            "interval": self.interval_var.get(),
            "click_count": self.click_count_var.get(),
            "random_mode": self.random_mode_var.get(),
            "stop_key": self.stop_key_var.get(),
            "key_actions": {
                key: [
                    {"name": action["name"], "coords": [list(coord) for coord in action["coords"]]}
                    for action in actions
                ]
                for key, actions in self.key_actions.items()
            }
        }
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "w") as f:
                json.dump(config, f, indent=4)
            messagebox.showinfo("Thành công", "Cấu hình Game Maker đã được lưu!")

    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "r") as f:
                config = json.load(f)
            self.interval_var.set(config.get("interval", 1.0))
            self.click_count_var.set(config.get("click_count", 0))
            self.random_mode_var.set(config.get("random_mode", False))
            self.stop_key_var.set(config.get("stop_key", "q"))
            self.key_actions = {
                key: [
                    {"name": action["name"], "coords": [tuple(coord) for coord in action["coords"]]}
                    for action in actions
                ]
                for key, actions in config.get("key_actions", {}).items()
            }
            self.update_key_menu()
            self.current_key.set(list(self.key_actions.keys())[0] if self.key_actions else "1")
            self.update_action_menu()
            messagebox.showinfo("Thành công", "Cấu hình Game Maker đã được tải!")

if __name__ == "__main__":
    root = tk.Tk()
    app = GameMakerApp(root)
    root.mainloop()