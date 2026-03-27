# Hướng Dẫn sử dụng phần mềm MedFabric

MedFabric là phần mềm sử dụng cho ghi nhãn từ ảnh CT của bệnh nhân, từ đó hỗ trợ chẩn đoán đột quỵ thiếu máu qua điểm ASPECTS.

Hiện tại, trọng tâm của MedFabric tập trung vào xác định các lát cắt:

- Vùng đồi thị - hạch nền (Basal Ganglia)
- Lát cắt trên hạch nền (Corona Radiata)

Hiện tại, MedFabric hỗ trợ nhập những nhãn sau:

- Các nhãn về chất lượng bộ ảnh:
  - **Irrelevant**: Ảnh không liên quan đến yêu cầu xác định
  - **Low Quality**: Ảnh có chất lượng kém hoặc không thể nhìn được

- Các nhãn cho từng bức ảnh:
  - None: Ảnh không có giá trị trong chấm điểm ASPECTS
  - **BasalGanglia (Cortex)**: Ảnh của vỏ não dưới vùng Đồi thị - Hạch nền
  - **BasalGanglia (Central)**: Ảnh của não vùng đồi thị - Hạch nền
  - **CoronaRadiata**: Lát cắt trên hạch nền

- Chấm điểm: Mỗi ảnh sau khi đã có nhãn vùng sẽ được chấm điểm ASPECTS tương ứng:
  - Các bức ảnh **BasalGanglia (Cortex)** sẽ được chấm điểm từ 0-3 mỗi bán cầu não
  - Các bức ảnh **BasalGanglia (Central)** sẽ được chấm điểm từ 0-4 mỗi bán cầu não
  - Các bức ảnh **CoronaRadiata** sẽ được chấm điểm từ 0-3

## Hướng dẫn bằng hình ảnh

### Bước 1. Đăng nhập

- Vui lòng nhập tên đăng nhập (Username) và mật khẩu (Password):

![alt text](images/image.png)

- Nếu chưa có username và password, vui lòng đăng kí (Lưu ý, mật khẩu cần có 8 kí tự trở lên) và quay lại đăng nhập:

![alt text](images/image-1.png)

### Bước 2. Chọn bộ ảnh

- Tại bảng chọn bộ ảnh (Dashboard), từ trên xuống dưới, từ trái sang phải có:
  - Thanh trạng thái về số bộ ảnh mà tài khoản đã ghi nhãn trước.
  - Bảng tất cả các bộ ảnh CT trong cơ sở dữ liệu, trong đó:
    - Scan Type: mã của bộ ảnh CT, bao gồm loại ảnh CT và mã định danh bộ ảnh
    - Patient ID: mã định danh của bệnh nhân của bộ ảnh
    - Number of images: Số lượng lát cắt trong bộ ảnh
    - Evaluated: Cho biết bộ ảnh này đã được tài khoản hiện tại ghi nhãn chưa
    - Evaluate: chọn ảnh để ghi nhãn tại phiên này. Vui lòng chọn đúng ô vào đúng bức ảnh để chọn bộ ảnh.

![alt text](images/Login_Screen.png)
Giao diện khi chọn

- Các tùy chỉnh khác:
  - Sắp xếp (Sorting): Bằng cách nhấp vào tiêu đề từng cột, có thể sắp xếp bảng theo thứ tự tăng/giảm dần: Đưa các ảnh đã ghi nhãn lên trước hoặc ra sau; Số lượng lát cắt lớn đến nhỏ,...

- Sau khi chọn những bộ ảnh sẽ được ghi nhãn ở phiên này, chọn Evaluate Selected Scans

### Bước 3: ghi nhãn bộ ảnh

- Bảng điều khiển được chia làm ba phần: Xem ảnh, điều khiển và ghi nhãn ảnh và điều khiển bộ ảnh.

- Phần điều khiển ảnh (Image Navigation) gồm hai phần: Chọn ảnh và đánh nhãn ảnh.
  - Phần điều khiển ảnh có 1 thanh chọn, có thể kéo giữ hoặc nhấn chọn ảnh. Previous: Ảnh trước, Next: Ảnh sau
  - Mỗi ảnh có phần đánh giá riêng (Current Image Evaluation):
    - Region: Phân loại khu vực ảnh, mặc định là None (cả hai ô đều không được lựa chọn)
    - Nếu được chọn loại ảnh (Basal Ganglia hoặc Corona Radiata), sẽ hiên ra ô chấm điểm tương ứng: Basal Ganglia (Cortex) từ 0-3, Basal Ganglia (Central) từ 0-4, Corona Radiata từ 0-3

- Phần điều khiển bộ ảnh gồm bốn phần: Thông tin bộ ảnh, thông tin bệnh nhân, ý kiến các nhãn sẵn có và đánh giá bộ ảnh:
  - Thông tin bộ ảnh bao gồm:
    - Số thứ tự bộ ảnh của phiên này **Current Set**
    - Định danh bệnh nhân: **Patient ID**
    - Định danh và loại bộ ảnh: **Scan Type**
  - Nút chọn bộ ảnh: bộ ảnh trước: **Previous Set**, bộ ảnh tiếp: **Next Set**
  - Trạng thái bộ ảnh: Ghi lại số ảnh Basal Ganglia (Cortex), Basal Ganglia (Central), Corona Radiata và trạng thái:
  - COMPLETED: Đã hoàn thành: Khi ảnh đã có đủ các ô chấm điểm đúng yêu cầu
  - INCOMPLETED: Chưa hoàn thành
  - Tại tab All Set Status, có
  - Đánh giá ảnh **Image Set Evaluation** có hai ô: Bộ ảnh không liên quan **Irrelevant Data** và chất lượng thấp **Low Quality**
    - Notes: Các thông tin thêm người dùng có thể ghi chú về bộ ảnh
  - All Image Set Statuses: Trạng thái của toàn bộ các bộ ảnh. Khi tất cả các bộ ảnh Hợp lệ/Đánh dấu xong.

- Các quy tắc khi ghi nhãn:
  - Một bộ ảnh được coi là Đánh dấu xong khi:
    - Trong bộ ảnh có **ít nhất** 1 bức ảnh đánh dấu là **BasalGanglia(Cortex)**, **Basal Ganglia(Cantral) và 1 bức ảnh đánh dấu là CoronaRadiata và **tất cả** các bức ảnh đó đều được đánh dấu điểm
    - Hoặc bộ ảnh được đánh nhãn **Irrelevant** hoặc **Low Quality**
  - Hiện tại, ở mỗi phiên nhập, cần nhập tất cả các bộ ảnh đã chọn (Khi đó hiện lên nút **Submit All Evaluations**) để  lưu dữ liệu về cơ sở dữ liệu.

- Một số lưu ý:
  - Cảnh báo khi ảnh không liên tục: Hệ thống sẽ cảnh báo nếu như bộ ảnh lưu nhãn không liền nhau, để tránh người dùng bỏ sót vùng cần lưu nhãn

- Hình ảnh:

![alt text](images/Label_1.png)
hình ảnh ban đầu, bộ ảnh chưa được ghi nhãn

![alt text](images/Set_Label.png)
nếu bộ ảnh được đánh giá Irrelevant, không thể chấm vùng và điểm cho các ảnh thuộc bộ đó

![alt text](images/Valid_Set.png)
sau khi chọn vùng, sẽ hiện ra ô nhập điểm, vui lòng nhập điểm tương ứng

![alt text](images/Submission.png)
Khi tất cả bộ ảnh đã hợp lệ, Submit Evaluation để lưu dữ liệu vào cơ sở dữ liệu

### Các tính năng đang phát triển

Latest Update: v2.2.0

- Tính năng lưu nháp, lưu những bộ ảnh đã đánh dấu trong phiên khi các bộ khác chưa được ghi nhãn.
- Nhập điểm tương ứng từng vùng: C, L, IC, I, M1-M6
- Xem ảnh ở nhiều window CT khác nhau.

### MedFabric 2.2.0. Viết bởi Nguyễn Đức Hùng - iBME Lab, HUST
