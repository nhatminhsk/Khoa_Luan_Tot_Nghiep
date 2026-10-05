package vn.kltn.bankadvisor.common.mail;

/**
 * Một email cần gửi. Luôn có bản chữ thường ({@code text}) cho trình đọc thư không hiện HTML.
 *
 * @param to      địa chỉ người nhận
 * @param subject tiêu đề
 * @param text    nội dung dạng chữ thường
 * @param html    nội dung HTML (đã escape dữ liệu động)
 */
public record EmailMessage(String to, String subject, String text, String html) {
}
