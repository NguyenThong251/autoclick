# Game Maker — Auto click

Công cụ auto click cho Windows. Ghi sẵn chuỗi tọa độ theo từng phím, lúc chạy
bấm phím nào thì lặp chuỗi của phím đó. Hỗ trợ nhiều màn hình và trigger theo
màu.

## Cài đặt và chạy (Windows)

| File | Việc |
| --- | --- |
| `caidat.bat` | Tạo venv và cài thư viện từ `requirements.txt`. Chạy một lần. |
| `chay.bat` | Chạy app, không có cửa sổ console. |
| `debug.bat` | Chạy app **có console** để đọc traceback. Dùng khi test. |
| `thu.bat` | Thử riêng phần chuột ảo, không dính giao diện. |

`chay.bat` và `debug.bat` tự gọi `caidat.bat` nếu chưa có venv, nên bấm thẳng
cái nào cũng được.

Làm tay:

    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    python clicker.py

Nội dung các file `.bat` viết không dấu là cố ý: console Windows mặc định không
phải UTF-8, để tiếng Việt có dấu vào là vỡ font.

## Phím

| Phím | Việc |
| --- | --- |
| `Page Up` | Thoát hẳn chương trình |
| `Page Down` | Tạm dừng / chạy tiếp |
| `F8` | Hủy chế độ chọn tọa độ, ghi hành động, hoặc lấy màu |

Đổi được phím thoát và phím tạm dừng ngay trong app, app nhớ cho lần sau.

## Color trigger

Chỉ click khi màu tại một điểm khớp với màu đã đặt.

- Bật "Bật click theo nhận diện màu"
- Chọn điểm trigger bằng nút "Lấy tọa độ trigger từ chuột"
- Bấm "Lấy màu tại trigger" để đặt RGB mục tiêu
- Chỉnh tolerance để nới độ lệch màu

Mỗi tọa độ cũng gán riêng được nhiều màu trigger, khớp màu nào cũng click.
Tọa độ có màu riêng thì màu riêng thắng, không dùng trigger chung nữa.

## Chuột ảo (click ngầm)

Click vào một **điểm cố định trên màn hình** mà không đụng tới con trỏ thật,
nên vừa auto vừa dùng máy bình thường được.

Windows chỉ có duy nhất một con trỏ chuột và không tạo thêm được nếu không viết
driver. Nên chế độ này không tạo con trỏ thứ hai, mà gửi thẳng message chuột
vào cửa sổ đang nằm tại điểm đó.

**Tọa độ là điểm trên màn hình, không gắn vào app nào.** Kéo một cửa sổ đi chỗ
khác thì điểm click vẫn đứng nguyên; lúc đó app click vào thứ đang nằm ở đấy,
y như chuột thật bấm xuống. Bật hay tắt chuột ảo cũng cùng một điểm.

**Cách dùng:**

- Chọn tọa độ như bình thường, bằng "Chọn bằng chuột", "Ghi hành động" hoặc
  nhập tay X/Y.
- Tích "Bật chuột ảo" rồi bấm Bắt đầu.

**Giới hạn, không lách được:**

- App đích phải xử lý chuột theo kiểu message cổ điển. Thứ nào đọc Raw Input
  hoặc DirectInput (đa số game 3D, game có anti-cheat) sẽ bỏ qua hoàn toàn.
- App nào đòi nút chuột phải được giữ một khoảng thật mới tính là click cũng bỏ
  qua. Gặp trường hợp đó thì nâng `GIU_NUT` trong `virtual_mouse.py` lên, ví dụ
  `0.01`. Để `0` là để cửa sổ đích khỏi chiếm chuột thật của người dùng.
- Cửa sổ đích bị app khác che thì click rơi vào app đang che, đúng như chuột
  thật. Muốn click trúng thì để cửa sổ đích hở ra.
- Màu trigger đọc từ màn hình, nên cũng theo đúng thứ đang hiện ở điểm đó.

## Các file

| File | Việc |
| --- | --- |
| `clicker.py` | Toàn bộ giao diện và vòng lặp auto |
| `screens.py` | Nhận diện nhiều màn hình, quy đổi tọa độ |
| `virtual_mouse.py` | Chuột ảo: gửi click và chụp cửa sổ qua Win32 |
| `settings.py` | Thiết lập theo máy, tự lưu tự nạp |
| `thu_chuot_ao.py` | Script console thử riêng chuột ảo |

Cấu hình tọa độ lưu / tải thủ công ra file JSON. Riêng thiết lập theo chỗ ngồi
(màn khởi động, vị trí cửa sổ, phím tắt, bật chuột ảo) thì tự ghi vào
`app_settings.json`, không hỏi gì.
