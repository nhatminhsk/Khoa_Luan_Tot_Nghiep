package vn.kltn.bankadvisor.common.mail;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;

import java.nio.charset.StandardCharsets;

/** Gửi email thật qua SMTP: một thư gồm bản chữ thường và bản HTML (multipart/alternative), mã hóa UTF-8. */
final class SmtpEmailGateway implements EmailGateway {

    private final JavaMailSender sender;
    private final InternetAddress from;

    SmtpEmailGateway(JavaMailSender sender, InternetAddress from) {
        this.sender = sender;
        this.from = from;
    }

    @Override
    public MailMode mode() {
        return MailMode.SMTP;
    }

    @Override
    public void send(EmailMessage message) {
        try {
            MimeMessage mime = sender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(mime, message.html() != null, StandardCharsets.UTF_8.name());
            helper.setFrom(from);
            helper.setTo(message.to());
            helper.setSubject(message.subject());
            if (message.html() != null) {
                helper.setText(message.text(), message.html());
            } else {
                helper.setText(message.text(), false);
            }
            sender.send(mime);
        } catch (MessagingException | MailException e) {
            throw new EmailDeliveryException(
                    "Không gửi được email tới " + EmailAddresses.mask(message.to()) + ": " + e.getMessage(), e);
        }
    }
}
