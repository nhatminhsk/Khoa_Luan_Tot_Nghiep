-- Gửi thông báo qua email.
--
-- 1. Người dùng phải xác minh email trước khi chọn kênh EMAIL: đăng ký không kiểm tra email, nên nếu không
--    xác minh thì ai cũng có thể dùng hệ thống gửi thư tới địa chỉ của người khác.
-- 2. Bảng notification kiêm hàng đợi gửi (outbox): thông báo luôn lưu trong ứng dụng; email là bản sao gửi
--    sau, nên máy chủ thư lỗi không làm mất thông báo.

ALTER TABLE app_user ADD COLUMN email_verified_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE app_user ADD COLUMN email_verification_sent_at TIMESTAMP WITH TIME ZONE;

-- Chưa ai xác minh email, nên không ai được ở kênh EMAIL.
UPDATE app_user SET notify_channel = 'IN_APP' WHERE notify_channel = 'EMAIL';

-- email_status: NULL = chỉ trong ứng dụng; PENDING = chờ gửi; SENT = đã gửi;
-- FAILED = hết số lần thử; SKIPPED = không gửi nữa (đã đọc trong ứng dụng hoặc đã tắt email trước khi gửi).
ALTER TABLE notification ADD COLUMN email_status VARCHAR(12);
ALTER TABLE notification ADD COLUMN email_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE notification ADD COLUMN email_next_attempt_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE notification ADD COLUMN email_last_error VARCHAR(500);
ALTER TABLE notification ADD COLUMN emailed_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX ix_notification_email_status ON notification (email_status, email_next_attempt_at);
