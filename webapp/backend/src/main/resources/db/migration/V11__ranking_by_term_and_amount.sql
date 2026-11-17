-- Xếp hạng tổng hợp (MCDM × Monte Carlo, serving/rankings.py) có từ 03/11/2026. Mỗi lần chạy xếp nhiều bảng:
--   - gửi: mỗi kỳ hạn × kênh, ở trọng số mặc định (amount_vnd NULL) và theo mức tiền gửi (amount_vnd = mốc tiền):
--     trọng số an toàn nhân phần tiền không được bảo hiểm tiền gửi chi trả (uninsured_share), safety_weight là trọng số
--     nhóm an toàn tại tâm sau khi nhân;
--   - vay: một bảng (term_months, channel, amount_vnd NULL).
-- p_top1, p_top3: tần suất đứng đầu / lọt top 3 trong mô phỏng (trung bình 4 thuật toán), không phải xác suất.
-- rates_as_of: ngày lãi gửi (YYYY-MM-DD) hoặc tháng lãi vay (YYYY-MM) của ảnh chụp đã xếp.
ALTER TABLE ranking_result DROP CONSTRAINT uq_ranking_result;
ALTER TABLE ranking_result ADD COLUMN term_months INTEGER;
ALTER TABLE ranking_result ADD COLUMN channel VARCHAR(8);
ALTER TABLE ranking_result ADD COLUMN amount_vnd BIGINT;
ALTER TABLE ranking_result ADD COLUMN p_top1 DOUBLE PRECISION;
ALTER TABLE ranking_result ADD COLUMN p_top3 DOUBLE PRECISION;
ALTER TABLE ranking_result ADD COLUMN rates_as_of VARCHAR(10);
ALTER TABLE ranking_result ADD COLUMN uninsured_share DOUBLE PRECISION;
ALTER TABLE ranking_result ADD COLUMN safety_weight DOUBLE PRECISION;
ALTER TABLE ranking_result ALTER COLUMN method_version SET DATA TYPE VARCHAR(80);
CREATE INDEX ix_ranking_result_lookup ON ranking_result (purpose, as_of_period, term_months, channel, amount_vnd);
