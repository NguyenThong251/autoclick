import os as _os
import sys as _sys


def _tu_chuyen_sang_pythonw():
    """Chạy bằng python.exe thì bàn giao cho pythonw.exe rồi thoát.

    python.exe luôn kéo theo một cửa sổ console đen. Trên Windows 11 không ẩn
    được nó bằng ShowWindow: cửa sổ thật nằm ở tiến trình WindowsTerminal.exe
    khác, GetConsoleWindow() chỉ trả về một stub vô hình. Cách duy nhất sạch là
    chạy bằng pythonw.exe, vốn không tạo console.

    Làm ở đây để anh vẫn gõ "python clicker.py" như cũ mà không thấy console.
    """
    if _os.environ.get("AUTOCLICK_NO_RELAUNCH"):
        return                      # đã là tiến trình con, chạy tiếp bình thường
    exe = _sys.executable or ""
    if _os.path.basename(exe).lower() != "python.exe":
        return                      # đã là pythonw.exe rồi
    pyw = _os.path.join(_os.path.dirname(exe), "pythonw.exe")
    if not _os.path.isfile(pyw):
        return                      # không có pythonw thì chạy như cũ, còn hơn không chạy
    import subprocess
    env = dict(_os.environ, AUTOCLICK_NO_RELAUNCH="1")
    try:
        subprocess.Popen(
            [pyw, _os.path.abspath(__file__)] + _sys.argv[1:],
            creationflags=0x00000008 | 0x00000200,   # DETACHED_PROCESS | NEW_PROCESS_GROUP
            close_fds=True, env=env,
            cwd=_os.path.dirname(_os.path.abspath(__file__)),
        )
    except Exception:
        return                      # bàn giao hỏng thì vẫn chạy được, chỉ là còn console
    _sys.exit(0)


_tu_chuyen_sang_pythonw()


def _bao_loi(etype, value, tb):
    """Hiện lỗi ra hộp thoại và ghi vào file.

    Chạy bằng pythonw thì không còn console, nên lỗi sẽ biến mất không dấu vết
    nếu không có hàm này. Bắt buộc phải đi kèm việc ẩn console.
    """
    import traceback
    import ctypes
    text = "".join(traceback.format_exception(etype, value, tb))
    try:
        log = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "loi.log")
        with open(log, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(0, text[-1500:], "Game Maker - Lỗi", 0x10)
    except Exception:
        pass


_sys.excepthook = _bao_loi

import threading as _threading

_threading.excepthook = lambda a: _bao_loi(a.exc_type, a.exc_value, a.exc_traceback)

import ctypes as _ctypes

# Khai báo DPI mức per-monitor NGAY TRƯỚC mọi import khác. Dòng này bắt buộc
# phải đứng ở đây: khi tkinter hoặc pyautogui nạp xong thì Windows đã chốt mức
# DPI của tiến trình và không đổi được nữa.
#
# Không có nó, trên máy nhiều màn hình đặt scaling khác nhau Windows dùng những
# hệ tọa độ lệch nhau cho cùng một điểm: chỗ đặt cửa sổ, chỗ con trỏ chuột và
# chỗ đọc màu ra ba con số khác nhau. Hậu quả là tọa độ chọn trên màn phụ bị
# trượt. Khai báo per-monitor gộp tất cả về một hệ duy nhất.
def _khai_bao_dpi_per_monitor():
    PER_MONITOR_AWARE_V2 = _ctypes.c_void_p(-4)
    try:
        _ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [_ctypes.c_void_p]
        _ctypes.windll.user32.SetProcessDpiAwarenessContext.restype = _ctypes.c_int
        if _ctypes.windll.user32.SetProcessDpiAwarenessContext(PER_MONITOR_AWARE_V2):
            return True
    except Exception:
        pass
    # Máy cũ không có hàm trên thì thử API đời trước
    try:
        return _ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0
    except Exception:
        return False


DPI_PER_MONITOR = _khai_bao_dpi_per_monitor()

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

import screens
import settings

# Giá trị của ô "Mở app tại" khi muốn app nhớ chỗ cũ thay vì gắn vào một màn
NHO_VI_TRI_CU = "Nhớ vị trí lần trước"


def chuan_hoa_phim(raw):
    """Đổi tên phím người dùng nhập thành tên chuẩn, hoặc None nếu không hợp lệ.

    Bắt buộc phải chuẩn hóa TRƯỚC KHI LƯU. Sự kiện bàn phím luôn báo tên đã
    chuẩn hóa ("page up"), nên nếu lưu "pgup" thì hook vẫn đăng ký được nhưng
    tra cứu sẽ trượt và phím im lặng không làm gì — loại lỗi rất khó tìm.

    Lưu ý: "pgdn", "prior", "next" KHÔNG hợp lệ trên Windows, phải viết
    "page down" hoặc "pgdown".
    """
    s = (raw or "").strip()
    if not s:
        return None
    try:
        ten = keyboard.normalize_name(s)
        keyboard.key_to_scan_codes(ten)   # ném lỗi nếu Windows không map được
        return ten
    except (ValueError, KeyError):
        return None

# Cấu hình PyAutoGUI
# Tắt failsafe: mặc định pyautogui dừng chương trình khi chuột chạm góc trên
# trái. Ở đây điều đó vô nghĩa vì auto vốn đã tự nhường khi người dùng động
# vào chuột, mà nó lại làm app dừng hẳn kèm hộp thoại giữa lúc đang chạy.
# Đường thoát khẩn cấp giờ là phím thoát, dùng được mọi lúc.
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05

# Chuột phải đứng yên đủ lâu chừng này thì auto mới chạy tiếp
GIAY_CHO_CHUOT_RANH = 2.0

class GameMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Game Maker - Multi Action")
        self.root.geometry("900x750")
        self.root.configure(bg="#f0f0f0")
        self.settings = settings.load()
        self.is_running = False
        self.is_selecting = False
        self.is_recording = False
        self.is_picking_trigger_color = False
        self.is_quitting = False
        self._mouse_after_id = None

        # --- trạng thái tạm dừng ---
        # Dùng Event chứ không phải vòng lặp kiểm tra cờ: vòng lặp bận ngốn trọn
        # một lõi CPU, còn Event.wait() gần như không tốn gì mà vẫn tỉnh dậy
        # trong chưa tới một phần nghìn giây.
        self.is_paused = False
        self._pause_lock = threading.Lock()
        self._resume_evt = threading.Event()
        self._resume_evt.set()          # đặt = đang chạy, xóa = đang tạm dừng
        self._stop_evt = threading.Event()   # đặt = phải thoát khỏi mọi giấc ngủ

        # Bản sao thuần Python của tên phím. Hàm xử lý phím chạy trên thread
        # riêng của thư viện keyboard, đọc biến Tkinter từ đó sẽ treo cứng sau
        # khi cửa sổ bị hủy, nên phải đọc từ bản sao này.
        self._pause_key = "page down"
        self._stop_key = "page up"
        self._keys_down = set()         # lọc auto-repeat khi giữ phím
        self._kb_hook = None
        self._cap_handle = None         # đang bắt phím cho nút "Bấm phím để gán"
        self._cap_timer = None

        # Bản chụp cấu hình cho vòng lặp auto, lấy ở main thread lúc bấm Bắt đầu
        self._cfg_click_count = 0
        self._cfg_random = False
        self._cfg_trigger = None

        # --- nhường chuột cho người dùng ---
        # Chính app cũng làm con trỏ nhảy mỗi lần click, nên muốn biết người
        # dùng có động vào chuột hay không thì phải nhớ chỗ app vừa đặt con trỏ
        # tới, rồi so với chỗ con trỏ đang thực sự nằm.
        self._vi_tri_app_dat = None
        self._vi_tri_chuot_cuoi = None
        self._luc_chuot_doi = 0.0

        self.screens = screens.ScreenLayout()
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
        # Phím mặc định là Page Up / Page Down, và nhớ lại lựa chọn của lần trước
        self.stop_key_var = tk.StringVar(
            value=chuan_hoa_phim(self.settings.get("stop_key")) or "page up"
        )
        self.pause_key_var = tk.StringVar(
            value=chuan_hoa_phim(self.settings.get("pause_key")) or "page down"
        )
        self._stop_key = self.stop_key_var.get()
        self._pause_key = self.pause_key_var.get()
        # Giữ bản sao thuần Python đồng bộ với ô nhập, để thread bàn phím dùng
        self.stop_key_var.trace_add("write", self._dong_bo_ten_phim)
        self.pause_key_var.trace_add("write", self._dong_bo_ten_phim)
        self.new_x_var = tk.IntVar(value=0)
        self.new_y_var = tk.IntVar(value=0)
        self.new_delay_var = tk.DoubleVar(value=0.1)
        self.click_type_var = tk.StringVar(value="left")
        self.new_key_var = tk.StringVar(value="1")
        self.new_action_name_var = tk.StringVar(value="Action 1")
        self.new_monitor_var = tk.StringVar(value="Tự động")
        self.startup_monitor_var = tk.StringVar(value=NHO_VI_TRI_CU)
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

        # Container chính có thanh cuộn dọc
        outer_frame = ttk.Frame(self.root)
        outer_frame.pack(fill="both", expand=True)

        self.main_canvas = tk.Canvas(outer_frame, bg="#f0f0f0", highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(outer_frame, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=main_scrollbar.set)
        main_scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)

        main_frame = ttk.Frame(self.main_canvas, padding="10")
        main_frame_window = self.main_canvas.create_window((0, 0), window=main_frame, anchor="nw")

        main_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        # Cho main_frame rộng bằng canvas để các frame con fill="x" đúng
        self.main_canvas.bind(
            "<Configure>",
            lambda e: self.main_canvas.itemconfigure(main_frame_window, width=e.width)
        )
        # Cuộn bằng con lăn chuột khi trỏ trong cửa sổ chính
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

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

        ttk.Label(config_frame, text="Phím tạm dừng / chạy tiếp:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(config_frame, textvariable=self.pause_key_var, width=14).grid(row=3, column=1, sticky="w", pady=2)
        self.nut_bat_pause = ttk.Button(
            config_frame, text="Bấm phím để gán",
            command=lambda: self.bat_dau_gan_phim(self.pause_key_var, self.nut_bat_pause),
        )
        self.nut_bat_pause.grid(row=3, column=2, sticky="w", padx=5, pady=2)

        ttk.Label(config_frame, text="Phím thoát hẳn chương trình:").grid(row=4, column=0, sticky="w", pady=2)
        ttk.Entry(config_frame, textvariable=self.stop_key_var, width=14).grid(row=4, column=1, sticky="w", pady=2)
        self.nut_bat_stop = ttk.Button(
            config_frame, text="Bấm phím để gán",
            command=lambda: self.bat_dau_gan_phim(self.stop_key_var, self.nut_bat_stop),
        )
        self.nut_bat_stop.grid(row=4, column=2, sticky="w", padx=5, pady=2)

        ttk.Label(config_frame, text="Mở app tại:").grid(row=5, column=0, sticky="w", pady=2)
        self.startup_monitor_menu = ttk.OptionMenu(
            config_frame, self.startup_monitor_var, NHO_VI_TRI_CU
        )
        self.startup_monitor_menu.grid(row=5, column=1, sticky="w", pady=2)

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

        ttk.Label(new_coord_frame, text="Màn hình:").grid(row=2, column=0, padx=10, pady=5)
        self.monitor_menu = ttk.OptionMenu(new_coord_frame, self.new_monitor_var, "Tự động")
        self.monitor_menu.grid(row=2, column=1, columnspan=2, sticky="w", pady=5)
        ttk.Button(
            new_coord_frame,
            text="Nhận diện lại màn hình",
            command=self.rescan_screens_announce,
        ).grid(row=2, column=3, columnspan=2, padx=10, pady=5)

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
        self.monitor_status_label = ttk.Label(status_frame, text="Màn hình: đang nhận diện...")
        self.monitor_status_label.pack(pady=2)

        self.update_monitor_menu()
        self.update_startup_menu()
        self.update_mouse_position()
        self.update_key_menu()
        self.khoi_phuc_vi_tri_cua_so()
        self.dang_ky_hook_ban_phim()
        # Bấm nút X cũng phải lưu lại vị trí như khi thoát bằng phím dừng
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.after(300, self.canh_bao_dpi_neu_can)

    def _on_mousewheel(self, event):
        # Để Listbox tự cuộn nội dung của nó, chỉ cuộn trang khi trỏ ngoài Listbox
        widget = event.widget
        if isinstance(widget, tk.Listbox):
            return
        if widget.winfo_toplevel() is not self.root:
            return
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def update_mouse_position(self):
        if self.is_quitting:
            return
        self._mouse_after_id = None
        if not self.is_running and not self.is_selecting and not self.is_recording and not self.is_picking_trigger_color:
            x, y = pyautogui.position()
            self.mouse_pos_label.config(text=f"Tọa độ chuột: ({x}, {y})")
            self.new_x_var.set(x)
            self.new_y_var.set(y)
        self._mouse_after_id = self.root.after(100, self.update_mouse_position)

    def add_key(self):
        key = chuan_hoa_phim(self.new_key_var.get())
        if key is None:
            messagebox.showerror(
                "Lỗi",
                "Tên phím không hợp lệ.\n"
                "Ví dụ: a, 1, f5, page up, page down, home, end, insert, delete\n"
                "(lưu ý: 'pgdn' và 'prior' không dùng được, phải viết 'page down')",
            )
            return
        if key in self.key_actions:
            messagebox.showwarning("Cảnh báo", f"Phím '{key}' đã tồn tại!")
            return
        self.key_actions[key] = []
        self.update_key_menu()
        self.current_key.set(key)
        self.update_action_menu()
        # Phím số thì gợi ý số kế tiếp, phím khác thì để nguyên cho người dùng tự đổi
        if key.isdigit():
            self.new_key_var.set(str(int(key) + 1))
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
                        tag = self.monitor_tag(coord_item)
                        self.coord_listbox.insert(
                            tk.END,
                            f"[{tag}] X: {coord_item['x']}, Y: {coord_item['y']}, Delay: {coord_item['delay']:.2f}s, Click: {coord_item['click_type']}, Trigger: {trigger_text}"
                        )
                        if coord_item.get("missing_monitor"):
                            self.coord_listbox.itemconfig(
                                tk.END, foreground="white", background="#c0392b"
                            )
        self.refresh_coord_color_listbox()
        self.refresh_monitor_status()

    def add_coordinate(self):
        x = self.new_x_var.get()
        y = self.new_y_var.get()
        delay = self.new_delay_var.get()
        click_type = self.click_type_var.get()
        if delay < 0:
            messagebox.showerror("Lỗi", "Delay không thể âm!")
            return
        # Chọn màn cụ thể thì X, Y hiểu là tọa độ TƯƠNG ĐỐI trong màn đó.
        # Để "Tự động" thì X, Y là tọa độ tuyệt đối và app tự suy ra màn.
        mon = self.chosen_monitor()
        if mon is not None:
            x, y = mon.to_absolute(x, y)
        elif self.screens.monitor_at(x, y) is None:
            messagebox.showerror(
                "Lỗi",
                f"Tọa độ ({x}, {y}) không nằm trên màn hình nào.\n"
                "Chọn đúng màn ở ô 'Màn hình' rồi nhập lại tọa độ tương đối.",
            )
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
        self.status_label.config(text="Trạng thái: Chọn tọa độ (nhấn F8 để dừng)", foreground="blue")
        self.preview_window, canvas, offset = self.make_overlay(alpha=0.8)
        self.label_monitors(canvas, offset)
        canvas.create_text(
            10, 10,
            text="Nhấn chuột trái để chọn tọa độ (mọi màn hình), F8 để dừng",
            fill="white", anchor="nw", font=("Arial", 14),
        )
        self.draw_existing_coords(canvas, offset)
        canvas.bind("<Button-1>", self.add_coord_click)
        threading.Thread(target=self.check_cancel_key, daemon=True).start()

    def add_coord_click(self, event):
        if self.is_selecting:
            # Lấy tọa độ của CHÍNH cú click, không đọc vị trí chuột hiện tại:
            # giữa lúc bấm và lúc xử lý, con trỏ có thể đã nhích đi vài pixel
            x, y = event.x_root, event.y_root
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
                # Canvas có gốc tọa độ riêng nên phải trừ đi gốc desktop ảo,
                # không thì chấm đỏ vẽ lệch hẳn sang chỗ khác
                off_x, off_y, _w, _h = self.screens.virtual_bounds()
                canvas = self.preview_window.winfo_children()[0]
                cx, cy = x - off_x, y - off_y
                canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="red")
            messagebox.showinfo("Thành công", f"Đã thêm tọa độ ({x}, {y}) vào hành động '{name}'!")

    def start_recording(self):
        if self.is_running or self.is_selecting or self.is_recording or self.is_picking_trigger_color:
            messagebox.showwarning("Cảnh báo", "Vui lòng dừng chương trình, chế độ chọn hoặc ghi trước!")
            return
        self.is_recording = True
        self.status_label.config(text="Trạng thái: Đang ghi hành vi (nhấn F8 để dừng)", foreground="purple")
        self.preview_window, canvas, offset = self.make_overlay(alpha=0.8)
        self.label_monitors(canvas, offset)
        canvas.create_text(
            10, 10,
            text="Nhấn chuột để ghi hành vi (mọi màn hình), F8 để dừng",
            fill="white", anchor="nw", font=("Arial", 14),
        )
        self.draw_existing_coords(canvas, offset)
        canvas.bind("<Button-1>", lambda e: self.record_click("left", e))
        canvas.bind("<Button-2>", lambda e: self.record_click("middle", e))
        canvas.bind("<Button-3>", lambda e: self.record_click("right", e))
        self.last_click_time = time.time()
        threading.Thread(target=self.check_cancel_key, daemon=True).start()

    def record_click(self, click_type, event=None):
        if self.is_recording:
            if event is not None:
                x, y = event.x_root, event.y_root
            else:
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
                # Canvas có gốc tọa độ riêng nên phải trừ đi gốc desktop ảo,
                # không thì chấm đỏ vẽ lệch hẳn sang chỗ khác
                off_x, off_y, _w, _h = self.screens.virtual_bounds()
                canvas = self.preview_window.winfo_children()[0]
                cx, cy = x - off_x, y - off_y
                canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="red")
            messagebox.showinfo("Thành công", f"Đã ghi tọa độ ({x}, {y}) vào hành động '{name}'!")

    def check_cancel_key(self):
        while self.is_selecting or self.is_recording or self.is_picking_trigger_color:
            if keyboard.is_pressed("f8"):
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
            item = {
                "x": int(coord.get("x", 0)),
                "y": int(coord.get("y", 0)),
                "delay": float(coord.get("delay", 0.1)),
                "click_type": coord.get("click_type", "left"),
                "trigger_colors": trigger_colors,
                "monitor": coord.get("monitor"),
                "rel_x": coord.get("rel_x"),
                "rel_y": coord.get("rel_y"),
            }
            return self.attach_monitor(item)
        if isinstance(coord, (list, tuple)) and len(coord) >= 4:
            return self.attach_monitor({
                "x": int(coord[0]),
                "y": int(coord[1]),
                "delay": float(coord[2]),
                "click_type": coord[3],
                "trigger_colors": [],
                "monitor": None,
                "rel_x": None,
                "rel_y": None,
            })
        return self.attach_monitor({
            "x": 0, "y": 0, "delay": 0.1, "click_type": "left",
            "trigger_colors": [], "monitor": None, "rel_x": None, "rel_y": None,
        })

    def attach_monitor(self, item):
        """Gắn thông tin màn hình cho một tọa độ.

        Cấu hình cũ không có trường monitor thì suy ra từ tọa độ tuyệt đối.
        Cấu hình mới có monitor thì tính lại tọa độ tuyệt đối từ vị trí tương
        đối, để cấu hình vẫn đúng khi màn hình đổi vị trí trong bố cục.
        """
        sig = item.get("monitor")
        if sig and item.get("rel_x") is not None and item.get("rel_y") is not None:
            mon = self.screens.match_signature(sig)
            if mon is None:
                # Màn đã lưu giờ không còn -> đánh dấu hỏng, giữ nguyên tọa độ cũ
                item["missing_monitor"] = True
                return item
            item["x"], item["y"] = mon.to_absolute(int(item["rel_x"]), int(item["rel_y"]))
            item["monitor"] = mon.signature()
            item["missing_monitor"] = False
            return item

        found = self.screens.to_relative(item["x"], item["y"])
        if found is None:
            item["monitor"] = None
            item["rel_x"] = None
            item["rel_y"] = None
            item["missing_monitor"] = True
            return item
        mon, rel_x, rel_y = found
        item["monitor"] = mon.signature()
        item["rel_x"] = rel_x
        item["rel_y"] = rel_y
        item["missing_monitor"] = False
        return item

    def monitor_tag(self, coord_item):
        if coord_item.get("missing_monitor"):
            return "THIẾU MÀN"
        sig = coord_item.get("monitor") or {}
        return "M%s" % sig.get("index", "?")

    def make_overlay(self, alpha=0.8):
        """Dựng lớp phủ trải kín MỌI màn hình.

        Trước đây lớp phủ dựng theo pyautogui.size(), mà hàm đó chỉ biết màn
        chính, nên không thể chọn tọa độ trên màn thứ hai.

        Trả về (cửa sổ, canvas, offset). Canvas có hệ tọa độ riêng bắt đầu từ 0,
        nên muốn vẽ tại điểm (x, y) của hệ app thì phải trừ đi offset.
        """
        vx, vy, vw, vh = self.screens.virtual_bounds()
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", alpha)
        win.geometry("%dx%d+%d+%d" % (vw, vh, vx, vy))
        canvas = tk.Canvas(win, width=vw, height=vh, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        return win, canvas, (vx, vy)

    def draw_existing_coords(self, canvas, offset):
        """Chấm đỏ các tọa độ đã có của hành động đang chọn."""
        off_x, off_y = offset
        key = self.current_key.get()
        name = self.current_action_name.get()
        for action in self.key_actions.get(key, []):
            if action["name"] != name:
                continue
            for coord in action["coords"]:
                item = self.normalize_coord(coord)
                cx, cy = item["x"] - off_x, item["y"] - off_y
                canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill="red")

    def label_monitors(self, canvas, offset):
        """Ghi tên từng màn lên lớp phủ để biết đang trỏ vào màn nào."""
        off_x, off_y = offset
        for mon in self.screens.monitors:
            canvas.create_rectangle(
                mon.x - off_x, mon.y - off_y,
                mon.right - off_x - 1, mon.bottom - off_y - 1,
                outline="#00ff88", width=3,
            )
            canvas.create_text(
                mon.x - off_x + 24, mon.y - off_y + 24,
                text=mon.describe(), fill="#00ff88", anchor="nw",
                font=("Arial", 22, "bold"),
            )

    def update_monitor_menu(self):
        """Đổ lại danh sách màn hình vào ô chọn."""
        menu = self.monitor_menu["menu"]
        menu.delete(0, "end")
        for name in self.monitor_choices():
            menu.add_command(label=name, command=lambda n=name: self.new_monitor_var.set(n))
        if self.new_monitor_var.get() not in self.monitor_choices():
            self.new_monitor_var.set("Tự động")

    def monitor_choices(self):
        return ["Tự động"] + [m.describe() for m in self.screens.monitors]

    # --- vị trí cửa sổ app -----------------------------------------------

    def startup_choices(self):
        return [NHO_VI_TRI_CU] + [m.describe() for m in self.screens.monitors]

    def update_startup_menu(self):
        menu = self.startup_monitor_menu["menu"]
        menu.delete(0, "end")
        for name in self.startup_choices():
            menu.add_command(
                label=name,
                command=lambda n=name: self.chon_man_khoi_dong(n),
            )
        # Khôi phục lựa chọn đã lưu, nếu màn đó vẫn còn
        sig = self.settings.get("startup_monitor")
        mon = self.screens.match_signature(sig) if sig else None
        self.startup_monitor_var.set(mon.describe() if mon else NHO_VI_TRI_CU)

    def chon_man_khoi_dong(self, ten):
        """Người dùng đổi ô 'Mở app tại': lưu ngay và dời cửa sổ luôn cho thấy."""
        self.startup_monitor_var.set(ten)
        mon = next((m for m in self.screens.monitors if m.describe() == ten), None)
        if mon is None:
            self.settings = settings.update(startup_monitor=None)
        else:
            self.settings = settings.update(startup_monitor=mon.signature())
            self.dat_cua_so_vao_man(mon)

    def dat_cua_so_vao_man(self, mon):
        """Đưa cửa sổ chính vào giữa màn hình chỉ định."""
        self.root.update_idletasks()
        w = self.root.winfo_width() or 900
        h = self.root.winfo_height() or 750
        # Cửa sổ to hơn màn thì thu lại cho vừa, còn hơn để tràn ra ngoài
        w = min(w, mon.width)
        h = min(h, mon.height)
        x = mon.x + (mon.width - w) // 2
        y = mon.y + (mon.height - h) // 2
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def khoi_phuc_vi_tri_cua_so(self):
        """Đặt cửa sổ theo thiết lập đã lưu, gọi một lần lúc khởi động."""
        sig = self.settings.get("startup_monitor")
        if sig:
            mon = self.screens.match_signature(sig)
            if mon is not None:
                self.dat_cua_so_vao_man(mon)
                return
            # Màn đã lưu giờ không còn -> rơi về vị trí cũ hoặc mặc định
        vi_tri = self.settings.get("window_pos")
        if not vi_tri:
            return
        try:
            x, y, w, h = (int(vi_tri[k]) for k in ("x", "y", "w", "h"))
        except Exception:
            return
        # Chỉ khôi phục nếu chỗ đó vẫn nằm trên một màn hình nào đó, tránh
        # trường hợp rút màn ra rồi cửa sổ mở tuốt ngoài vùng nhìn thấy.
        if self.screens.monitor_at(x + w // 2, y + h // 2) is None:
            return
        self.root.geometry("%dx%d+%d+%d" % (w, h, x, y))

    def luu_vi_tri_cua_so(self):
        """Ghi lại chỗ cửa sổ đang đứng, gọi lúc thoát."""
        try:
            # Lúc đang chạy auto thì cửa sổ bị ẩn, tọa độ đọc ra không có nghĩa
            if self.root.state() != "normal":
                return
            settings.update(window_pos={
                "x": self.root.winfo_rootx(),
                "y": self.root.winfo_rooty(),
                "w": self.root.winfo_width(),
                "h": self.root.winfo_height(),
            })
        except Exception:
            pass

    def chosen_monitor(self):
        """Màn hình đang chọn trong ô, None nghĩa là để app tự nhận."""
        name = self.new_monitor_var.get()
        for mon in self.screens.monitors:
            if mon.describe() == name:
                return mon
        return None

    def rescan_screens(self, announce=False):
        """Nhận diện lại bố cục màn hình, dùng khi vừa cắm hoặc rút màn."""
        if self.is_running or self.is_selecting or self.is_recording or self.is_picking_trigger_color:
            return
        self.screens.refresh()
        self.update_monitor_menu()
        self.update_startup_menu()
        self.update_coord_listbox()
        if announce:
            chi_tiet = "\n".join(
                "  %s tại (%d, %d)" % (m.describe(), m.x, m.y) for m in self.screens.monitors
            )
            if screens.dpi_ok():
                messagebox.showinfo("Thành công", "Đã nhận diện lại màn hình:\n" + chi_tiet)
            else:
                messagebox.showwarning(
                    "Cảnh báo",
                    "Đã nhận diện lại màn hình:\n" + chi_tiet + "\n\n"
                    "Nhưng Windows không cho khai báo DPI per-monitor cho tiến trình này. "
                    "Trên máy nhiều màn hình đặt scaling khác nhau, tọa độ và màu trên màn "
                    "phụ có thể lệch. Thử đặt mọi màn về cùng một mức scaling.",
                )

    def rescan_screens_announce(self):
        self.rescan_screens(announce=True)

    def missing_monitor_coords(self):
        """Các tọa độ trỏ tới màn hình không còn tồn tại."""
        hong = []
        for key, actions in self.key_actions.items():
            for action in actions:
                for coord in action["coords"]:
                    if self.normalize_coord(coord).get("missing_monitor"):
                        hong.append((key, action["name"]))
                        break
        return hong

    def refresh_monitor_status(self):
        if not hasattr(self, "monitor_status_label"):
            return
        phan = ["%s tại (%d,%d)" % (m.describe(), m.x, m.y) for m in self.screens.monitors]
        text = "Màn hình: " + "  |  ".join(phan)
        mau = "black"
        hong = self.missing_monitor_coords()
        if hong:
            text += "  —  %d hành động có tọa độ thiếu màn hình" % len(hong)
            mau = "red"
        elif not screens.dpi_ok():
            text += "  —  CẢNH BÁO: không khai báo được DPI per-monitor"
            mau = "#b8860b"
        self.monitor_status_label.config(text=text, foreground=mau)

    def canh_bao_dpi_neu_can(self):
        """Báo ngay nếu Windows không cho khai báo DPI per-monitor.

        Không khai báo được thì tọa độ trên màn phụ sẽ lệch, và đó là loại lỗi
        âm thầm nên phải nói rõ chứ không để người dùng tự đoán.
        """
        self.refresh_monitor_status()
        if len(self.screens.monitors) > 1 and not screens.dpi_ok():
            messagebox.showwarning(
                "Cảnh báo",
                "Windows không cho khai báo DPI per-monitor cho tiến trình này.\n\n"
                "Máy anh đang dùng nhiều màn hình, nên tọa độ và màu trên màn phụ "
                "có thể bị lệch.\n\n"
                "Cách khắc phục: đặt mọi màn hình về cùng một mức scaling trong "
                "Windows Settings > Display > Scale.",
            )

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
        self.preview_window, canvas, offset = self.make_overlay(alpha=0.8)
        self.label_monitors(canvas, offset)
        off_x, off_y = offset
        for coord in coords:
            coord_item = self.normalize_coord(coord)
            x, y = coord_item["x"] - off_x, coord_item["y"] - off_y
            canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
            canvas.create_text(
                x + 10, y - 10, text=self.monitor_tag(coord_item),
                fill="#ffd700", anchor="nw", font=("Arial", 11, "bold"),
            )
        canvas.create_text(
            10, 10,
            text=f"Xem trước: {name} (phím {key}) — click bất kỳ đâu để đóng",
            fill="white", anchor="nw", font=("Arial", 14),
        )
        canvas.bind("<Button-1>", lambda e: self.close_preview())

    def close_preview(self):
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None

    # --- bàn phím ---------------------------------------------------------

    def _dong_bo_ten_phim(self, *_args):
        """Chép tên phím sang bản sao thuần Python và ghi nhớ cho lần sau."""
        self._stop_key = chuan_hoa_phim(self.stop_key_var.get()) or self.stop_key_var.get()
        self._pause_key = chuan_hoa_phim(self.pause_key_var.get()) or self.pause_key_var.get()
        self.settings = settings.update(
            stop_key=self._stop_key, pause_key=self._pause_key
        )

    def dang_ky_hook_ban_phim(self):
        """Đăng ký MỘT hook duy nhất, một lần, cho cả vòng đời app.

        Trước đây hook chỉ được đăng ký bên trong auto_click nên phím thoát vô
        tác dụng khi app chưa chạy, và còn một khoảng mù ba giây ngay sau khi
        bấm Bắt đầu. Một hook toàn cục xóa cả hai vấn đề đó, đồng thời tránh
        việc gỡ hook theo tên vốn rất dễ ném lỗi.
        """
        if self._kb_hook is not None:
            return
        self._kb_hook = keyboard.hook(self._on_key_event)

    def _on_key_event(self, e):
        """Chạy trên thread của thư viện keyboard.

        Không được chạm vào Tkinter và không được làm gì nặng ở đây: cả thư
        viện chỉ có một thread xử lý, nghẽn ở đây là mọi phím khác chết theo.
        """
        ten = e.name
        if e.event_type == keyboard.KEY_UP:
            self._keys_down.discard(ten)
            return
        if ten in self._keys_down:
            return                      # giữ phím sinh ra hàng loạt sự kiện, bỏ qua
        self._keys_down.add(ten)

        if self._cap_handle is not None:
            return                      # đang bắt phím để gán, không xử lý gì khác
        if ten == self._stop_key:
            self.quit_app()
        elif ten == self._pause_key:
            self.toggle_pause()
        elif self.is_running and ten in self.key_actions:
            self.current_active_key = ten

    def toggle_pause(self):
        """Bật/tắt tạm dừng. Nhấn lần nữa chính phím đó thì chạy tiếp."""
        if not self.is_running or self.is_quitting:
            return
        with self._pause_lock:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self._resume_evt.clear()
            else:
                self._resume_evt.set()

    def bat_dau_gan_phim(self, bien_dich, nut):
        """Bắt một lần nhấn phím rồi điền tên phím vào ô.

        Dùng keyboard.hook vì nó trả về ngay lập tức. Tuyệt đối không dùng
        read_key/read_event/wait: chúng chặn vĩnh viễn, không hủy được, và sẽ
        treo cứng cả app.
        """
        if self._cap_handle is not None:
            return
        nhan_cu = nut["text"]
        nut.config(text="Đang chờ... (Esc để hủy)")

        def ap_dung(ten):
            self.ket_thuc_gan_phim()
            nut.config(text=nhan_cu)
            if ten:
                bien_dich.set(ten)

        def on_event(e):
            if e.event_type != keyboard.KEY_DOWN:
                return
            if self._cap_handle is None:
                return
            raw = e.name or ""
            ten = None if raw == "esc" else chuan_hoa_phim(raw)
            # Callback chạy trên thread khác, phải đẩy về main thread mới đụng UI
            self.root.after(0, lambda: ap_dung(ten))

        self._cap_handle = keyboard.hook(on_event)
        # Hết giờ mà không bấm gì thì tự hủy, không để nút kẹt mãi
        self._cap_timer = self.root.after(8000, lambda: ap_dung(None))

    def ket_thuc_gan_phim(self):
        h = self._cap_handle
        self._cap_handle = None
        if h is not None:
            try:
                keyboard.unhook(h)
            except (KeyError, ValueError):
                pass
        t = self._cap_timer
        self._cap_timer = None
        if t is not None:
            try:
                self.root.after_cancel(t)
            except Exception:
                pass

    def quit_app(self):
        """Phím dừng: tắt hẳn chương trình, không hiện lại cửa sổ."""
        if self.is_quitting:
            return
        self.is_quitting = True
        self.is_running = False
        # Đánh thức vòng lặp auto để nó thoát ngay, kể cả khi đang tạm dừng
        self._stop_evt.set()
        self._resume_evt.set()
        self.is_paused = False
        self.is_selecting = False
        self.is_recording = False
        self.is_picking_trigger_color = False
        self.current_active_key = None
        # Hàm này chạy trên thread của keyboard, phải đẩy việc đóng UI về main thread
        self.root.after(0, self._shutdown)

    def _shutdown(self):
        self.luu_vi_tri_cua_so()
        # Hủy callback định kỳ trước khi phá cửa sổ, không thì Tcl kêu lỗi
        if getattr(self, "_mouse_after_id", None) is not None:
            try:
                self.root.after_cancel(self._mouse_after_id)
            except Exception:
                pass
            self._mouse_after_id = None
        try:
            keyboard.unhook_all()
        except Exception:
            pass
        if self.preview_window:
            try:
                self.preview_window.destroy()
            except Exception:
                pass
            self.preview_window = None
        try:
            self.root.destroy()
        except Exception:
            pass

    def set_trigger_from_mouse(self):
        x, y = pyautogui.position()
        self.trigger_x_var.set(x)
        self.trigger_y_var.set(y)
        messagebox.showinfo("Thành công", f"Đã đặt điểm trigger tại ({x}, {y})")

    def capture_trigger_color(self):
        try:
            x = self.trigger_x_var.get()
            y = self.trigger_y_var.get()
            r, g, b = self.screens.read_pixel(x, y)
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
        self.status_label.config(text="Trạng thái: Chọn màu trigger (click để lấy, F8 để hủy)", foreground="blue")

        if self.preview_window:
            self.preview_window.destroy()
        self.preview_window, canvas, _offset = self.make_overlay(alpha=0.2)
        canvas.create_text(
            10,
            10,
            text="Di chuyển chuột đến điểm màu cần lấy trên bất kỳ màn nào, click chuột trái để chọn (F8 để hủy)",
            fill="white",
            anchor="nw",
            font=("Arial", 14),
        )
        canvas.bind("<Button-1>", self.pick_trigger_color_click)

        threading.Thread(target=self.check_cancel_key, daemon=True).start()

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
            r, g, b = self.screens.read_pixel(x, y)
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
        # Đang chạy thì dùng bản chụp, vì hàm này được gọi từ thread của vòng
        # lặp auto và đọc biến Tkinter từ đó sẽ treo cứng.
        cfg = self._cfg_trigger if self.is_running else None
        if cfg is None:
            cfg = {
                "enabled": self.color_trigger_enabled_var.get(),
                "x": self.trigger_x_var.get(),
                "y": self.trigger_y_var.get(),
                "rgb": (
                    self.trigger_r_var.get(),
                    self.trigger_g_var.get(),
                    self.trigger_b_var.get(),
                ),
                "tolerance": max(0, min(255, self.color_tolerance_var.get())),
            }
        if not cfg["enabled"]:
            return True
        target = cfg["rgb"]
        tolerance = cfg["tolerance"]
        current = self.screens.read_pixel(cfg["x"], cfg["y"])
        return all(abs(current[i] - target[i]) <= tolerance for i in range(3))

    def is_coord_trigger_matched(self, coord):
        coord_item = self.normalize_coord(coord)
        trigger_colors = coord_item["trigger_colors"]
        if trigger_colors:
            current = self.screens.read_pixel(coord_item["x"], coord_item["y"])
            for trigger in trigger_colors:
                tolerance = max(0, min(255, int(trigger.get("tolerance", 10))))
                if all(abs(current[i] - int(trigger[channel])) <= tolerance for i, channel in enumerate(("r", "g", "b"))):
                    return True
            return False
        return self.is_trigger_color_matched()

    def auto_click(self):
        # Đọc từ bản chụp, KHÔNG đọc biến Tkinter ở đây: hàm này chạy trên
        # thread riêng, mà đọc Tkinter từ thread khác sẽ treo cứng vĩnh viễn.
        click_count = self._cfg_click_count
        random_mode = self._cfg_random

        self._ui(self.root.withdraw)
        self._ui(lambda: self.status_label.config(text="Trạng thái: Đang chạy", foreground="green"))
        self._ngu(3)

        # Hook bàn phím đã đăng ký sẵn từ lúc khởi động, không cần làm gì ở đây

        count = 0
        while self.is_running:
            try:
                # Chốt 1: chỗ duy nhất được phép ngủ dài khi tạm dừng
                if not self._cho_tiep_tuc():
                    break
                # Người dùng đang dùng chuột thì nhường, chờ họ buông ra
                if not self._cho_chuot_ranh():
                    break
                # Thực hiện hành động của phím đang active
                if self.current_active_key and self.current_active_key in self.key_actions:
                    for action in self.key_actions[self.current_active_key]:
                        for coord in action["coords"]:
                            coord_item = self.normalize_coord(coord)
                            x = coord_item["x"]
                            y = coord_item["y"]
                            delay = coord_item["delay"]
                            click_type = coord_item["click_type"]
                            # Chốt 2: phải đứng TRƯỚC lệnh đọc màu, vì đọc màu
                            # tốn hàng chục mili giây nên một hành động dài vẫn
                            # click thêm cả chục phát sau khi đã bấm tạm dừng
                            if not self.is_running or not self._resume_evt.is_set():
                                break
                            # Người dùng vừa chạm chuột thì bỏ dở hành động,
                            # nhường ngay chứ không click nốt cho hết chuỗi
                            if self._nguoi_dung_cham_chuot():
                                break
                            if self.is_coord_trigger_matched(coord_item):
                                pyautogui.click(x, y, button=click_type)
                                self._vi_tri_app_dat = (x, y)
                                self._vi_tri_chuot_cuoi = (x, y)
                            self._ngu(delay)
                        # Chốt 3: giữa hai hành động
                        if not self.is_running or not self._resume_evt.is_set():
                            break

                # Chế độ ngẫu nhiên (nếu bật)
                # Chốt 4: chế độ ngẫu nhiên cũng phải dừng khi tạm dừng
                if random_mode and self.is_running and self._resume_evt.is_set():
                    vx, vy, vw, vh = self.screens.virtual_bounds()
                    coords = [(random.randint(vx, vx + vw), random.randint(vy, vy + vh), 0.1, "left") for _ in range(3)]
                    for x, y, delay, click_type in coords:
                        # Chốt 5
                        if not self.is_running or not self._resume_evt.is_set():
                            break
                        if self._nguoi_dung_cham_chuot():
                            break
                        if self.is_trigger_color_matched():
                            pyautogui.click(x, y, button=click_type)
                            self._vi_tri_app_dat = (x, y)
                            self._vi_tri_chuot_cuoi = (x, y)
                        self._ngu(delay)

                count += 1
                if click_count != 0 and count >= click_count:
                    self.stop_clicking()
                    break

                # Giữ nguyên 0.01s như cũ. Ô "Khoảng thời gian giữa các chu kỳ"
                # vẫn chưa có tác dụng — đó là lỗi có sẵn, chưa sửa ở lần này
                # vì sửa sẽ đổi hẳn nhịp chạy của các cấu hình đang dùng.
                self._ngu(0.01)

            except pyautogui.FailSafeException:
                # Failsafe đã tắt nên nhánh này gần như không bao giờ chạy.
                # Giữ lại cho chắc, nhưng dừng im lặng chứ không hiện hộp thoại.
                self.stop_clicking()
                break
            except Exception as e:
                self.stop_clicking()
                loi = str(e)
                self._ui(lambda: messagebox.showerror("Lỗi", f"Lỗi xảy ra: {loi}"))
                break

        # Đang thoát hẳn thì bỏ qua phần dọn dẹp UI, _shutdown lo phần còn lại
        if self.is_quitting:
            return

        # Hook bàn phím là hook toàn cục, giữ nguyên cho lần chạy sau.
        # Trước đây chỗ này gỡ hook theo tên và rất dễ ném lỗi, làm cửa sổ
        # không bao giờ hiện lại.
        self._ui(self.root.deiconify)
        self._ui(lambda: self.status_label.config(text="Trạng thái: Đã dừng", foreground="red"))

    def _ui(self, fn):
        """Chạy một việc động tới giao diện, luôn trên main thread.

        Vòng lặp auto chạy ở thread riêng. Gọi thẳng Tkinter từ đó sẽ treo cứng
        vĩnh viễn sau khi cửa sổ bị hủy, nên mọi thay đổi giao diện phải đi qua
        đây.
        """
        if self.is_quitting:
            return
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def _nguoi_dung_cham_chuot(self):
        """True nếu người dùng vừa động vào chuột trong vài giây gần đây.

        Con trỏ nhảy vì hai lý do: người dùng di, hoặc chính app click. Phân
        biệt bằng cách so vị trí hiện tại với chỗ app vừa click tới — khác chỗ
        đó nghĩa là do người dùng.
        """
        try:
            pos = tuple(pyautogui.position())
        except Exception:
            return False
        if pos != self._vi_tri_chuot_cuoi:
            self._vi_tri_chuot_cuoi = pos
            if pos != self._vi_tri_app_dat:
                self._luc_chuot_doi = time.time()
        return (time.time() - self._luc_chuot_doi) < GIAY_CHO_CHUOT_RANH

    def _cho_chuot_ranh(self):
        """Đứng chờ tới khi chuột yên đủ lâu. False nghĩa là phải thoát vòng lặp."""
        while self._nguoi_dung_cham_chuot():
            if not self.is_running or self.is_quitting:
                return False
            self._stop_evt.wait(0.1)
        return self.is_running and not self.is_quitting

    def _cho_tiep_tuc(self):
        """Đứng chờ tại đây khi đang tạm dừng. False nghĩa là phải thoát vòng lặp."""
        while not self._resume_evt.is_set():
            if not self.is_running or self.is_quitting:
                return False
            self._resume_evt.wait(0.2)
        return self.is_running and not self.is_quitting

    def _ngu(self, giay):
        """Thay cho time.sleep: tỉnh dậy ngay khi bấm Dừng hoặc Thoát."""
        return not self._stop_evt.wait(giay)

    def start_clicking(self):
        if not self.is_running and not self.is_selecting and not self.is_recording and not self.is_picking_trigger_color:
            try:
                if self.interval_var.get() <= 0:
                    messagebox.showerror("Lỗi", "Khoảng thời gian phải lớn hơn 0!")
                    return
                if self.click_count_var.get() < 0:
                    messagebox.showerror("Lỗi", "Số chu kỳ click không thể âm!")
                    return
                phim_thoat = chuan_hoa_phim(self.stop_key_var.get())
                if phim_thoat is None:
                    messagebox.showerror(
                        "Lỗi",
                        "Phím thoát không hợp lệ.\n"
                        "Ví dụ: page up, page down, f5, home, end, insert, delete, a, 1\n"
                        "(lưu ý: 'pgdn' và 'prior' không dùng được, phải viết 'page down')",
                    )
                    return
                phim_dung = chuan_hoa_phim(self.pause_key_var.get())
                if phim_dung is None:
                    messagebox.showerror("Lỗi", "Phím tạm dừng không hợp lệ.")
                    return
                if phim_dung == phim_thoat:
                    messagebox.showerror("Lỗi", "Phím tạm dừng và phím thoát không được trùng nhau!")
                    return
                if phim_dung in self.key_actions:
                    messagebox.showerror("Lỗi", f"Phím tạm dừng '{phim_dung}' trùng với phím hành động!")
                    return
                self.stop_key_var.set(phim_thoat)
                self.pause_key_var.set(phim_dung)
                if self.color_tolerance_var.get() < 0:
                    messagebox.showerror("Lỗi", "Tolerance màu không thể âm!")
                    return
                if not self.random_mode_var.get() and not any(actions for actions in self.key_actions.values()):
                    messagebox.showerror("Lỗi", "Vui lòng thêm ít nhất một tọa độ hoặc bật chế độ ngẫu nhiên!")
                    return
                if self.stop_key_var.get() in self.key_actions:
                    messagebox.showerror("Lỗi", f"Phím dừng '{self.stop_key_var.get()}' trùng với phím hành động!")
                    return
                hong = self.missing_monitor_coords()
                if hong:
                    danh_sach = "\n".join(f"  - Phím {k}, hành động '{n}'" for k, n in hong)
                    messagebox.showerror(
                        "Lỗi",
                        "Không chạy được vì có tọa độ trỏ tới màn hình không còn tồn tại:\n\n"
                        f"{danh_sach}\n\n"
                        "Cắm lại màn hình đó, hoặc xóa và đặt lại các tọa độ đã tô đỏ.",
                    )
                    return
                # Chụp lại cấu hình ngay tại đây, trên main thread. Vòng lặp
                # auto chạy ở thread riêng và không được phép đọc Tkinter.
                self._cfg_click_count = self.click_count_var.get()
                self._cfg_random = self.random_mode_var.get()
                self._cfg_trigger = {
                    "enabled": self.color_trigger_enabled_var.get(),
                    "x": self.trigger_x_var.get(),
                    "y": self.trigger_y_var.get(),
                    "rgb": (
                        self.trigger_r_var.get(),
                        self.trigger_g_var.get(),
                        self.trigger_b_var.get(),
                    ),
                    "tolerance": max(0, min(255, self.color_tolerance_var.get())),
                }
                # Lấy mốc vị trí chuột ngay bây giờ, nếu không app sẽ tưởng
                # người dùng vừa di chuột và chờ vô cớ hai giây đầu
                try:
                    vt = tuple(pyautogui.position())
                except Exception:
                    vt = None
                self._vi_tri_chuot_cuoi = vt
                self._vi_tri_app_dat = vt
                self._luc_chuot_doi = 0.0

                self.is_running = True
                self.is_paused = False
                self._resume_evt.set()
                self._stop_evt.clear()
                self.thread = threading.Thread(target=self.auto_click, daemon=True)
                self.thread.start()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi xảy ra: {e}")
                self.is_running = False
                self.root.deiconify()

    def stop_clicking(self):
        self.is_running = False
        # Đánh thức mọi giấc ngủ và mọi chỗ đang chờ tạm dừng
        self._stop_evt.set()
        self._resume_evt.set()
        self.is_paused = False
        self.is_selecting = False
        self.is_recording = False
        self.is_picking_trigger_color = False
        self.current_active_key = None

        # Hàm này gọi được từ cả nút bấm lẫn vòng lặp auto ở thread khác,
        # nên phần đụng giao diện phải đi qua _ui
        def _don_giao_dien():
            if self.preview_window:
                self.preview_window.destroy()
                self.preview_window = None
            self.root.deiconify()
            self.status_label.config(text="Trạng thái: Đã dừng", foreground="red")

        self._ui(_don_giao_dien)

    def save_config(self):
        config = {
            "interval": self.interval_var.get(),
            "click_count": self.click_count_var.get(),
            "random_mode": self.random_mode_var.get(),
            "stop_key": self.stop_key_var.get(),
            "pause_key": self.pause_key_var.get(),
            "color_trigger": {
                "enabled": self.color_trigger_enabled_var.get(),
                "x": self.trigger_x_var.get(),
                "y": self.trigger_y_var.get(),
                "r": self.trigger_r_var.get(),
                "g": self.trigger_g_var.get(),
                "b": self.trigger_b_var.get(),
                "tolerance": self.color_tolerance_var.get(),
            },
            # Bố cục màn hình lúc lưu, để khi tải lại còn đối chiếu và báo lệch
            "monitors": [
                {"index": m.index, "x": m.x, "y": m.y, "w": m.width, "h": m.height}
                for m in self.screens.monitors
            ],
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
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Thành công", "Cấu hình Game Maker đã được lưu!")

    def load_config(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.interval_var.set(config.get("interval", 1.0))
            self.click_count_var.set(config.get("click_count", 0))
            self.random_mode_var.set(config.get("random_mode", False))
            # Chuẩn hóa khi tải: cấu hình cũ có thể ghi "pgup" hoặc "Page Up",
            # mà sự kiện bàn phím luôn báo tên chuẩn nên không chuẩn hóa là phím chết
            self.stop_key_var.set(
                chuan_hoa_phim(config.get("stop_key")) or self.stop_key_var.get()
            )
            self.pause_key_var.set(
                chuan_hoa_phim(config.get("pause_key")) or self.pause_key_var.get()
            )
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

            hong = self.missing_monitor_coords()
            if hong:
                da_luu = config.get("monitors") or []
                mo_ta_cu = ", ".join(
                    "Màn %s (%sx%s)" % (m.get("index"), m.get("w"), m.get("h")) for m in da_luu
                ) or "(cấu hình cũ không ghi lại bố cục màn hình)"
                mo_ta_moi = ", ".join(m.describe() for m in self.screens.monitors)
                messagebox.showwarning(
                    "Thiếu màn hình",
                    "Đã tải cấu hình, nhưng có tọa độ trỏ tới màn hình không còn tồn tại.\n\n"
                    f"Bố cục lúc lưu: {mo_ta_cu}\n"
                    f"Bố cục hiện tại: {mo_ta_moi}\n\n"
                    f"{len(hong)} hành động có tọa độ hỏng, đã tô đỏ trong danh sách.\n"
                    "Nút Bắt đầu bị khóa cho tới khi sửa xong.",
                )
            else:
                messagebox.showinfo("Thành công", "Cấu hình Game Maker đã được tải!")

if __name__ == "__main__":
    root = tk.Tk()
    # Chạy bằng pythonw nên không còn console: lỗi trong callback của Tkinter
    # phải hiện ra hộp thoại, không thì nó biến mất không dấu vết
    root.report_callback_exception = _bao_loi
    app = GameMakerApp(root)
    root.mainloop()
