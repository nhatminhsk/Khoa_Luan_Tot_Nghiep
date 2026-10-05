package vn.kltn.bankadvisor.common.mail;

/** Tiện ích cho địa chỉ email. */
public final class EmailAddresses {

    private EmailAddresses() {
    }

    /** Che bớt địa chỉ khi ghi log: {@code an.nguyen@example.test} → {@code an***@example.test}. */
    public static String mask(String email) {
        if (email == null) {
            return "(trống)";
        }
        int at = email.indexOf('@');
        if (at <= 0) {
            return "***";
        }
        return email.substring(0, Math.min(2, at)) + "***" + email.substring(at);
    }
}
