-- Mã xác minh 6 số gửi kèm link xác minh. Người dùng đọc email trên điện thoại rồi nhập mã trên máy đang dùng
-- BankAdvisor; không cần mở link (khi chạy trên máy cá nhân, link localhost không mở được từ điện thoại).
-- Chỉ lưu băm của mã (BCrypt); sai quá số lần cho phép thì mã bị hủy.
ALTER TABLE app_user ADD COLUMN email_verification_code_hash VARCHAR(100);
ALTER TABLE app_user ADD COLUMN email_verification_code_expires_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE app_user ADD COLUMN email_verification_code_attempts INTEGER NOT NULL DEFAULT 0;
