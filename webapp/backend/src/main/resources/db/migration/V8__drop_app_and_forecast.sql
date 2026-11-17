-- CSDL chỉ giữ thứ hệ thống gợi ý dùng (người dùng chốt 29/10/2026).
--   - Điểm / đánh giá ứng dụng ngân hàng: bỏ khỏi phạm vi 26–27/10, không còn màn hình nào đọc.
--   - Dự báo chỉ tiêu 1–4 quý: không vào xếp hạng, ngoài lõi gợi ý; bảng chưa từng có dữ liệu.
-- Dữ liệu gốc của phần ứng dụng vẫn còn ở data/app_reviews/ của pipeline, nên xóa bảng không mất gì không dựng lại được.

DROP TABLE app_aspect_score;
DROP TABLE app_review_monthly;
DROP TABLE app_store_snapshot;
DROP TABLE forecast_point;

ALTER TABLE bank DROP COLUMN app_name;

-- Nhật ký nạp và danh mục nguồn của các bộ dữ liệu đã bỏ: trang Phương pháp / Quản trị không liệt kê nữa.
DELETE FROM import_run WHERE dataset IN ('app_store', 'app_reviews_monthly', 'app_aspects', 'forecasts');
DELETE FROM dataset_info WHERE dataset IN ('app_store', 'app_reviews_monthly', 'app_aspects', 'forecasts');
