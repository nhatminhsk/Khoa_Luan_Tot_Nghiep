# Tín dụng chính sách — dữ liệu nhập tay

Nhập tay từ thông cáo NHNN, văn bản và BCTC. Kiểm ngày 14/09/2026. Mỗi dòng đều có `source_url`.

| File | Nội dung | Dùng cho mô hình |
|---|---|---|
| `program_participation.csv` | 22 mã × 8 chương trình: có tham gia không (0/1), cam kết (tỷ đồng) nếu có công bố | Biến giả theo ngân hàng, bật từ `list_as_of` |
| `program_rates.csv` | Lãi suất hoặc mức ưu đãi của từng chương trình theo kỳ | Chuỗi thời gian, chỉ có nghĩa khi nhân với biến tham gia |
| `program_aggregates.csv` | Số tổng NHNN công bố (giải ngân, dư nợ) ở một số mốc | Chỉ để mô tả, không theo ngân hàng |
| `disaster_provinces.csv` | Tỉnh trong TT 53/2024 (Yagi, 26 tỉnh cũ, đã quy đổi sang 34 tỉnh mới) và CV 9651/NHNN-TD (22 tỉnh) | Nối với `branch_network/branch_by_province.csv` để đo mức độ ảnh hưởng |
| `bank_reported_items.csv` | Số liệu từng ngân hàng tự công bố: phải thu/phải trả hỗ trợ lãi suất (VCB, EIB), số liệu tự báo cáo, báo chí | Tham khảo; không đủ 22 mã, định nghĩa không đồng nhất |
| `agri_loans_fill_template.csv` | 81 ô cuối năm của dư nợ nông, lâm, thủy sản đọc từ BCTC kiểm toán. Cột `status`: 77 ô đã nhập, 3 ô BCTC không tách dòng (NAB 2019–2021), 1 ô chưa có file (NAB 2018) | **Nguồn sự thật**: sửa ở đây rồi chạy script, đừng sửa thẳng `agri_loans_annual.csv` vì script ghi đè |
| `agri_loans_annual.csv` | Chuỗi năm 22 mã × 2018–2025: BCTC đọc tay được ưu tiên, còn lại lấy vnstock Q4; có tỷ trọng %, nguồn, ghi chú phạm vi | **File nên dùng**, 172/176 ô, chỉ trống NAB 2018–2021 (14/09: lấy 14 ô từ bảng ngành, SHB 2019 và VPB 2024 thay số vnstock bằng số BCTC; 15/09: gộp 16 ô người dùng tự đọc BCTC — BAB 2019–21, LPB 2018–23, OCB 2018, SSB 2018–19, TPB 2018–21, cả 16 ô có tổng khớp tổng dư nợ API) |

## Nhập tay thêm

**Liên kết với bảng ngành:** khi nhập bảng ngành ở `data/credit/loans_by_industry_manual/fill_template.xlsx` rồi chạy `python -m crawlers.loans_by_industry` và `python -m crawlers.agri_loans_manual`, ô "chưa có file" nào có đúng một dòng nhóm A sẽ tự được điền. Ô đã có số thì không bị ghi đè. Mục `agri_differs_from_industry_table` liệt kê ô mà số nông nghiệp khác dòng A của bảng ngành (hiện chỉ SHB 2018, lệch 24 triệu).

Nhập riêng từng ô:

1. Mở `agri_loans_fill_template.csv`, tìm dòng `ticker` + `period` cần điền.
2. Điền `status` = `đã nhập`, hai cột số (đơn vị **triệu đồng**, bỏ dấu chấm), tên dòng, năm BCTC, cột đọc, trang PDF, link.
3. Chạy `python -m crawlers.agri_loans_manual`. Script kiểm lỗi nhập (thiếu số, sai đơn vị, số nông nghiệp lớn hơn tổng, thiếu link) rồi mới ghi vào `agri_loans_annual.csv`, và in cảnh báo gãy chuỗi.

## Lưu ý

- **Dư nợ nông, lâm, thủy sản.** Số của `vnstock` (dòng `NT_BS_AGRICULTURE_AND_FORESTRY`) khớp đúng BCTC kiểm toán: VCB 2024, STB 2025, HDB 2024–2025. Các chỗ gãy chuỗi (HDB 2024-Q4, SHB 2024-Q4, MSB 2024-Q3) nằm **ngay trong BCTC**, do ngân hàng đổi cách phân ngành, không phải lỗi nguồn. Nhập tay không sửa được chỗ gãy này.
- **Trong `agri_loans_fill_template.csv`:** 16/41 file BCTC không có trên static2.vietstock.vn (cột `fs_url` trống) — tải từ trang quan hệ nhà đầu tư của ngân hàng. Cột `column` cho biết đọc cột "Số cuối năm" hay "Số đầu năm".
- **Cách kiểm 46 ô đã nhập (14/09/2026):** đọc trên ảnh trang BCTC. 41 ô khớp đúng chuỗi số trong bản OCR 160 dpi. 7 ô OCR tách chữ số thì phóng to ảnh để đọc lại. Tỷ trọng tính ra khớp cột % in sẵn trong BCTC (BID, CTG, EIB, SSB, STB, TCB, HDB), riêng EIB 2020 lệch 0,01 điểm do ngân hàng làm tròn. OCB ghi đơn vị đồng, đã quy về triệu.
- **Phạm vi dòng không đồng nhất:** ACB ghi "Nông, lâm nghiệp", NVB ghi "Nông nghiệp và lâm nghiệp" (không nêu thủy sản). TCB chỉ phân ngành phần cho vay tổ chức kinh tế, nên tỷ trọng bị đánh giá thấp. CTG 2022 là số đầu năm đã trình bày lại trong BCTC 2023.
- **BCTC kiểm toán 2025 trên Vietstock là ảnh quét.** Đã OCR 18 mã bằng Windows OCR (tiếng Anh, mất dấu nhưng số đọc đúng).

## Không nhập tay được (đã kiểm, không có nguồn công khai)

- Giải ngân hoặc dư nợ của **từng ngân hàng** trong các gói NHNN — NHNN chỉ công bố tổng.
- Số tiền hỗ trợ lãi suất 2% (NĐ 31/2022) và số cấp bù (NĐ 157/2026) theo từng ngân hàng.
- Dư nợ cơ cấu lại theo TT 02/2023, TT 06/2024, TT 53/2024 — 18 BCTC 2025 chỉ nêu chính sách kế toán, không có số tiền.
- Tiền gửi 2% tại NHCSXH của BID, CTG, VCB — không trình bày riêng; chỉ tính được theo quy tắc 2% × tiền gửi VND cuối năm trước.
- Cam kết từng ngân hàng trong gói hạ tầng 500.000 tỷ.
