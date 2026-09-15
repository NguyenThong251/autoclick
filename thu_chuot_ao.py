"""Thử riêng phần chuột ảo, chạy bằng console, không cần giao diện.

Mục đích là tách phần dễ hỏng (ctypes gọi Win32) ra khỏi phần giao diện, để khi
hỏng thì thấy ngay traceback thật chứ không phải một hộp thoại cụt.

Chạy:  python thu_chuot_ao.py

Chỉ cần Python, không cần pyautogui / keyboard / tkinter, cũng không cần venv.
"""

import ctypes
import os
import sys
import time

# Phải khai báo DPI per-monitor TRƯỚC khi nạp virtual_mouse, y như clicker.py
# làm. Không khai báo thì trên máy nhiều màn scaling khác nhau, tọa độ chuột và
# tọa độ cửa sổ nằm ở hai hệ khác nhau và mọi con số dưới đây đều lệch.
def _khai_bao_dpi():
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)):
            return True
    except Exception:
        pass
    try:
        return ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0
    except Exception:
        return False


if not hasattr(ctypes, "windll"):
    sys.exit("Script này chỉ chạy trên Windows.")

DPI_OK = _khai_bao_dpi()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import virtual_mouse as vm
except Exception:
    import traceback
    print("Nạp virtual_mouse.py thất bại:\n")
    traceback.print_exc()
    sys.exit(1)


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def vi_tri_chuot():
    p = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def dem_nguoc(giay=5):
    for i in range(giay, 0, -1):
        print("   %d..." % i, end="\r", flush=True)
        time.sleep(1)
    print("            ", end="\r")


def mot_luot():
    print("\nĐưa chuột tới chỗ muốn thử (trên màn nào cũng được), giữ yên ở đó.")
    dem_nguoc(5)

    x, y = vi_tri_chuot()
    print("Điểm thử: (%d, %d)" % (x, y))

    kq = vm.probe(x, y, bo_qua_pid=os.getpid())
    if not kq.get("hwnd"):
        print("  KHÔNG thấy cửa sổ nào ở đó: %s" % kq.get("ly_do"))
        return

    sig = kq["sig"]
    print("  Cửa sổ      : %s" % (sig.get("title") or "(không tiêu đề)"))
    print("  Tiến trình  : %s" % (sig.get("exe") or "?"))
    print("  Lớp cửa sổ  : %s" % (sig.get("class") or "?"))
    print("  Ô nhận click: %s" % (kq.get("con") or "?"))
    print("  Khung       : (%d, %d) - (%d, %d)" % tuple(kq["rect"]))
    print("  Thu nhỏ     : %s" % ("CÓ" if kq.get("thu_nho") else "không"))

    if kq["ok"]:
        print("  Chụp cửa sổ : ĐƯỢC, màu tại điểm đó là RGB%s" % (kq["mau"],))
    else:
        print("  Chụp cửa sổ : HỎNG — %s" % kq.get("ly_do"))

    # Tìm lại cửa sổ từ chữ ký: đây là đường mà app dùng sau khi mở lại
    tim_lai = vm.find_window(sig)
    print("  Tìm lại từ chữ ký: %s"
          % ("được" if tim_lai else "KHÔNG ĐƯỢC — cấu hình lưu ra sẽ không nhận lại được cửa sổ"))

    tra_loi = input("\n  Bắn thử một cú click trái vào đó? [y/N] ").strip().lower()
    if tra_loi == "y":
        print("  Đừng động vào chuột. Con trỏ KHÔNG được phép nhúc nhích.")
        truoc = vi_tri_chuot()
        gui_duoc = vm.click(kq["hwnd"], x, y, "left")
        time.sleep(0.3)
        sau = vi_tri_chuot()
        print("  Gửi message : %s" % ("được" if gui_duoc else "THẤT BẠI"))
        print("  Con trỏ     : %s"
              % ("đứng yên, đúng như mong đợi" if truoc == sau
                 else "ĐÃ DỜI %s -> %s, sai rồi" % (truoc, sau)))
        print("  Giờ nhìn sang app đích xem nó có ăn cú click đó không.")


def main():
    print("=" * 62)
    print("Thử chuột ảo")
    print("=" * 62)
    print("DPI per-monitor: %s" % ("đã khai báo" if DPI_OK else "KHÔNG khai báo được — tọa độ màn phụ sẽ lệch"))
    so_man = len(vm.top_level_windows())
    print("Cửa sổ gốc đang mở: %d" % so_man)

    while True:
        try:
            mot_luot()
        except Exception:
            import traceback
            print("\nLỖI:")
            traceback.print_exc()
        if input("\nThử điểm khác? [y/N] ").strip().lower() != "y":
            break


if __name__ == "__main__":
    main()
