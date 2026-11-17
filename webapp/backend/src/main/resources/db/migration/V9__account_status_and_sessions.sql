-- Phân quyền rõ ràng (29/10/2026):
--   status        ACTIVE / LOCKED — quản trị viên khóa tài khoản thì không đăng nhập được nữa;
--   token_version tăng khi khóa, đổi vai trò hoặc "đăng xuất mọi thiết bị": mọi JWT đã cấp (mang số cũ) hết hiệu lực ngay
--                 ở request kế tiếp, vì backend đối chiếu số này với CSDL ở mỗi request cần đăng nhập;
--   last_login_at hiện ở trang quản lý người dùng.
-- JWT phát trước bản này không có số phiên bản nên bị coi là đã thu hồi: người đang đăng nhập phải đăng nhập lại một lần.

ALTER TABLE app_user ADD COLUMN status VARCHAR(12) DEFAULT 'ACTIVE' NOT NULL;
ALTER TABLE app_user ADD COLUMN token_version INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE app_user ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE app_user ADD CONSTRAINT ck_app_user_role CHECK (role IN ('USER', 'ADMIN'));
ALTER TABLE app_user ADD CONSTRAINT ck_app_user_status CHECK (status IN ('ACTIVE', 'LOCKED'));
ALTER TABLE app_user ADD CONSTRAINT ck_app_user_token_version CHECK (token_version >= 0);
