-- V1 đặt repayment VARCHAR(12), nhưng RepaymentMethod.DECLINING_BALANCE dài 17 ký tự: lưu nhu cầu vay với cách trả
-- mặc định (gốc đều, lãi giảm dần) bị H2 báo "Value too long" → lỗi 500. Nới lên 20 cho cùng cỡ với loan_purpose.
-- SET DATA TYPE chạy được cả trên H2 lẫn PostgreSQL.
ALTER TABLE saved_need ALTER COLUMN repayment SET DATA TYPE VARCHAR(20);
