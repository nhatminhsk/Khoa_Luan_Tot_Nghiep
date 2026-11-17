package vn.kltn.bankadvisor;

import io.zonky.test.db.postgres.embedded.EmbeddedPostgres;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;

import java.io.IOException;
import java.io.UncheckedIOException;

/**
 * Chạy lại toàn bộ test API của {@link BankAdvisorApiApplicationTests} trên PostgreSQL 17 thật (chạy nhúng, không cần
 * Docker): Flyway V1→Vn từ CSDL trống, Hibernate validate schema, nạp CSV, đăng ký/đăng nhập, phân quyền.
 * <p>
 * Chế độ PostgreSQL của H2 không tái hiện đủ kiểu dữ liệu, khóa và cú pháp của PostgreSQL, nên bộ test H2 không đủ làm
 * bằng chứng chạy được trên CSDL thật.
 */
@SpringBootTest(properties = {
        "APP_ENV_FILE=khong-ton-tai.env",
        "app.data-import.dir=src/test/resources/serving",
        "app.jwt.secret=test-secret-that-is-long-enough-for-hs256-signing",
        "app.bootstrap-admin.email=",
        "app.bootstrap-admin.password="
})
class PostgresCompatibilityTests extends BankAdvisorApiApplicationTests {

    /** Một tiến trình PostgreSQL cho cả lớp; thư viện tự dừng nó khi JVM kết thúc. */
    private static final EmbeddedPostgres POSTGRES = start();

    private static EmbeddedPostgres start() {
        try {
            return EmbeddedPostgres.builder().start();
        } catch (IOException e) {
            throw new UncheckedIOException("Không khởi động được PostgreSQL nhúng", e);
        }
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", () -> POSTGRES.getJdbcUrl("postgres", "postgres"));
        registry.add("spring.datasource.username", () -> "postgres");
        registry.add("spring.datasource.password", () -> "");
    }
}
