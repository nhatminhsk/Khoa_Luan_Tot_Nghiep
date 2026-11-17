package vn.kltn.bankadvisor.module.user.entity;

/**
 * Quyền theo chức năng. Vai trò → tập quyền khai báo ở {@link Role}; {@code SecurityConfig} kiểm theo quyền chứ không
 * theo tên vai trò, nên ma trận phân quyền đọc được ở một chỗ.
 * <p>
 * Khách (chưa đăng nhập) không có quyền nào: chỉ dùng các API công khai (dashboard, tra cứu, công cụ tính, gợi ý).
 */
public enum Permission {

    /** Lưu nhu cầu, theo dõi ngân hàng, đọc thông báo, đổi email, đăng xuất mọi thiết bị — chỉ dữ liệu của chính mình. */
    PERSONAL_DATA,

    /** Nạp dữ liệu, xem nhật ký nạp. */
    DATA_MANAGE,

    /** Xem danh sách người dùng, khóa / mở tài khoản, đổi vai trò, thu hồi phiên. */
    USER_MANAGE,

    /** Hàng đợi email thông báo. */
    EMAIL_MANAGE;

    /** Tên quyền trong Spring Security (khác tiền tố {@code ROLE_} của vai trò). */
    public String authority() {
        return "PERM_" + name();
    }
}
