"""Thiết lập riêng của máy, tự lưu và tự nạp.

Khác với file cấu hình tọa độ (phải bấm Lưu / Tải thủ công), đây là những lựa
chọn thuộc về chỗ ngồi làm việc chứ không thuộc về kịch bản click: mở app ở màn
nào, cửa sổ nằm đâu. Nên nó tự ghi và tự đọc, không hỏi gì người dùng.

File nằm cạnh clicker.py. Hỏng hay thiếu thì coi như chưa có thiết lập, không
bao giờ làm app chết chỉ vì đọc được nửa file.
"""

import json
import os

TEN_FILE = "app_settings.json"


def _duong_dan():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), TEN_FILE)


def load():
    """Đọc thiết lập. File thiếu hoặc hỏng thì trả về dict rỗng."""
    try:
        with open(_duong_dan(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save(data):
    """Ghi thiết lập. Ghi hỏng cũng không được làm app dừng."""
    try:
        with open(_duong_dan(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False


def update(**thay_doi):
    """Sửa vài khóa rồi ghi lại, giữ nguyên các khóa khác."""
    data = load()
    data.update(thay_doi)
    save(data)
    return data
