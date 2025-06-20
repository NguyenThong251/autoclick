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
        self.root.title("Game Maker")
        self.root.geometry("600x700")
        self.root.configure(bg="#f0f0f0")
        self.is_running = False
        self.is_selecting = False
        self.is_recording = False
        self.preview_window = None
        self.thread = None
        self.coordinates = []  # Danh sách tọa độ: [(x, y, delay, click_type), ...]
        self.last_click_time = None

        # Biến lưu trữ
        self.interval_var = tk.DoubleVar(value=1.0)
        self.random_mode_var = tk.BooleanVar(value=False)
        self.click_count_var = tk.IntVar(value=0)
        self.stop_key_var = tk.StringVar(value="q")
        self.new_x_var = tk.IntVar(value=0)
        self.new_y_var = tk.IntVar(value=0)
        self.new_delay_var = tk.DoubleVar(value=0.1)
        self.click_type_var = tk.StringVar(value="left")

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
        ttk.Label(main_frame, text="Game Maker", font=("Arial", 16, "bold"), background="#f0f0f0").pack(pady=10)

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

        # Frame quản lý tọa độ
        coord_frame = ttk.LabelFrame(main_frame, text="Quản lý tọa độ", padding="10")
        coord_frame.pack(fill="both", expand=True, pady=5)

        self.coord_listbox = tk.Listbox(coord_frame, height=8, font=("Arial", 10))
        self.coord_listbox.pack(fill="both", expand=True, pady=5)
        self.coord_listbox.bind("<Delete>", self.remove_selected_coord)

        # Frame thêm tọa độ
        new_coord_frame = ttk.Frame(coord_frame)
        new_coord_frame.pack(fill="x", pady=5)

        ttk.Label(new_coord_frame, text="X:").grid(row=0, column=0, padx=5)
        ttk.Entry(new_coord_frame, textvariable=self.new_x_var, width=10).grid(row=0, column=1)
        ttk.Label(new_coord_frame, text="Y:").grid(row=0, column=2, padx=5)
        ttk.Entry(new_coord_frame, textvariable=self.new_y_var, width=10).grid(row=0, column=3)
        ttk.Label(new_coord_frame, text="Delay (giây):").grid(row=0, column=4, padx=5)
        ttk.Entry(new_coord_frame, textvariable=self.new_delay_var, width=10).grid(row=0, column=5)

        ttk.Label(new_coord_frame, text="Loại click:").grid(row=1, column=0, padx=5, pady=5)
        ttk.OptionMenu(new_coord_frame, self.click_type_var, "left", "left", "right", "middle").grid(row=1, column=1, columnspan=2, pady=5)

        ttk.Button(new_coord_frame, text="Thêm tọa độ", command=self.add_coordinate).grid(row=1, column=3, padx=5, pady=5)
        ttk.Button(new_coord_frame, text="Chọn bằng chuột", command=self.start_mouse_selection).grid(row=1, column=4, padx=5, pady=5)
        ttk.Button(new_coord_frame, text="Ghi hành vi", command=self.start_recording).grid(row=1, column=5, padx=5, pady=5)

        # Frame điều khiển
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=5)

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

    def update_mouse_position(self):
        if not self.is_running and not self.is_selecting and not self.is_recording:
            x, y = pyautogui.position()
            self.mouse_pos_label.config(text=f"Tọa độ chuột: ({x}, {y})")
            self.new_x_var.set(x)
            self.new_y_var.set(y)
        self.root.after(100, self.update_mouse_position)

    def add_coordinate(self):
        x = self.new_x_var.get()
        y = self.new_y_var.get()
        delay = self.new_delay_var.get()
        click_type = self.click_type_var.get()
        if delay < 0:
            messagebox.showerror("Lỗi", "Delay không thể âm!")
            return
        self.coordinates.append((x, y, delay, click_type))
        self.coord_listbox.insert(tk.END, f"X: {x}, Y: {y}, Delay: {delay:.2f}s, Click: {click_type}")
        self.new_x_var.set(0)
        self.new_y_var.set(0)

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
        for x, y, _, _ in self.coordinates:
            canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        canvas.bind("<Button-1>", self.add_coord_by_mouse)
        threading.Thread(target=self.check_escape_key, daemon=True).start()

    def add_coord_by_mouse(self, event):
        if self.is_selecting:
            x, y = pyautogui.position()
            delay = self.new_delay_var.get()
            click_type = self.click_type_var.get()
            self.coordinates.append((x, y, delay, click_type))
            self.coord_listbox.insert(tk.END, f"X: {x}, Y: {y}, Delay: {delay:.2f}s, Click: {click_type}")
            if self.preview_window:
                canvas = self.preview_window.winfo_children()[0]
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")

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
        for x, y, _, _ in self.coordinates:
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
            self.coordinates.append((x, y, delay, click_type))
            self.coord_listbox.insert(tk.END, f"X: {x}, Y: {y}, Delay: {delay:.2f}s, Click: {click_type}")
            if self.preview_window:
                canvas = self.preview_window.winfo_children()[0]
                canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")

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
            time.sleep(0.1)

    def remove_selected_coord(self, event=None):
        selected = self.coord_listbox.curselection()
        if selected:
            self.coordinates.pop(selected[0])
            self.coord_listbox.delete(selected[0])

    def preview_coordinates(self):
        if not self.coordinates and not self.random_mode_var.get():
            messagebox.showwarning("Cảnh báo", "Chưa có tọa độ nào để xem trước!")
            return
        if self.preview_window:
            self.preview_window.destroy()
        self.preview_window = tk.Toplevel(self.root)
        self.preview_window.title("Xem trước vị trí click - Game Maker")
        self.preview_window.attributes("-alpha", 0.8)
        self.preview_window.attributes("-topmost", True)
        screen_width, screen_height = pyautogui.size()
        canvas = tk.Canvas(self.preview_window, width=screen_width, height=screen_height, bg="black")
        canvas.pack()
        for x, y, _, _ in self.coordinates:
            canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        canvas.create_text(10, 10, text="Đóng cửa sổ này để dừng xem trước", fill="white", anchor="nw")

    def auto_click(self):
        interval = self.interval_var.get()
        click_count = self.click_count_var.get()
        random_mode = self.random_mode_var.get()
        stop_key = self.stop_key_var.get()

        # Ẩn UI
        self.root.withdraw()
        self.status_label.config(text="Trạng thái: Đang chạy", foreground="green")
        print("Bắt đầu Game Maker trong 3 giây...")
        time.sleep(3)

        count = 0
        while self.is_running:
            try:
                if keyboard.is_pressed(stop_key):
                    self.stop_clicking()
                    break

                if random_mode:
                    screen_width, screen_height = pyautogui.size()
                    coords = [(random.randint(0, screen_width), random.randint(0, screen_height), 0.1, "left") for _ in range(3)]
                else:
                    coords = self.coordinates

                for x, y, delay, click_type in coords:
                    pyautogui.click(x, y, button=click_type)
                    print(f"Clicked tại: ({x}, {y}) với {click_type} click")
                    time.sleep(delay)

                count += 1
                if click_count != 0 and count >= click_count:
                    self.stop_clicking()
                    break

                time.sleep(interval)

            except pyautogui.FailSafeException:
                print("Failsafe kích hoạt: Chuột di chuyển vào góc trên bên trái màn hình.")
                self.stop_clicking()
                messagebox.showwarning("Cảnh báo", "Game Maker dừng do chuột di chuyển vào góc trên bên trái (failsafe).")
                break

        # Hiển thị lại UI
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
                if not self.random_mode_var.get() and not self.coordinates:
                    messagebox.showerror("Lỗi", "Vui lòng thêm ít nhất một tọa độ hoặc bật chế độ ngẫu nhiên!")
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
            "coordinates": self.coordinates
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
            self.coordinates = config.get("coordinates", [])
            self.coord_listbox.delete(0, tk.END)
            for x, y, delay, click_type in self.coordinates:
                self.coord_listbox.insert(tk.END, f"X: {x}, Y: {y}, Delay: {delay:.2f}s, Click: {click_type}")
            messagebox.showinfo("Thành công", "Cấu hình Game Maker đã được tải!")

if __name__ == "__main__":
    root = tk.Tk()
    app = GameMakerApp(root)
    root.mainloop()