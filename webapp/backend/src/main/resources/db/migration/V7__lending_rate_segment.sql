-- Lãi cho vay bình quân giờ lấy từ web từng ngân hàng (Chỉ thị 01/CT-NHNN), VietnamNet chỉ còn để lấp chỗ trống.
-- Mỗi ngân hàng công bố một nhóm khách hàng khác nhau nên phải ghi kèm số thuộc nhóm nào:
--   segment: INDIVIDUAL (khách hàng cá nhân) | ALL (số chung) | UNSPECIFIED (báo không ghi nhóm)
--   basis:   NEW_LOANS (khoản vay mới trong kỳ) | OUTSTANDING (toàn bộ dư nợ) | NULL (ngân hàng không ghi)
--   source:  BANK (web ngân hàng) | VIETNAMNET
ALTER TABLE lending_rate ADD COLUMN segment VARCHAR(16);
ALTER TABLE lending_rate ADD COLUMN basis VARCHAR(16);
ALTER TABLE lending_rate ADD COLUMN source VARCHAR(16);

-- Buộc nạp lại lending_rates.csv ở lần nạp tới: nếu backend cũ đã nạp file mới (bỏ qua ba cột trên) thì checksum
-- trùng và bộ nạp sẽ bỏ qua, ba cột mới trống mãi.
UPDATE import_run SET checksum = NULL WHERE dataset = 'lending_rates';
