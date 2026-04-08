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
        self.is_picking_trigger_color = False
        self.preview_window = None
        self.pending_color_coord_index = None
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
        self.color_trigger_enabled_var = tk.BooleanVar(value=False)
        self.trigger_x_var = tk.IntVar(value=0)
        self.trigger_y_var = tk.IntVar(value=0)
        self.trigger_r_var = tk.IntVar(value=255)
        self.trigger_g_var = tk.IntVar(value=255)
        self.trigger_b_var = tk.IntVar(value=255)
        self.color_tolerance_var = tk.IntVar(value=10)
        self.manual_color_r_var = tk.IntVar(value=255)
        self.manual_color_g_var = tk.IntVar(value=255)
        self.manual_color_b_var = tk.IntVar(value=255)
        self.manual_color_tolerance_var = tk.IntVar(value=10)

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

        # Frame trigger theo màu
        color_frame = ttk.LabelFrame(main_frame, text="Color Trigger", padding="10")
        color_frame.pack(fill="x", pady=5)

        ttk.Checkbutton(
            color_frame,
            text="Bật click theo nhận diện màu",
            variable=self.color_trigger_enabled_var
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=2)

        ttk.Label(color_frame, text="Điểm kiểm tra màu X:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(color_frame, textvariable=self.trigger_x_var, width=10).grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(color_frame, text="Y:").grid(row=1, column=2, sticky="w", pady=2)
        ttk.Entry(color_frame, textvariable=self.trigger_y_var, width=10).grid(row=1, column=3, sticky="w", pady=2)

        ttk.Label(color_frame, text="Màu mục tiêu (R,G,B):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(color_frame, textvariable=self.trigger_r_var, width=6).grid(row=2, column=1, sticky="w", pady=2)
        ttk.Entry(color_frame, textvariable=self.trigger_g_var, width=6).grid(row=2, column=2, sticky="w", pady=2)
        ttk.Entry(color_frame, textvariable=self.trigger_b_var, width=6).grid(row=2, column=3, sticky="w", pady=2)

        ttk.Label(color_frame, text="Tolerance (0-255):").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(color_frame, textvariable=self.color_tolerance_var, width=10).grid(row=3, column=1, sticky="w", pady=2)

        ttk.Button(
            color_frame,
            text="Lấy tọa độ trigger từ chuột",
            command=self.set_trigger_from_mouse
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        ttk.Button(
            color_frame,
            text="Lấy màu tại trigger",
            command=self.capture_trigger_color
        ).grid(row=4, column=2, columnspan=2, sticky="w", pady=5)
        ttk.Button(
            color_frame,
            text="Chọn màu bằng click màn hình",
            command=self.start_trigger_color_pick
        ).grid(row=5, column=0, columnspan=4, sticky="w", pady=5)

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
        self.coord_listbox.bind("<<ListboxSelect>>", self.on_coord_selected)

        coord_trigger_frame = ttk.Frame(coord_frame)
        coord_trigger_frame.pack(fill="x", pady=5)
        ttk.Button(
            coord_trigger_frame,
            text="Gán màu trigger cho tọa độ đã chọn",
            command=self.start_pick_color_for_selected_coord
        ).pack(side="left", padx=5)
        ttk.Button(
            coord_trigger_frame,
            text="Xóa màu trigger của tọa độ đã chọn",
            command=self.clear_selected_coord_trigger
        ).pack(side="left", padx=5)

        color_list_frame = ttk.LabelFrame(coord_frame, text="Màu trigger của tọa độ đang chọn", padding="8")
        color_list_frame.pack(fill="x", pady=5)
        self.coord_color_listbox = tk.Listbox(color_list_frame, height=4, font=("Arial", 10))
        self.coord_color_listbox.pack(fill="x", pady=4)
        self.coord_color_listbox.bind("<<ListboxSelect>>", self.on_coord_color_selected)

        color_edit_frame = ttk.Frame(color_list_frame)
        color_edit_frame.pack(fill="x", pady=2)
        ttk.Label(color_edit_frame, text="R:").grid(row=0, column=0, padx=5)
        ttk.Entry(color_edit_frame, textvariable=self.manual_color_r_var, width=6).grid(row=0, column=1, padx=5)
        ttk.Label(color_edit_frame, text="G:").grid(row=0, column=2, padx=5)
        ttk.Entry(color_edit_frame, textvariable=self.manual_color_g_var, width=6).grid(row=0, column=3, padx=5)
        ttk.Label(color_edit_frame, text="B:").grid(row=0, column=4, padx=5)
        ttk.Entry(color_edit_frame, textvariable=self.manual_color_b_var, width=6).grid(row=0, column=5, padx=5)
        ttk.Label(color_edit_frame, text="Tol:").grid(row=0, column=6, padx=5)
        ttk.Entry(color_edit_frame, textvariable=self.manual_color_tolerance_var, width=6).grid(row=0, column=7, padx=5)

        color_action_frame = ttk.Frame(color_list_frame)
        color_action_frame.pack(fill="x", pady=2)
        ttk.Button(
            color_action_frame,
            text="Thêm/Cập nhật màu (nhập tay)",
            command=self.add_or_update_selected_coord_color
        ).pack(side="left", padx=5)
        ttk.Button(
            color_action_frame,
            text="Xóa màu đang chọn",
            command=self.delete_selected_coord_color
        ).pack(side="left", padx=5)

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
        if not self.is_running and not self.is_selecting and not self.is_recording and not self.is_picking_trigger_color:
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
                    for coord in action["coords"]:
                        coord_item = self.normalize_coord(coord)
                        trigger_count = len(coord_item["trigger_colors"])
                        trigger_text = f"{trigger_count} màu trigger" if trigger_count else "No trigger"
                        self.coord_listbox.insert(
                            tk.END,
                            f"X: {coord_item['x']}, Y: {coord_item['y']}, Delay: {coord_item['delay']:.2f}s, Click: {coord_item['click_type']}, Trigger: {trigger_text}"
                        )
        self.refresh_coord_color_listbox()

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
        new_coord = {
            "x": x,
            "y": y,
            "delay": delay,
            "click_type": click_type,
            "trigger_colors": [],
        }
        for action in self.key_actions[key]:
            if action["name"] == name:
                action["coords"].append(new_coord)
                break
        else:
            self.key_actions[key].append({"name": name, "coords": [new_coord]})
        self.update_coord_listbox()
        self.new_x_var.set(0)
        self.new_y_var.set(0)
        messagebox.showinfo("Thành công", f"Đã thêm tọa độ ({x}, {y}) vào hành động '{name}'!")

    def start_mouse_selection(self):
        if self.is_running or self.is_selecting or self.is_recording or self.is_picking_trigger_color:
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
                    for coord in action["coords"]:
                        coord_item = self.normalize_coord(coord)
                        x, y = coord_item["x"], coord_item["y"]
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
            new_coord = {
                "x": x,
                "y": y,
                "delay": delay,
                "click_type": click_type,
                "trigger_colors": [],
            }
            for action in self.key_actions[key]:
                if action["name"] == name:
                    action["coords"].append(new_coord)
                    break
            else:
                self.key_actions[key].append({"name": name, "coords": [new_coord]})
            self.update_coord_listbox()
            if self.preview_window:
                canvas = self.preview_window.winfo_children()[0]
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
            messagebox.showinfo("Thành công", f"Đã thêm tọa độ ({x}, {y}) vào hành động '{name}'!")

    def start_recording(self):
        if self.is_running or self.is_selecting or self.is_recording or self.is_picking_trigger_color:
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
                    for coord in action["coords"]:
                        coord_item = self.normalize_coord(coord)
                        x, y = coord_item["x"], coord_item["y"]
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
            new_coord = {
                "x": x,
                "y": y,
                "delay": delay,
                "click_type": click_type,
                "trigger_colors": [],
            }
            for action in self.key_actions[key]:
                if action["name"] == name:
                    action["coords"].append(new_coord)
                    break
            else:
                self.key_actions[key].append({"name": name, "coords": [new_coord]})
            self.update_coord_listbox()
            if self.preview_window:
                canvas = self.preview_window.winfo_children()[0]
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
            messagebox.showinfo("Thành công", f"Đã ghi tọa độ ({x}, {y}) vào hành động '{name}'!")

    def check_escape_key(self):
        while self.is_selecting or self.is_recording or self.is_picking_trigger_color:
            if keyboard.is_pressed("esc"):
                self.is_selecting = False
                self.is_recording = False
                self.is_picking_trigger_color = False
                self.pending_color_coord_index = None
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

    def get_current_action(self):
        key = self.current_key.get()
        name = self.current_action_name.get()
        if key in self.key_actions:
            for action in self.key_actions[key]:
                if action["name"] == name:
                    return action
        return None

    def get_selected_coord(self):
        action = self.get_current_action()
        selected_index = self.get_selected_coord_index()
        if action is None or selected_index is None or selected_index >= len(action["coords"]):
            return None, None, None
        coord = self.normalize_coord(action["coords"][selected_index])
        return action, selected_index, coord

    def normalize_coord(self, coord):
        if isinstance(coord, dict):
            trigger_colors = []
            raw_colors = coord.get("trigger_colors")
            if isinstance(raw_colors, list):
                for item in raw_colors:
                    if isinstance(item, dict):
                        trigger_colors.append({
                            "r": int(item.get("r", 255)),
                            "g": int(item.get("g", 255)),
                            "b": int(item.get("b", 255)),
                            "tolerance": int(item.get("tolerance", 10)),
                        })
            elif coord.get("trigger_color"):
                # Tương thích cấu hình cũ chỉ có 1 màu
                old = coord.get("trigger_color")
                trigger_colors.append({
                    "r": int(old.get("r", 255)),
                    "g": int(old.get("g", 255)),
                    "b": int(old.get("b", 255)),
                    "tolerance": int(old.get("tolerance", 10)),
                })
            return {
                "x": int(coord.get("x", 0)),
                "y": int(coord.get("y", 0)),
                "delay": float(coord.get("delay", 0.1)),
                "click_type": coord.get("click_type", "left"),
                "trigger_colors": trigger_colors,
            }
        if isinstance(coord, (list, tuple)) and len(coord) >= 4:
            return {
                "x": int(coord[0]),
                "y": int(coord[1]),
                "delay": float(coord[2]),
                "click_type": coord[3],
                "trigger_colors": [],
            }
        return {"x": 0, "y": 0, "delay": 0.1, "click_type": "left", "trigger_colors": []}

    def get_selected_coord_index(self):
        selected = self.coord_listbox.curselection()
        if not selected:
            return None
        return selected[0]

    def start_pick_color_for_selected_coord(self):
        if self.is_running or self.is_selecting or self.is_recording or self.is_picking_trigger_color:
            messagebox.showwarning("Cảnh báo", "Vui lòng dừng chương trình, chế độ chọn hoặc ghi trước!")
            return
        selected_index = self.get_selected_coord_index()
        if selected_index is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một tọa độ trong danh sách trước!")
            return
        self.pending_color_coord_index = selected_index
        self.start_trigger_color_pick()

    def clear_selected_coord_trigger(self):
        action, selected_index, coord = self.get_selected_coord()
        if action is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một tọa độ trong danh sách trước!")
            return
        coord["trigger_colors"] = []
        action["coords"][selected_index] = coord
        self.update_coord_listbox()
        self.coord_listbox.selection_set(selected_index)
        messagebox.showinfo("Thành công", "Đã xóa màu trigger của tọa độ đã chọn.")

    def refresh_coord_color_listbox(self):
        self.coord_color_listbox.delete(0, tk.END)
        _, _, coord = self.get_selected_coord()
        if not coord:
            return
        for color in coord["trigger_colors"]:
            self.coord_color_listbox.insert(
                tk.END,
                f"RGB({color['r']},{color['g']},{color['b']}), Tol:{color['tolerance']}"
            )

    def on_coord_selected(self, event=None):
        self.refresh_coord_color_listbox()

    def on_coord_color_selected(self, event=None):
        _, _, coord = self.get_selected_coord()
        if not coord:
            return
        selected = self.coord_color_listbox.curselection()
        if not selected:
            return
        color = coord["trigger_colors"][selected[0]]
        self.manual_color_r_var.set(color["r"])
        self.manual_color_g_var.set(color["g"])
        self.manual_color_b_var.set(color["b"])
        self.manual_color_tolerance_var.set(color["tolerance"])

    def add_or_update_selected_coord_color(self):
        action, selected_index, coord = self.get_selected_coord()
        if action is None:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một tọa độ trong danh sách trước!")
            return
        try:
            r = max(0, min(255, int(self.manual_color_r_var.get())))
            g = max(0, min(255, int(self.manual_color_g_var.get())))
            b = max(0, min(255, int(self.manual_color_b_var.get())))
            tolerance = max(0, min(255, int(self.manual_color_tolerance_var.get())))
        except Exception:
            messagebox.showerror("Lỗi", "Giá trị RGB/Tolerance phải là số nguyên.")
            return
        selected_color = self.coord_color_listbox.curselection()
        payload = {"r": r, "g": g, "b": b, "tolerance": tolerance}
        if selected_color:
            coord["trigger_colors"][selected_color[0]] = payload
        else:
            coord["trigger_colors"].append(payload)
        action["coords"][selected_index] = coord
        self.update_coord_listbox()
        self.coord_listbox.selection_set(selected_index)
        self.refresh_coord_color_listbox()

    def delete_selected_coord_color(self):
        action, selected_index, coord = self.get_selected_coord()
        selected_color = self.coord_color_listbox.curselection()
        if action is None or not selected_color:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn màu trong danh sách màu.")
            return
        coord["trigger_colors"].pop(selected_color[0])
        action["coords"][selected_index] = coord
        self.update_coord_listbox()
        self.coord_listbox.selection_set(selected_index)
        self.refresh_coord_color_listbox()

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
        for coord in coords:
            coord_item = self.normalize_coord(coord)
            x, y = coord_item["x"], coord_item["y"]
            canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        canvas.create_text(10, 10, text="Đóng cửa sổ này để dừng xem trước", fill="white", anchor="nw")

    def handle_key_press(self, key):
        if key.name in self.key_actions:
            self.current_active_key = key.name
        elif key.name == self.stop_key_var.get():
            self.stop_clicking()

    def set_trigger_from_mouse(self):
        x, y = pyautogui.position()
        self.trigger_x_var.set(x)
        self.trigger_y_var.set(y)
        messagebox.showinfo("Thành công", f"Đã đặt điểm trigger tại ({x}, {y})")

    def capture_trigger_color(self):
        try:
            x = self.trigger_x_var.get()
            y = self.trigger_y_var.get()
            r, g, b = pyautogui.pixel(x, y)
            self.trigger_r_var.set(r)
            self.trigger_g_var.set(g)
            self.trigger_b_var.set(b)
            messagebox.showinfo("Thành công", f"Đã lấy màu tại ({x}, {y}): RGB({r}, {g}, {b})")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lấy màu: {e}")

    def start_trigger_color_pick(self):
        if self.is_running or self.is_selecting or self.is_recording or self.is_picking_trigger_color:
            messagebox.showwarning("Cảnh báo", "Vui lòng dừng chương trình, chế độ chọn hoặc ghi trước!")
            return

        self.is_picking_trigger_color = True
        self.status_label.config(text="Trạng thái: Chọn màu trigger (click để lấy, Esc để hủy)", foreground="blue")

        if self.preview_window:
            self.preview_window.destroy()
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Chọn màu trigger - Game Maker")
        self.preview_window.attributes("-topmost", True)
        self.preview_window.attributes("-alpha", 0.2)
        self.preview_window.attributes("-fullscreen", True)

        canvas = tk.Canvas(self.preview_window, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_text(
            10,
            10,
            text="Di chuyển chuột đến điểm màu cần lấy, click chuột trái để chọn (Esc để hủy)",
            fill="white",
            anchor="nw",
        )
        canvas.bind("<Button-1>", self.pick_trigger_color_click)

        threading.Thread(target=self.check_escape_key, daemon=True).start()

    def pick_trigger_color_click(self, event):
        if not self.is_picking_trigger_color:
            return

        x = event.x_root
        y = event.y_root
        self.trigger_x_var.set(x)
        self.trigger_y_var.set(y)

        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None

        self.root.update_idletasks()
        time.sleep(0.05)

        try:
            r, g, b = pyautogui.pixel(x, y)
            action = self.get_current_action()
            if action is not None and self.pending_color_coord_index is not None and self.pending_color_coord_index < len(action["coords"]):
                coord = self.normalize_coord(action["coords"][self.pending_color_coord_index])
                coord["trigger_colors"].append({
                    "r": r,
                    "g": g,
                    "b": b,
                    "tolerance": self.color_tolerance_var.get(),
                })
                action["coords"][self.pending_color_coord_index] = coord
                self.update_coord_listbox()
                self.coord_listbox.selection_set(self.pending_color_coord_index)
                self.refresh_coord_color_listbox()
                messagebox.showinfo(
                    "Thành công",
                    f"Đã thêm màu trigger RGB({r}, {g}, {b}) cho tọa độ ({coord['x']}, {coord['y']})."
                )
            else:
                self.trigger_r_var.set(r)
                self.trigger_g_var.set(g)
                self.trigger_b_var.set(b)
                messagebox.showinfo("Thành công", f"Đã lấy màu RGB({r}, {g}, {b}) tại ({x}, {y})")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lấy màu: {e}")
        finally:
            self.pending_color_coord_index = None
            self.is_picking_trigger_color = False
            self.status_label.config(text="Trạng thái: Đang dừng", foreground="red")

    def is_trigger_color_matched(self):
        if not self.color_trigger_enabled_var.get():
            return True
        x = self.trigger_x_var.get()
        y = self.trigger_y_var.get()
        target = (
            self.trigger_r_var.get(),
            self.trigger_g_var.get(),
            self.trigger_b_var.get(),
        )
        tolerance = max(0, min(255, self.color_tolerance_var.get()))
        current = pyautogui.pixel(x, y)
        return all(abs(current[i] - target[i]) <= tolerance for i in range(3))

    def is_coord_trigger_matched(self, coord):
        coord_item = self.normalize_coord(coord)
        trigger_colors = coord_item["trigger_colors"]
        if trigger_colors:
            current = pyautogui.pixel(coord_item["x"], coord_item["y"])
            for trigger in trigger_colors:
                tolerance = max(0, min(255, int(trigger.get("tolerance", 10))))
                if all(abs(current[i] - int(trigger[channel])) <= tolerance for i, channel in enumerate(("r", "g", "b"))):
                    return True
            return False
        return self.is_trigger_color_matched()

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
                        for coord in action["coords"]:
                            coord_item = self.normalize_coord(coord)
                            x = coord_item["x"]
                            y = coord_item["y"]
                            delay = coord_item["delay"]
                            click_type = coord_item["click_type"]
                            if not self.is_running or self.current_active_key != self.current_active_key:
                                break
                            if self.is_coord_trigger_matched(coord_item):
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
                        if self.is_trigger_color_matched():
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
        if not self.is_running and not self.is_selecting and not self.is_recording and not self.is_picking_trigger_color:
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
                if self.color_tolerance_var.get() < 0:
                    messagebox.showerror("Lỗi", "Tolerance màu không thể âm!")
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
        self.is_picking_trigger_color = False
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
            "color_trigger": {
                "enabled": self.color_trigger_enabled_var.get(),
                "x": self.trigger_x_var.get(),
                "y": self.trigger_y_var.get(),
                "r": self.trigger_r_var.get(),
                "g": self.trigger_g_var.get(),
                "b": self.trigger_b_var.get(),
                "tolerance": self.color_tolerance_var.get(),
            },
            "key_actions": {
                key: [
                    {"name": action["name"], "coords": [self.normalize_coord(coord) for coord in action["coords"]]}
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
            color_trigger = config.get("color_trigger", {})
            self.color_trigger_enabled_var.set(color_trigger.get("enabled", False))
            self.trigger_x_var.set(color_trigger.get("x", 0))
            self.trigger_y_var.set(color_trigger.get("y", 0))
            self.trigger_r_var.set(color_trigger.get("r", 255))
            self.trigger_g_var.set(color_trigger.get("g", 255))
            self.trigger_b_var.set(color_trigger.get("b", 255))
            self.color_tolerance_var.set(color_trigger.get("tolerance", 10))
            self.key_actions = {
                key: [
                    {"name": action["name"], "coords": [self.normalize_coord(coord) for coord in action["coords"]]}
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