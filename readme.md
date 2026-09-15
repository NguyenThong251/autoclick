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

Click thẳng vào cửa sổ đích mà không đụng tới con trỏ thật, nên vừa auto vừa
dùng máy bình thường được.

Windows chỉ có duy nhất một con trỏ chuột và không tạo thêm được nếu không viết
driver. Nên chế độ này không tạo con trỏ thứ hai, mà gửi thẳng message chuột
vào cửa sổ đích.

**Cách dùng:**

- Chọn tọa độ bằng "Chọn bằng chuột" (hoặc "Ghi hành động"), click thẳng lên
  app đích. Mỗi tọa độ tự nhớ cửa sổ nằm dưới cú click đó — lúc ấy là lúc duy
  nhất biết chắc đó đúng là app anh nhắm tới.
- Tích "Bật chuột ảo" rồi bấm Bắt đầu. Danh sách tọa độ hiện tên app mỗi tọa độ
  sẽ click vào, ví dụ `[M1 · chrome.exe]`.
- Tọa độ nhập tay bằng "Thêm tọa độ" không biết cửa sổ nào, danh sách ghi
  `CHƯA GẮN CỬA SỔ` và nút Bắt đầu khóa lại. Xóa rồi chọn lại bằng chuột.
- Muốn đổi app đích cho một tọa độ thì xóa rồi chọn lại.

App **không bao giờ tự đoán cửa sổ** cho tọa độ có sẵn. Đoán theo cửa sổ đang
nằm trên cùng là sai: lúc tích ô, thứ nằm trên cùng thường là app vừa dùng
xong, còn nền desktop luôn phủ kín màn hình nên điểm nào cũng "có cửa sổ".

Tọa độ bám theo cửa sổ: kéo cửa sổ đi chỗ khác thì tọa độ đi theo. Cửa sổ đóng
thì tọa độ bị tô đỏ và nút Bắt đầu khóa lại.

Bỏ tích thì quay về chuột thật và click **đúng chỗ đã chọn trên màn hình**,
không bám theo cửa sổ nào.

**Giới hạn, không lách được:**

- App đích phải xử lý chuột theo kiểu message cổ điển. Thứ nào đọc Raw Input
  hoặc DirectInput (đa số game 3D, game có anti-cheat) sẽ bỏ qua hoàn toàn.
- Cửa sổ bị che hoặc nằm sau thì đọc màu vẫn đúng, vì màu đọc thẳng từ cửa sổ
  chứ không từ màn hình. Nhưng cửa sổ **thu nhỏ** thì không: phần lớn app không
  vẽ ra gì khi đã minimize.
- Không đọc được màu thì app không click, chứ không lùi về đọc màn hình — lúc
  đó màn hình đang là cửa sổ nằm đè lên, lấy màu app khác rồi click bừa còn tệ
  hơn đứng im. Cuối lần chạy app báo có bao nhiêu lần như vậy.

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
