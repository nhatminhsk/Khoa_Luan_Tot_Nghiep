package vn.kltn.bankadvisor.common.mail;

import org.springframework.web.util.HtmlUtils;

/**
 * Khung HTML chung cho email: một cột rộng tối đa 560px, style viết inline (trình đọc thư bỏ thẻ style).
 * Dữ liệu động phải đi qua {@link #escape(String)} hoặc các hàm dựng sẵn ở đây.
 */
public final class EmailLayout {

    private static final String TEXT = "#1f2937";
    private static final String MUTED = "#6b7280";
    private static final String BRAND = "#1d4ed8";

    private EmailLayout() {
    }

    public static String escape(String value) {
        return value == null ? "" : HtmlUtils.htmlEscape(value, "UTF-8");
    }

    public static String paragraph(String text) {
        return "<p style=\"margin:0 0 16px;font-size:15px;line-height:1.6;color:" + TEXT + "\">" + escape(text) + "</p>";
    }

    public static String muted(String text) {
        return "<p style=\"margin:0 0 8px;font-size:13px;line-height:1.5;color:" + MUTED + "\">" + escape(text) + "</p>";
    }

    public static String button(String href, String label) {
        return "<p style=\"margin:8px 0 24px\"><a href=\"" + escape(href) + "\" style=\"display:inline-block;padding:12px 20px;"
                + "background:" + BRAND + ";color:#ffffff;text-decoration:none;border-radius:8px;font-weight:600;font-size:15px\">"
                + escape(label) + "</a></p>";
    }

    /** Mã xác minh chữ to, cách chữ, dễ đọc trên điện thoại. */
    public static String code(String code) {
        return "<p style=\"margin:0 0 12px\"><span style=\"display:inline-block;padding:12px 20px;border:1px solid #e5e7eb;"
                + "border-radius:8px;background:#f9fafb;font-family:Consolas,Menlo,monospace;font-size:28px;font-weight:700;"
                + "letter-spacing:6px;color:" + TEXT + "\">" + escape(code) + "</span></p>";
    }

    public static String link(String href, String label) {
        return "<a href=\"" + escape(href) + "\" style=\"color:" + BRAND + "\">" + escape(label) + "</a>";
    }

    /** Một mục thông báo: tiêu đề đậm, nội dung, thời gian. */
    public static String item(String title, String body, String time) {
        return "<div style=\"margin:0 0 16px;padding:12px 16px;border:1px solid #e5e7eb;border-radius:8px\">"
                + "<div style=\"font-size:15px;font-weight:600;color:" + TEXT + "\">" + escape(title) + "</div>"
                + "<div style=\"margin-top:4px;font-size:14px;line-height:1.55;color:" + TEXT + "\">" + escape(body) + "</div>"
                + "<div style=\"margin-top:6px;font-size:12px;color:" + MUTED + "\">" + escape(time) + "</div>"
                + "</div>";
    }

    /**
     * @param contentHtml phần thân đã dựng bằng các hàm trên
     * @param footerHtml  chân thư (lý do nhận thư, cách tắt)
     */
    public static String page(String contentHtml, String footerHtml) {
        return "<!DOCTYPE html><html lang=\"vi\"><head><meta charset=\"UTF-8\">"
                + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"></head>"
                + "<body style=\"margin:0;padding:24px 12px;background:#f3f4f6;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif\">"
                + "<div style=\"max-width:560px;margin:0 auto;background:#ffffff;border-radius:12px;padding:28px 24px\">"
                + "<div style=\"font-size:18px;font-weight:700;color:" + BRAND + ";margin-bottom:20px\">BankAdvisor</div>"
                + contentHtml
                + "<hr style=\"border:none;border-top:1px solid #e5e7eb;margin:24px 0 16px\">"
                + footerHtml
                + "</div></body></html>";
    }
}
