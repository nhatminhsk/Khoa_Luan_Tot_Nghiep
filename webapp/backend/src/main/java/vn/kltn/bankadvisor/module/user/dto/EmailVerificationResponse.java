package vn.kltn.bankadvisor.module.user.dto;

import java.time.Instant;

/**
 * Trạng thái xác minh email của người đang đăng nhập.
 *
 * @param sentAt             lần gửi email xác minh gần nhất (null nếu chưa gửi)
 * @param resendAvailableAt  thời điểm được gửi lại (null nếu gửi được ngay hoặc đã xác minh)
 * @param codeExpiresAt      hạn của mã 6 số đang còn hiệu lực (null nếu không có mã)
 */
public record EmailVerificationResponse(String email, boolean verified, Instant sentAt, Instant resendAvailableAt,
                                        Instant codeExpiresAt) {
}
