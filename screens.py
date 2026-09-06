"""Nhận diện bố cục nhiều màn hình và quy đổi tọa độ.

Module này giả định tiến trình đã khai báo DPI ở mức per-monitor (clicker.py
làm việc đó ngay dòng đầu, trước mọi import). Khi đã khai báo, Windows dùng
CHUNG một hệ tọa độ cho mọi thứ app cần: chỗ đặt cửa sổ Tkinter, vị trí con
trỏ chuột, đích của lệnh click, và điểm đọc màu.

Nếu không khai báo, Windows trả về ba hệ tọa độ lệch nhau cho cùng một điểm
trên máy nhiều màn hình có scaling khác nhau. Đó là nguyên nhân khiến tọa độ
chọn trên màn phụ bị trượt. Hàm dpi_ok() bên dưới để app kiểm tra lại và cảnh
báo nếu việc khai báo thất bại.
"""

import ctypes

import pyautogui

user32 = ctypes.windll.user32


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


_ENUM_PROC = ctypes.WINFUNCTYPE(
    ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(_RECT), ctypes.c_double
)


def dpi_ok():
    """True nếu tiến trình đang ở mức DPI per-monitor (mức 2)."""
    try:
        muc = ctypes.c_int()
        ctypes.windll.shcore.GetProcessDpiAwareness(None, ctypes.byref(muc))
        return muc.value == 2
    except Exception:
        return False


class Monitor:
    """Một màn hình, tọa độ theo hệ chung của app."""

    def __init__(self, index, x, y, width, height):
        self.index = index
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    def contains(self, x, y):
        return self.x <= x < self.right and self.y <= y < self.bottom

    def to_relative(self, x, y):
        return x - self.x, y - self.y

    def to_absolute(self, rel_x, rel_y):
        return self.x + rel_x, self.y + rel_y

    def label(self):
        return "M%d" % self.index

    def describe(self):
        return "Màn %d (%dx%d)" % (self.index, self.width, self.height)

    def signature(self):
        """Phần được ghi vào file cấu hình để nhận lại màn này về sau."""
        return {"index": self.index, "w": self.width, "h": self.height}

    def __repr__(self):
        return "<Monitor %d x=%d y=%d %dx%d>" % (
            self.index, self.x, self.y, self.width, self.height,
        )


def detect_monitors():
    """Liệt kê màn hình.

    Thứ tự cố định: màn chính (chứa gốc tọa độ) đứng đầu, các màn còn lại xếp
    từ trên xuống rồi trái sang phải, để số thứ tự không nhảy giữa các lần chạy.
    """
    rects = []

    def _collect(_handle, _hdc, lprect, _data):
        r = lprect.contents
        rects.append((r.left, r.top, r.right, r.bottom))
        return 1

    user32.EnumDisplayMonitors(0, 0, _ENUM_PROC(_collect), 0)

    if not rects:
        # Không enum được thì lùi về màn chính, còn hơn không có gì.
        width, height = pyautogui.size()
        rects = [(0, 0, int(width), int(height))]

    def _order(rect):
        left, top, right, bottom = rect
        is_primary = left <= 0 < right and top <= 0 < bottom
        return (0 if is_primary else 1, top, left)

    rects.sort(key=_order)
    return [
        Monitor(i + 1, left, top, right - left, bottom - top)
        for i, (left, top, right, bottom) in enumerate(rects)
    ]


class ScreenLayout:
    """Bố cục màn hình hiện tại."""

    def __init__(self):
        self.monitors = detect_monitors()

    def refresh(self):
        self.monitors = detect_monitors()

    # --- tra cứu ---------------------------------------------------------

    def monitor_at(self, x, y):
        for mon in self.monitors:
            if mon.contains(x, y):
                return mon
        return None

    def by_index(self, index):
        for mon in self.monitors:
            if mon.index == index:
                return mon
        return None

    def match_signature(self, sig):
        """Tìm lại màn hình từ thông tin đã lưu trong file cấu hình.

        Khớp theo kích thước trước vì số thứ tự có thể đổi khi cắm rút màn.
        Chỉ khi kích thước không phân biệt được mới xét tới số thứ tự.
        """
        if not sig:
            return None
        want_w, want_h = sig.get("w"), sig.get("h")
        same_size = [m for m in self.monitors if m.width == want_w and m.height == want_h]
        if len(same_size) == 1:
            return same_size[0]
        for mon in same_size:
            if mon.index == sig.get("index"):
                return mon
        return same_size[0] if same_size else None

    def virtual_bounds(self):
        """Khung bao trọn mọi màn hình, dùng để dựng overlay phủ toàn desktop."""
        left = min(m.x for m in self.monitors)
        top = min(m.y for m in self.monitors)
        right = max(m.right for m in self.monitors)
        bottom = max(m.bottom for m in self.monitors)
        return left, top, right - left, bottom - top

    # --- quy đổi tọa độ --------------------------------------------------

    def to_relative(self, x, y):
        """(x, y) tuyệt đối -> (màn, x tương đối, y tương đối). None nếu ngoài màn."""
        mon = self.monitor_at(x, y)
        if mon is None:
            return None
        rel_x, rel_y = mon.to_relative(x, y)
        return mon, rel_x, rel_y

    # --- đọc màu ---------------------------------------------------------

    def read_pixel(self, x, y):
        """Đọc màu tại (x, y).

        Đã khai báo DPI per-monitor nên hệ đọc màu trùng hệ click, không cần
        quy đổi gì. Gom vào đây một chỗ để nếu sau này phải xử lý khác thì chỉ
        sửa một nơi.
        """
        return tuple(pyautogui.pixel(int(x), int(y)))
