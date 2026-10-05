package vn.kltn.bankadvisor.module.user.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.Instant;

/**
 * Tài khoản người dùng kèm cài đặt thông báo. Không lưu dữ liệu tài chính cá nhân (thu nhập, số dư,
 * khoản vay đang có, tài khoản ngân hàng, giấy tờ tùy thân) — đúng phạm vi đề tài.
 */
@Entity
@Table(name = "app_user")
public class AppUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "email", nullable = false, unique = true)
    private String email;

    @Column(name = "password_hash", nullable = false)
    private String passwordHash;

    @Column(name = "display_name", nullable = false)
    private String displayName;

    @Enumerated(EnumType.STRING)
    @Column(name = "role", nullable = false)
    private Role role;

    @Column(name = "notify_rate_change", nullable = false)
    private boolean notifyRateChange = true;

    @Column(name = "notify_new_ranking", nullable = false)
    private boolean notifyNewRanking = true;

    @Enumerated(EnumType.STRING)
    @Column(name = "notify_channel", nullable = false)
    private NotifyChannel notifyChannel = NotifyChannel.IN_APP;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    /** Thời điểm xác minh email; null = chưa xác minh, chưa được chọn kênh EMAIL. */
    @Column(name = "email_verified_at")
    private Instant emailVerifiedAt;

    /** Lần gửi link xác minh gần nhất, để giới hạn tần suất gửi lại. */
    @Column(name = "email_verification_sent_at")
    private Instant emailVerificationSentAt;

    /** Băm BCrypt của mã xác minh 6 số đang còn hiệu lực (null = không có mã). */
    @Column(name = "email_verification_code_hash")
    private String verificationCodeHash;

    @Column(name = "email_verification_code_expires_at")
    private Instant verificationCodeExpiresAt;

    /** Số lần nhập sai mã hiện tại. */
    @Column(name = "email_verification_code_attempts", nullable = false)
    private int verificationCodeAttempts;

    protected AppUser() {
    }

    public static AppUser create(String email, String passwordHash, String displayName, Role role, Instant now) {
        AppUser user = new AppUser();
        user.email = email;
        user.passwordHash = passwordHash;
        user.displayName = displayName;
        user.role = role;
        user.createdAt = now;
        return user;
    }

    public void updateNotificationSettings(boolean rateChange, boolean newRanking, NotifyChannel channel) {
        this.notifyRateChange = rateChange;
        this.notifyNewRanking = newRanking;
        this.notifyChannel = channel;
    }

    /**
     * Đổi email đăng nhập. Địa chỉ mới chưa được chứng minh là của người dùng, nên bỏ trạng thái đã xác minh và
     * đưa kênh thông báo về trong ứng dụng; link xác minh cũ không còn dùng được (token gắn với email cũ).
     */
    public void changeEmail(String newEmail) {
        this.email = newEmail;
        this.emailVerifiedAt = null;
        this.emailVerificationSentAt = null;
        clearVerificationCode();
        if (notifyChannel == NotifyChannel.EMAIL) {
            notifyChannel = NotifyChannel.IN_APP;
        }
    }

    public void markEmailVerified(Instant now) {
        if (emailVerifiedAt == null) {
            emailVerifiedAt = now;
        }
        clearVerificationCode();
    }

    /** Mã mới thay mã cũ và đặt lại số lần nhập sai. */
    public void issueVerificationCode(String codeHash, Instant expiresAt) {
        this.verificationCodeHash = codeHash;
        this.verificationCodeExpiresAt = expiresAt;
        this.verificationCodeAttempts = 0;
    }

    /** Ghi một lần nhập sai; trả số lần còn được thử (0 = mã đã bị hủy). */
    public int recordWrongVerificationCode(int maxAttempts) {
        verificationCodeAttempts++;
        int remaining = Math.max(0, maxAttempts - verificationCodeAttempts);
        if (remaining == 0) {
            clearVerificationCode();
        }
        return remaining;
    }

    public void clearVerificationCode() {
        verificationCodeHash = null;
        verificationCodeExpiresAt = null;
        verificationCodeAttempts = 0;
    }

    /** Có mã còn hiệu lực tại thời điểm {@code now}. */
    public boolean hasActiveVerificationCode(Instant now) {
        return verificationCodeHash != null && verificationCodeExpiresAt != null && verificationCodeExpiresAt.isAfter(now);
    }

    public void recordVerificationSent(Instant now) {
        emailVerificationSentAt = now;
    }

    public boolean isEmailVerified() {
        return emailVerifiedAt != null;
    }

    /** Thông báo mới của người này có được gửi thêm qua email không. */
    public boolean wantsEmail() {
        return notifyChannel == NotifyChannel.EMAIL && isEmailVerified();
    }

    public Long getId() {
        return id;
    }

    public String getEmail() {
        return email;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public String getDisplayName() {
        return displayName;
    }

    public Role getRole() {
        return role;
    }

    public boolean isNotifyRateChange() {
        return notifyRateChange;
    }

    public boolean isNotifyNewRanking() {
        return notifyNewRanking;
    }

    public NotifyChannel getNotifyChannel() {
        return notifyChannel;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getEmailVerifiedAt() {
        return emailVerifiedAt;
    }

    public Instant getEmailVerificationSentAt() {
        return emailVerificationSentAt;
    }

    public String getVerificationCodeHash() {
        return verificationCodeHash;
    }

    public Instant getVerificationCodeExpiresAt() {
        return verificationCodeExpiresAt;
    }
}
