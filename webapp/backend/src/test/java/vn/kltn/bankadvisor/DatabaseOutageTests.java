package vn.kltn.bankadvisor;

import io.zonky.test.db.postgres.embedded.EmbeddedPostgres;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.net.ServerSocket;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Tình huống lỗi (bổ sung 10/11/2026 theo nhận xét hội đồng): cơ sở dữ liệu PostgreSQL ngừng giữa chừng rồi chạy lại.
 * Khi mất kết nối, API phải trả lỗi có cấu trúc trong thời gian ngắn (không treo, không lộ chi tiết nội bộ) và health
 * báo DOWN; khi CSDL chạy lại, hệ thống tự phục hồi mà không cần khởi động lại máy chủ ứng dụng.
 */
@SpringBootTest(properties = {
        "APP_ENV_FILE=khong-ton-tai.env",
        "app.data-import.dir=src/test/resources/serving",
        "app.jwt.secret=test-secret-that-is-long-enough-for-hs256-signing",
        "app.bootstrap-admin.email=",
        "app.bootstrap-admin.password=",
        "spring.datasource.hikari.connection-timeout=2000",
        "spring.datasource.hikari.validation-timeout=1000",
        "management.endpoint.health.show-components=always"
})
class DatabaseOutageTests {

    private static final Path DATA_DIR = tempDir();
    private static final int PORT = freePort();
    private static EmbeddedPostgres postgres = start();

    @Autowired
    private WebApplicationContext context;

    private static Path tempDir() {
        try {
            return Files.createTempDirectory("ba-pg-outage");
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static int freePort() {
        try (ServerSocket s = new ServerSocket(0)) {
            return s.getLocalPort();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private static EmbeddedPostgres start() {
        try {
            return EmbeddedPostgres.builder().setPort(PORT).setDataDirectory(DATA_DIR).setCleanDataDirectory(false).start();
        } catch (IOException e) {
            throw new UncheckedIOException("Không khởi động được PostgreSQL nhúng", e);
        }
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> postgres.getJdbcUrl("postgres", "postgres"));
        registry.add("spring.datasource.username", () -> "postgres");
        registry.add("spring.datasource.password", () -> "");
    }

    @AfterAll
    static void stop() throws IOException {
        postgres.close();
    }

    @Test
    void apiFailsFastWhileDatabaseIsDownAndRecoversWithoutRestart() throws Exception {
        MockMvc mvc = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
        mvc.perform(get("/api/v1/banks")).andExpect(status().isOk()).andExpect(jsonPath("$.success").value(true));

        postgres.close();  // CSDL ngừng: tiến trình PostgreSQL dừng hẳn, cổng không còn nghe
        long t0 = System.nanoTime();
        MvcResult down = mvc.perform(get("/api/v1/banks")).andReturn();
        double seconds = (System.nanoTime() - t0) / 1e9;
        int code = down.getResponse().getStatus();
        String body = down.getResponse().getContentAsString();
        assertTrue(code >= 500, "mất CSDL phải trả lỗi 5xx, nhận " + code);
        assertTrue(body.contains("\"success\":false"), "lỗi vẫn theo khuôn JSON chung: " + body);
        assertTrue(!body.contains("org.postgresql") && !body.contains("Exception"), "không lộ chi tiết nội bộ: " + body);
        assertTrue(seconds < 10, "phải báo lỗi nhanh, không treo: " + seconds + " giây");
        mvc.perform(get("/actuator/health")).andExpect(status().isServiceUnavailable());
        System.out.printf("[mat-csdl] ma=%d, thoi-gian=%.2fs, than=%s%n", code, seconds, body);

        postgres = start();  // CSDL chạy lại trên cùng cổng, cùng dữ liệu
        boolean recovered = false;
        long t1 = System.nanoTime();
        for (int i = 0; i < 20 && !recovered; i++) {
            recovered = mvc.perform(get("/api/v1/banks")).andReturn().getResponse().getStatus() == 200;
            if (!recovered) {
                Thread.sleep(500);
            }
        }
        assertTrue(recovered, "API phải tự phục hồi khi CSDL chạy lại");
        System.out.printf("[phuc-hoi] sau %.2fs%n", (System.nanoTime() - t1) / 1e9);
        mvc.perform(get("/actuator/health")).andExpect(status().isOk());
        mvc.perform(get("/api/v1/rankings").param("purpose", "SAVINGS")).andExpect(status().isOk());
    }
}
