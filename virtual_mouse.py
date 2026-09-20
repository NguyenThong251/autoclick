"""Chuột ảo: click và đọc màu thẳng vào cửa sổ đích, không đụng tới con trỏ thật.

Windows chỉ có duy nhất MỘT con trỏ chuột, không tạo thêm được nếu không viết
driver. Nên "chuột ảo" ở đây làm theo cách khác: thay vì dời con trỏ rồi bấm,
app gửi thẳng message chuột vào cửa sổ đích. Con trỏ thật không nhúc nhích một
pixel, nên người dùng vẫn dùng chuột bình thường trong lúc auto đang chạy.

Cùng một lý do đó, màu trigger cũng không được đọc từ màn hình nữa: cửa sổ đích
có thể đang bị cửa sổ khác che, đọc màn hình sẽ ra màu của cửa sổ nằm đè lên.
Thay vào đó app bảo chính cửa sổ đích tự vẽ lại vào một bitmap riêng
(PrintWindow) rồi đọc màu từ bitmap đó.

Giới hạn phải biết trước, không lách được:
  - App đích phải xử lý chuột theo kiểu message cổ điển. Thứ nào đọc Raw Input
    hay DirectInput (đa số game 3D, game có anti-cheat) sẽ bỏ qua hoàn toàn.
  - Cửa sổ bị che hoặc nằm sau thì chụp được. Cửa sổ THU NHỎ thì phần lớn app
    không vẽ ra gì, chụp về một mảng đen -> trigger màu sai.

Module giả định tiến trình đã khai báo DPI per-monitor (clicker.py làm ngay
dòng đầu). Nhờ vậy tọa độ cửa sổ, tọa độ chuột và tọa độ click dùng chung một
hệ, giống hệt screens.py.
"""

import ctypes
import os
import threading
import time
from ctypes import wintypes

# Dùng instance riêng chứ không dùng ctypes.windll.user32: windll là bộ nhớ đệm
# dùng chung cả tiến trình, đặt argtypes lên đó sẽ ảnh hưởng tới screens.py.
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
except Exception:
    dwmapi = None

_NUT = {
    # tên nút -> (message nhấn, message nhả, cờ wParam lúc đang giữ)
    "left": (0x0201, 0x0202, 0x0001),
    "right": (0x0204, 0x0205, 0x0002),
    "middle": (0x0207, 0x0208, 0x0010),
}

GA_ROOT = 2
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002
CWP_SKIPTRANSPARENT = 0x0004
PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0
BI_RGB = 0
DWMWA_CLOAKED = 14
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Giữ nút bao lâu trước khi nhả.
#
# Để 0: nhấn xong nhả ngay. Khoảng giữ càng lâu thì cửa sổ đích càng lâu giữ
# quyền bắt chuột, mà trong lúc nó giữ thì chuột THẬT của người dùng bị cuốn
# theo và thao tác không ăn. Đo thật với Chrome, 10 cú click mỗi giây:
#   giữ 30ms -> cửa sổ đích chiếm chuột khoảng 1/4 thời gian
#   giữ 10ms -> còn khoảng 1/10
#   giữ  0ms -> không đo được lần nào, mà vẫn nhận đủ 40/40 cú click
#
# Đánh đổi: app nào đòi nút phải được giữ một khoảng thật mới tính là click thì
# sẽ bỏ qua. Gặp app như vậy thì nâng số này lên, ví dụ 0.01.
GIU_NUT = 0.0

# Ảnh chụp cửa sổ sống được bao lâu trước khi phải chụp lại. PrintWindow bắt
# cửa sổ vẽ lại nên khá tốn; không đệm thì một hành động mười tọa độ sẽ bắt cửa
# sổ vẽ lại mười lần. 50ms đủ ngắn để màu vẫn coi là hiện tại.
TTL_ANH = 0.05


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG), ("top", wintypes.LONG),
        ("right", wintypes.LONG), ("bottom", wintypes.LONG),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.RealChildWindowFromPoint.argtypes = [wintypes.HWND, POINT]
user32.RealChildWindowFromPoint.restype = wintypes.HWND
user32.ChildWindowFromPointEx.argtypes = [wintypes.HWND, POINT, wintypes.UINT]
user32.ChildWindowFromPointEx.restype = wintypes.HWND
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowDC.argtypes = [wintypes.HWND]
user32.GetWindowDC.restype = wintypes.HDC
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.GetDIBits.argtypes = [
    wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
    ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(BITMAPINFO), wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int

# Phải khai báo argtypes cho MỌI hàm nhận handle. Không khai báo thì ctypes gói
# tham số vào c_int 32 bit, mà trên Windows 64 bit handle và lParam đều rộng
# hơn thế — lỗi kiểu này im lặng và rất khó lần ra.
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
]
if dwmapi is not None:
    dwmapi.DwmGetWindowAttribute.argtypes = [
        wintypes.HWND, wintypes.DWORD, ctypes.POINTER(ctypes.c_int), wintypes.DWORD,
    ]


# --- tra cứu cửa sổ ------------------------------------------------------


def _ten_lop(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _tieu_de(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def _pid(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _ten_exe(hwnd):
    """Tên file exe của tiến trình sở hữu cửa sổ, rỗng nếu không hỏi được."""
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, _pid(hwnd))
    if not h:
        return ""
    try:
        size = wintypes.DWORD(1024)
        buf = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return ""
        return os.path.basename(buf.value)
    finally:
        kernel32.CloseHandle(h)


def _bi_an_kieu_dwm(hwnd):
    """True nếu cửa sổ bị DWM giấu (app UWP đang treo, tab ảo...).

    Loại này vẫn 'visible' theo user32 nhưng không có mặt trên màn, gặp nó mà
    coi là cửa sổ đích thì click rơi vào hư không.
    """
    if dwmapi is None:
        return False
    val = ctypes.c_int(0)
    try:
        if dwmapi.DwmGetWindowAttribute(
            wintypes.HWND(hwnd), DWMWA_CLOAKED, ctypes.byref(val), ctypes.sizeof(val)
        ) == 0:
            return val.value != 0
    except Exception:
        pass
    return False


def window_rect(hwnd):
    """Khung cửa sổ theo hệ tọa độ toàn desktop, None nếu hỏi không được."""
    r = RECT()
    if not user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(r)):
        return None
    return r.left, r.top, r.right, r.bottom


def is_minimized(hwnd):
    return bool(user32.IsIconic(wintypes.HWND(hwnd)))


def is_alive(hwnd):
    return bool(hwnd) and bool(user32.IsWindow(wintypes.HWND(hwnd)))


def root_of(hwnd):
    return user32.GetAncestor(wintypes.HWND(hwnd), GA_ROOT) or hwnd


def top_level_windows():
    """Cửa sổ gốc đang hiện, xếp theo thứ tự Z từ trên xuống."""
    ket_qua = []

    def _thu(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and not _bi_an_kieu_dwm(hwnd):
            ket_qua.append(hwnd)
        return True

    user32.EnumWindows(_WNDENUMPROC(_thu), 0)
    return ket_qua


def window_at(x, y, bo_qua_pid=None):
    """Cửa sổ gốc nằm trên cùng tại điểm (x, y).

    Phải tự duyệt theo thứ tự Z chứ không dùng thẳng WindowFromPoint, vì lúc
    người dùng chọn tọa độ thì lớp phủ của chính app đang trùm lên tất cả và
    WindowFromPoint sẽ chỉ trả về cái lớp phủ đó. bo_qua_pid để loại trừ tiến
    trình của chính mình.
    """
    x, y = int(x), int(y)
    for hwnd in top_level_windows():
        if bo_qua_pid is not None and _pid(hwnd) == bo_qua_pid:
            continue
        if is_minimized(hwnd):
            continue
        rect = window_rect(hwnd)
        if rect is None:
            continue
        left, top, right, bottom = rect
        if left <= x < right and top <= y < bottom:
            return hwnd
    # Duyệt Z không ra thì thử cách thường, còn hơn không có gì
    hwnd = user32.WindowFromPoint(POINT(x, y))
    return root_of(hwnd) if hwnd else None


def child_at(root, x, y):
    """Cửa sổ con sâu nhất TRONG cây của root tại điểm (x, y).

    Đi xuống từ root chứ không từ điểm trên màn hình, nên cửa sổ khác đang nằm
    đè lên cũng không ảnh hưởng. Đây mới là chỗ thật sự nhận message chuột.
    """
    hwnd = root
    for _ in range(16):     # chặn vòng lặp vô hạn nếu cây cửa sổ dị thường
        p = POINT(int(x), int(y))
        if not user32.ScreenToClient(wintypes.HWND(hwnd), ctypes.byref(p)):
            break
        con = user32.RealChildWindowFromPoint(wintypes.HWND(hwnd), p)
        if con and con != hwnd and _xuyen_thau(con):
            # Cửa sổ con xuyên thấu (WS_EX_TRANSPARENT) thì chuột thật bấm xuyên
            # qua nó, không bao giờ tới nó. RealChildWindowFromPoint lại không bỏ
            # qua loại này. Chrome là ví dụ điển hình: lớp "Intermediate D3D
            # Window" để vẽ hình phủ kín cửa sổ, gửi click vào đó là bị lờ đi.
            # Chỉ đổi cách tìm khi gặp đúng trường hợp này, để giữ nguyên cách xử
            # lý khung nhóm (group box) của RealChildWindowFromPoint cho app thường.
            con = user32.ChildWindowFromPointEx(
                wintypes.HWND(hwnd), p,
                CWP_SKIPINVISIBLE | CWP_SKIPDISABLED | CWP_SKIPTRANSPARENT,
            )
        if not con or con == hwnd:
            break
        hwnd = con
    return hwnd


def _xuyen_thau(hwnd):
    """True nếu cửa sổ để chuột bấm xuyên qua (cờ WS_EX_TRANSPARENT)."""
    try:
        return bool(user32.GetWindowLongPtrW(wintypes.HWND(hwnd), GWL_EXSTYLE) & WS_EX_TRANSPARENT)
    except Exception:
        return False


# --- nhận lại cửa sổ sau khi mở lại app ----------------------------------


def signature(hwnd):
    """Thông tin ghi vào file cấu hình để nhận lại cửa sổ này lần sau."""
    root = root_of(hwnd)
    return {
        "exe": _ten_exe(root),
        "class": _ten_lop(root),
        "title": _tieu_de(root),
    }


def describe(sig):
    if not sig:
        return "(chưa gắn cửa sổ)"
    ten = sig.get("title") or sig.get("class") or "?"
    exe = sig.get("exe") or "?"
    if len(ten) > 40:
        ten = ten[:39] + "…"
    return "%s — %s" % (exe, ten)


def find_window(sig):
    """Tìm lại cửa sổ từ thông tin đã lưu, None nếu không còn.

    Khớp theo exe + tên lớp trước, vì tiêu đề rất hay đổi (đổi tab, đổi file
    đang mở). Tiêu đề chỉ dùng để phân biệt khi có nhiều cửa sổ cùng loại.
    """
    if not sig:
        return None
    exe = (sig.get("exe") or "").lower()
    lop = sig.get("class") or ""
    tieu_de = sig.get("title") or ""
    if not exe and not lop:
        # Chữ ký rỗng thì khớp với mọi cửa sổ, thà không tìm thấy còn hơn trả
        # bừa một cửa sổ rồi click vào nhầm app
        return None

    ung_vien = []
    for hwnd in top_level_windows():
        if lop and _ten_lop(hwnd) != lop:
            continue
        if exe and _ten_exe(hwnd).lower() != exe:
            continue
        ung_vien.append(hwnd)
    if not ung_vien:
        return None
    for hwnd in ung_vien:
        if _tieu_de(hwnd) == tieu_de:
            return hwnd
    return ung_vien[0]


# --- gửi click -----------------------------------------------------------


def _lparam(x, y):
    """Gói tọa độ client thành lParam. Mỗi chiều là số 16 bit có dấu."""
    return ((int(y) & 0xFFFF) << 16) | (int(x) & 0xFFFF)


def click(hwnd, x, y, button="left", giu=GIU_NUT):
    """Gửi một cú click vào cửa sổ, (x, y) là tọa độ toàn desktop.

    Dùng PostMessage chứ không SendMessage: SendMessage đứng chờ cửa sổ đích xử
    lý xong mới trả về, gặp app đang bận là treo luôn cả vòng lặp auto.

    Trả về True nếu đã gửi được. Gửi được KHÔNG có nghĩa app đích chịu nhận —
    app đọc Raw Input sẽ lặng lẽ bỏ qua.
    """
    bo_msg = _NUT.get(button)
    if bo_msg is None or not is_alive(hwnd):
        return False
    nhan, nha, co_giu = bo_msg

    dich = child_at(hwnd, x, y)
    p = POINT(int(x), int(y))
    if not user32.ScreenToClient(wintypes.HWND(dich), ctypes.byref(p)):
        return False
    lp = _lparam(p.x, p.y)

    # KHÔNG gửi WM_MOUSEMOVE trước khi bấm. Gửi thì cửa sổ đích tưởng con trỏ
    # vừa dời tới đó và đổi hình con trỏ theo, trong khi con trỏ thật đang nằm
    # chỗ khác trong cùng cửa sổ — thành ra nó nhấp nháy đổi qua lại liên tục.
    # Đo thật với Chrome: có WM_MOUSEMOVE thì 31 cú click làm con trỏ đổi hình
    # 62 lần; bỏ đi thì 0 lần mà vẫn nhận đủ 31 cú.
    user32.PostMessageW(wintypes.HWND(dich), nhan, co_giu, lp)
    if giu > 0:
        time.sleep(giu)
    user32.PostMessageW(wintypes.HWND(dich), nha, 0, lp)
    return True


# --- chụp cửa sổ và đọc màu ---------------------------------------------

_khoa_anh = threading.Lock()
_anh = {}       # hwnd -> [luc_chup, hdc_mem, hbitmap, left, top, w, h]


def _xoa_anh(entry):
    _luc, hdc_mem, hbmp, _l, _t, _w, _h = entry
    if hbmp:
        gdi32.DeleteObject(hbmp)
    if hdc_mem:
        gdi32.DeleteDC(hdc_mem)


def invalidate(hwnd=None):
    """Bỏ ảnh đã đệm. Không truyền gì thì bỏ hết.

    Gọi lúc bắt đầu một lần chạy, và lúc dừng, để không đọc nhầm ảnh cũ và
    không giữ handle GDI lâu hơn cần thiết.
    """
    with _khoa_anh:
        if hwnd is None:
            for entry in _anh.values():
                _xoa_anh(entry)
            _anh.clear()
        elif hwnd in _anh:
            _xoa_anh(_anh.pop(hwnd))


def _chup(hwnd):
    """Chụp cửa sổ vào bitmap trong bộ nhớ, dùng lại ảnh cũ nếu còn hạn.

    Trả về entry trong _anh, hoặc None nếu chụp hỏng. Gọi trong _khoa_anh.
    """
    bay_gio = time.time()
    cu = _anh.get(hwnd)
    if cu is not None and bay_gio - cu[0] < TTL_ANH:
        return cu
    if cu is not None:
        _xoa_anh(_anh.pop(hwnd))

    if not is_alive(hwnd) or is_minimized(hwnd):
        return None
    rect = window_rect(hwnd)
    if rect is None:
        return None
    left, top, right, bottom = rect
    w, h = right - left, bottom - top
    if w <= 0 or h <= 0:
        return None

    hdc_win = user32.GetWindowDC(wintypes.HWND(hwnd))
    if not hdc_win:
        return None
    hdc_mem = hbmp = None
    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
        if not hdc_mem or not hbmp:
            raise OSError("không tạo được bitmap")
        cu_bmp = gdi32.SelectObject(hdc_mem, hbmp)
        # Cờ RENDERFULLCONTENT là thứ bắt buộc với app vẽ bằng GPU (trình
        # duyệt, Electron, app UWP); thiếu nó chụp về khung trắng. Máy quá cũ
        # không hiểu cờ này thì lùi về cách chụp thường.
        ok = user32.PrintWindow(wintypes.HWND(hwnd), hdc_mem, PW_RENDERFULLCONTENT)
        if not ok:
            ok = user32.PrintWindow(wintypes.HWND(hwnd), hdc_mem, 0)
        # Bỏ bitmap ra khỏi DC: GetDIBits không đọc được bitmap đang được chọn
        gdi32.SelectObject(hdc_mem, cu_bmp)
        if not ok:
            raise OSError("PrintWindow thất bại")
    except Exception:
        if hbmp:
            gdi32.DeleteObject(hbmp)
        if hdc_mem:
            gdi32.DeleteDC(hdc_mem)
        return None
    finally:
        user32.ReleaseDC(wintypes.HWND(hwnd), hdc_win)

    entry = [bay_gio, hdc_mem, hbmp, left, top, w, h]
    _anh[hwnd] = entry
    return entry


def read_pixel(hwnd, x, y):
    """Màu tại (x, y) đọc từ chính cửa sổ, không phải từ màn hình.

    Nhờ vậy cửa sổ bị che vẫn cho màu đúng. Trả về (r, g, b), hoặc None nếu
    không chụp được hoặc điểm nằm ngoài cửa sổ.
    """
    with _khoa_anh:
        entry = _chup(hwnd)
        if entry is None:
            return None
        _luc, hdc_mem, hbmp, left, top, w, h = entry
        rx, ry = int(x) - left, int(y) - top
        if not (0 <= rx < w and 0 <= ry < h):
            return None

        # Chỉ lấy đúng một dòng quét chứ không kéo cả ảnh về: cửa sổ 4K là 33MB
        # mỗi lần, mà vòng lặp auto có thể đọc màu vài trăm lần một giây.
        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = h        # dương = ảnh xếp từ dưới lên
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB
        dong = (ctypes.c_ubyte * (w * 4))()
        lay = gdi32.GetDIBits(
            hdc_mem, hbmp, h - 1 - ry, 1, dong, ctypes.byref(bmi), DIB_RGB_COLORS
        )
        if lay != 1:
            return None
        off = rx * 4
        return (dong[off + 2], dong[off + 1], dong[off])     # bitmap xếp B, G, R


# --- dò thử --------------------------------------------------------------


def probe(x, y, bo_qua_pid=None):
    """Xem tại điểm (x, y) có gì, dùng cho nút kiểm tra tương thích.

    Trả về dict mô tả cửa sổ, có chụp được không, và màu đọc được — đủ để biết
    chuột ảo có dùng được với app đó hay không mà không phải chạy thật.
    """
    hwnd = window_at(x, y, bo_qua_pid=bo_qua_pid)
    if not hwnd:
        return {"ok": False, "ly_do": "Không có cửa sổ nào tại điểm này."}
    sig = signature(hwnd)
    rect = window_rect(hwnd) or (0, 0, 0, 0)
    try:
        mau = read_pixel(hwnd, x, y)
    finally:
        # Dò là việc một lần, đừng giữ bitmap và handle GDI lại làm gì
        invalidate(hwnd)
    return {
        "ok": mau is not None,
        "hwnd": hwnd,
        "sig": sig,
        "mo_ta": describe(sig),
        "rect": rect,
        "con": _ten_lop(child_at(hwnd, x, y)),
        "mau": mau,
        "thu_nho": is_minimized(hwnd),
        "ly_do": "" if mau is not None else (
            "Cửa sổ đang thu nhỏ nên không vẽ ra gì để chụp."
            if is_minimized(hwnd) else
            "Không chụp được nội dung cửa sổ (PrintWindow thất bại)."
        ),
    }
