package vn.kltn.bankadvisor.common.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Clock;
import java.time.ZoneId;

/** Đồng hồ theo giờ Việt Nam; tiêm {@link Clock} thay vì gọi {@code now()} trực tiếp để test được. */
@Configuration
public class TimeConfig {

    public static final ZoneId VIETNAM = ZoneId.of("Asia/Ho_Chi_Minh");

    @Bean
    Clock clock() {
        return Clock.system(VIETNAM);
    }
}
