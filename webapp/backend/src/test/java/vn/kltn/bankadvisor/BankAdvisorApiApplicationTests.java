package vn.kltn.bankadvisor;

import jakarta.servlet.http.Cookie;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.core.env.ConfigurableEnvironment;
import org.springframework.web.filter.ForwardedHeaderFilter;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import com.jayway.jsonpath.JsonPath;
import vn.kltn.bankadvisor.module.advisor.entity.RepaymentMethod;
import vn.kltn.bankadvisor.module.user.entity.AppUser;
import vn.kltn.bankadvisor.module.user.entity.Role;
import vn.kltn.bankadvisor.module.user.repository.AppUserRepository;
import vn.kltn.bankadvisor.module.watchlist.service.NotificationService;

import java.time.LocalDate;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.hamcrest.Matchers.greaterThanOrEqualTo;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.security.test.web.servlet.setup.SecurityMockMvcConfigurers.springSecurity;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Chạy toàn bộ ứng dụng trên H2 trong bộ nhớ và bộ CSV mẫu ở src/test/resources/serving:
 * nạp dữ liệu → API công khai → đăng ký/đăng nhập bằng cookie → API cần đăng nhập.
 */
@SpringBootTest(properties = {
        // Không đọc file .env của máy dev: test phải chạy giống nhau ở mọi máy.
        "APP_ENV_FILE=khong-ton-tai.env",
        "spring.datasource.url=jdbc:h2:mem:bankadvisor;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DEFAULT_NULL_ORDERING=HIGH;DB_CLOSE_DELAY=-1",
        "app.data-import.dir=src/test/resources/serving",
        "app.jwt.secret=test-secret-that-is-long-enough-for-hs256-signing",
        "app.bootstrap-admin.email=",
        "app.bootstrap-admin.password="
})
class BankAdvisorApiApplicationTests {

    @Autowired
    private WebApplicationContext context;

    @Autowired
    private NotificationService notificationService;

    @Autowired
    private AppUserRepository userRepository;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        // Gắn ForwardedHeaderFilter do server.forward-headers-strategy=framework đăng ký (MockMvc không tự gắn filter),
        // đặt trước chuỗi filter của Spring Security giống thứ tự khi chạy thật.
        ForwardedHeaderFilter forwarded = context.getBeansOfType(FilterRegistrationBean.class).values().stream()
                .map(FilterRegistrationBean::getFilter)
                .filter(ForwardedHeaderFilter.class::isInstance)
                .map(ForwardedHeaderFilter.class::cast)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("Thiếu ForwardedHeaderFilter: kiểm tra server.forward-headers-strategy"));
        // Mọi request kèm token CSRF hợp lệ như giao diện thật; test riêng ở dưới kiểm cơ chế cookie + header.
        mvc = MockMvcBuilders.webAppContextSetup(context).addFilters(forwarded).apply(springSecurity())
                .defaultRequest(get("/").with(TestCsrf.xsrf())).build();
    }

    @Test
    void doesNotReadDeveloperEnvFile() {
        // .env của máy dev có thể chứa cấu hình SMTP thật: test không được nạp nó.
        assertTrue(((ConfigurableEnvironment) context.getEnvironment()).getPropertySources().stream()
                .noneMatch(source -> source.getName().contains(".env]")));
    }

    @Test
    void servesImportedReferenceDataAndSkipsUnknownTickers() throws Exception {
        mvc.perform(get("/api/v1/banks"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data", hasSize(2)));

        // Dòng XYZ trong bank_quarterly.csv bị bỏ qua; NIM của ACB (3,5) đứng đầu vì chỉ tiêu "cao hơn tốt hơn".
        mvc.perform(get("/api/v1/banks/acb/indicators"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.latestPeriod").value("2026-Q2"))
                .andExpect(jsonPath("$.data.indicators[1].indicator.code").value("nim"))
                .andExpect(jsonPath("$.data.indicators[1].latest.rank").value(1))
                .andExpect(jsonPath("$.data.indicators[1].latest.bankCount").value(2));
    }

    @Test
    void servesInflationForRealRateAndBankOwnership() throws Exception {
        mvc.perform(get("/api/v1/macro/inflation"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.latest.month").value("2026-08"))
                .andExpect(jsonPath("$.data.latest.yoyPercent").value(4.89))
                .andExpect(jsonPath("$.data.sourceUrl").value("https://www.nso.gov.vn/thang-8"))
                .andExpect(jsonPath("$.data.series", hasSize(2)));

        mvc.perform(get("/api/v1/banks/vcb"))
                .andExpect(jsonPath("$.data.ownership.statePercent").value(74.8035))
                .andExpect(jsonPath("$.data.ownership.asOfDate").value("2026-09-09"));
        // Danh sách cũng mang cơ cấu sở hữu; dòng mã lạ XYZ bị bỏ qua khi nạp.
        mvc.perform(get("/api/v1/banks"))
                .andExpect(jsonPath("$.data[0].ticker").value("ACB"))
                .andExpect(jsonPath("$.data[0].ownership.statePercent").value(0.0))
                .andExpect(jsonPath("$.data[0].ownership.foreignPercent").value(23.6416));
    }

    @Test
    void listsRateChangesAgainstPreviousObservation() throws Exception {
        // ACB 12 tháng trực tuyến 5,9 → 6,1; VCB giữ nguyên; ACB 6 tháng tại quầy mới xuất hiện (không tính là thay đổi).
        mvc.perform(get("/api/v1/rates/deposit/changes").param("days", "30"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.latestDate").value("2026-09-27"))
                .andExpect(jsonPath("$.data.fromDate").value("2026-08-29"))
                .andExpect(jsonPath("$.data.changes", hasSize(1)))
                .andExpect(jsonPath("$.data.changes[0].ticker").value("ACB"))
                .andExpect(jsonPath("$.data.changes[0].termMonths").value(12))
                .andExpect(jsonPath("$.data.changes[0].previousDate").value("2026-09-26"))
                .andExpect(jsonPath("$.data.changes[0].previousRate").value(5.9))
                .andExpect(jsonPath("$.data.changes[0].change").value(0.2));

        // Cửa sổ 1 ngày chỉ gồm ngày mới nhất — vẫn thấy thay đổi của ngày đó.
        mvc.perform(get("/api/v1/rates/deposit/changes").param("days", "1"))
                .andExpect(jsonPath("$.data.fromDate").value("2026-09-27"))
                .andExpect(jsonPath("$.data.changes", hasSize(1)));

        mvc.perform(get("/api/v1/rates/deposit/changes").param("days", "0"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("BAD_REQUEST"));
    }

    @Test
    void unknownBankReturnsNotFoundEnvelope() throws Exception {
        mvc.perform(get("/api/v1/banks/ZZZ"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.success").value(false))
                .andExpect(jsonPath("$.errorCode").value("BANK_NOT_FOUND"));
    }

    @Test
    void savingsAdviceComputesInterestAndPicksRankingByTermChannelAndAmount() throws Exception {
        // 100 triệu: mốc 100 triệu (trong hạn mức BHTG, trọng số an toàn 0).
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":100000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.rateDate").value("2026-09-27"))
                .andExpect(jsonPath("$.data.offers[0].ticker").value("ACB"))
                .andExpect(jsonPath("$.data.offers[0].interest").value(6_100_000))
                .andExpect(jsonPath("$.data.offers[0].changeFromPrevious").value(0.2))
                .andExpect(jsonPath("$.data.ranking.status").value("AVAILABLE"))
                .andExpect(jsonPath("$.data.ranking.amountVnd").value(100_000_000))
                .andExpect(jsonPath("$.data.ranking.safetyWeight").value(0.0))
                .andExpect(jsonPath("$.data.ranking.items[0].ticker").value("ACB"))
                .andExpect(jsonPath("$.data.ranking.items[0].shareTop1").value(1.0));
        // 2 tỷ: mốc lớn nhất không vượt số tiền là 1 tỷ, an toàn nặng hơn nên VCB lên đầu.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":2000000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(jsonPath("$.data.ranking.amountVnd").value(1_000_000_000))
                .andExpect(jsonPath("$.data.ranking.uninsuredShare").value(0.6698))
                .andExpect(jsonPath("$.data.ranking.items[0].ticker").value("VCB"))
                .andExpect(jsonPath("$.data.ranking.items", hasSize(2)));
        // Nhỏ hơn mọi mốc: lấy mốc nhỏ nhất.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":5000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(jsonPath("$.data.ranking.amountVnd").value(100_000_000));
        // Kỳ hạn × kênh không có bảng xếp hạng.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":100000000,\"termMonths\":12,\"channel\":\"COUNTER\"}"))
                .andExpect(jsonPath("$.data.ranking.status").value("NOT_AVAILABLE"))
                .andExpect(jsonPath("$.data.ranking.reason").value("TERM_NOT_RANKED"));
    }

    @Test
    void rankingsEndpointServesDefaultSavingsTableAndLoanTable() throws Exception {
        mvc.perform(get("/api/v1/rankings").param("purpose", "SAVINGS"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("AVAILABLE"))
                .andExpect(jsonPath("$.data.asOfPeriod").value("2026-Q3"))
                .andExpect(jsonPath("$.data.termMonths").value(12))
                .andExpect(jsonPath("$.data.channel").value("ONLINE"))
                .andExpect(jsonPath("$.data.amountVnd").doesNotExist())
                .andExpect(jsonPath("$.data.safetyWeight").value(0.375))
                .andExpect(jsonPath("$.data.items[0].ticker").value("ACB"))
                .andExpect(jsonPath("$.data.items[0].rankHigh").value(2));
        mvc.perform(get("/api/v1/rankings").param("purpose", "LOAN").param("limit", "1"))
                .andExpect(jsonPath("$.data.ratesAsOf").value("2026-09"))
                .andExpect(jsonPath("$.data.items", hasSize(1)))
                .andExpect(jsonPath("$.data.items[0].ticker").value("VCB"))
                .andExpect(jsonPath("$.data.items[0].topPositive").value("Lãi cho vay bình quân"));
    }

    @Test
    void savingsAdviceAppliesAmountTierOnlyWhenBaseRateStillMatches() throws Exception {
        // 100 triệu: dưới mọi bậc → lãi niêm yết, không có tierLabel.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":100000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(jsonPath("$.data.offers[0].ratePercent").value(6.1))
                .andExpect(jsonPath("$.data.offers[0].tierLabel").doesNotExist());
        // 1 tỷ: ACB lên bậc "Từ 1 tỷ" 6,3%. Bậc 6,5% của VCB bị bỏ qua vì lãi gốc 5,6 ≠ 5,7 đang niêm yết.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":1000000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(jsonPath("$.data.offers[0].ticker").value("ACB"))
                .andExpect(jsonPath("$.data.offers[0].ratePercent").value(6.3))
                .andExpect(jsonPath("$.data.offers[0].tierLabel").value("Từ 1 tỷ"))
                .andExpect(jsonPath("$.data.offers[0].interest").value(63_000_000))
                .andExpect(jsonPath("$.data.offers[1].ticker").value("VCB"))
                .andExpect(jsonPath("$.data.offers[1].ratePercent").value(5.7))
                .andExpect(jsonPath("$.data.offers[1].tierLabel").doesNotExist());
        // 6 tỷ: lấy bậc cao nhất có ngưỡng ≤ số tiền.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":6000000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(jsonPath("$.data.offers[0].ratePercent").value(6.4))
                .andExpect(jsonPath("$.data.offers[0].tierLabel").value("Từ 5 tỷ"));
        // 3 tỷ: bậc "Từ 2 tỷ" có hiệu lực từ 2026-10-01, sau ngày lãi 2026-09-27 → chưa áp, vẫn là "Từ 1 tỷ".
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":3000000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(jsonPath("$.data.offers[0].ratePercent").value(6.3))
                .andExpect(jsonPath("$.data.offers[0].tierLabel").value("Từ 1 tỷ"))
                .andExpect(jsonPath("$.data.offers[0].appScore").doesNotExist());
    }

    @Test
    void loanAdviceCarriesSegmentAndSourceOfEachBankRate() throws Exception {
        // Mỗi ngân hàng giữ tháng mới nhất của mình; nhãn nhóm khách hàng/nguồn đi kèm để giao diện ghi rõ số nào.
        mvc.perform(post("/api/v1/advisor/loans").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"purpose\":\"HOME_PURCHASE\",\"amount\":1000000000,\"termMonths\":240,"
                                + "\"repayment\":\"ANNUITY\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.latestMonth").value("2026-07"))
                .andExpect(jsonPath("$.data.offers[0].ticker").value("VCB"))
                .andExpect(jsonPath("$.data.offers[0].segment").value("UNSPECIFIED"))
                .andExpect(jsonPath("$.data.offers[0].source").value("VIETNAMNET"))
                .andExpect(jsonPath("$.data.offers[0].basis").doesNotExist())
                .andExpect(jsonPath("$.data.offers[1].ticker").value("ACB"))
                .andExpect(jsonPath("$.data.offers[1].segment").value("INDIVIDUAL"))
                .andExpect(jsonPath("$.data.offers[1].basis").value("NEW_LOANS"))
                .andExpect(jsonPath("$.data.offers[1].source").value("BANK"))
                .andExpect(jsonPath("$.data.offers[1].sourceUrl").value("https://example.test/a"))
                .andExpect(jsonPath("$.data.offers[1].monthsBehind").value(1));
        mvc.perform(get("/api/v1/banks/acb/lending-rates"))
                .andExpect(jsonPath("$.data[0].segment").value("INDIVIDUAL"))
                .andExpect(jsonPath("$.data[0].depositAvgPercent").value(4.4));
        // Nhóm hẹp (SSB trung dài hạn, SHB tiêu dùng ngắn hạn) phải vừa cột segment VARCHAR(16); tháng cũ hơn số
        // VietnamNet 2026-07 của VCB nên không đổi kết quả trang vay ở trên.
        mvc.perform(get("/api/v1/banks/vcb/lending-rates"))
                .andExpect(jsonPath("$.data", hasSize(3)))
                .andExpect(jsonPath("$.data[0].segment").value("INDIV_MID_LONG"))
                .andExpect(jsonPath("$.data[1].segment").value("CONSUMER_SHORT"))
                .andExpect(jsonPath("$.data[1].depositAvgPercent").doesNotExist());
    }

    @Test
    void savingsAdviceValidatesInput() throws Exception {
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":1000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors.amount").exists());
    }

    @Test
    void personalEndpointsRequireLogin() throws Exception {
        mvc.perform(get("/api/v1/me/watchlist"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.errorCode").value("UNAUTHORIZED"));
        mvc.perform(get("/api/v1/admin/imports"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void internalPathsStayClosedEvenForGet() throws Exception {
        // Matcher GET /api/v1/** công khai không được mở /api/v1/internal/** (dành cho token dịch vụ của pipeline).
        mvc.perform(get("/api/v1/internal/rate-overrides/snapshot"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/internal/releases"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void registerSetsHttpOnlySessionCookieThatUnlocksPersonalEndpoints() throws Exception {
        MvcResult registered = mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"An@Example.test\",\"displayName\":\"An\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isCreated())
                .andExpect(header().string("Set-Cookie", containsString("HttpOnly")))
                .andExpect(jsonPath("$.data.email").value("an@example.test"))
                .andReturn();
        Cookie session = registered.getResponse().getCookie("ba_session");
        assertNotNull(session);

        mvc.perform(get("/api/v1/auth/me").cookie(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.displayName").value("An"));
        mvc.perform(get("/api/v1/auth/session").cookie(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value("an@example.test"));

        mvc.perform(post("/api/v1/me/watchlist").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"ticker\":\"acb\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.data.rate12mOnline").value(6.1));

        mvc.perform(post("/api/v1/me/watchlist").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"ticker\":\"ACB\"}"))
                .andExpect(status().isConflict());

        // Người dùng thường không vào được khu quản trị.
        mvc.perform(get("/api/v1/admin/imports").cookie(session))
                .andExpect(status().isForbidden());

        // Đăng nhập sai mật khẩu và sai email trả cùng một lỗi.
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"an@example.test\",\"password\":\"sai-mat-khau1\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.errorCode").value("INVALID_CREDENTIALS"));
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"khong-co@example.test\",\"password\":\"matkhau123\"}"))
                .andExpect(jsonPath("$.errorCode").value("INVALID_CREDENTIALS"));
    }

    @Test
    void rateChangeCreatesOneNotificationPerWatchedBankAndDay() throws Exception {
        Cookie session = register("binh@example.test", "Bình");
        watch(session, "ACB");   // 12 tháng online 5,9 → 6,1 (+0,2) trong bộ CSV mẫu
        watch(session, "VCB");   // không đổi → không báo

        // ≥ 1 vì người dùng ở test khác (cùng context) có thể cũng theo dõi ACB; số của Bình kiểm qua API bên dưới.
        assertTrue(notificationService.notifyRateChanges(LocalDate.parse("2026-09-27")) >= 1);
        // Nạp lại cùng ngày không tạo trùng (ref_key duy nhất).
        assertEquals(0, notificationService.notifyRateChanges(LocalDate.parse("2026-09-27")));

        mvc.perform(get("/api/v1/me/notifications").cookie(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.totalItems").value(1))
                .andExpect(jsonPath("$.data.items[0].type").value("RATE_CHANGE"))
                .andExpect(jsonPath("$.data.items[0].title").value("ACB thay đổi lãi suất tiết kiệm"))
                .andExpect(jsonPath("$.data.items[0].body", containsString("12 tháng online 5,90% → 6,10% (+0,20)")));
        mvc.perform(get("/api/v1/me/notifications/unread-count").cookie(session))
                .andExpect(jsonPath("$.data.unread").value(1));
        mvc.perform(post("/api/v1/me/notifications/read-all").cookie(session)).andExpect(status().isOk());
        mvc.perform(get("/api/v1/me/notifications/unread-count").cookie(session))
                .andExpect(jsonPath("$.data.unread").value(0));
    }

    @Test
    void loanNeedSavesWithEveryRepaymentMethod() throws Exception {
        Cookie session = register("vay-nha@example.test", "Vay nhà");
        // Mỗi giá trị enum phải vừa cột: DECLINING_BALANCE (17 ký tự) từng vượt VARCHAR(12) → lỗi 500.
        for (RepaymentMethod repayment : RepaymentMethod.values()) {
            mvc.perform(post("/api/v1/me/needs").cookie(session).contentType(MediaType.APPLICATION_JSON)
                            .content("{\"purpose\":\"LOAN\",\"label\":\"Vay 1 tỷ, 20 năm\",\"amount\":1000000000,"
                                    + "\"termMonths\":240,\"loanPurpose\":\"HOUSEHOLD_BUSINESS\",\"repayment\":\"" + repayment + "\"}"))
                    .andExpect(status().isCreated())
                    .andExpect(jsonPath("$.data.repayment").value(repayment.name()));
        }
    }

    private Cookie register(String email, String name) throws Exception {
        MvcResult result = mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"displayName\":\"" + name + "\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isCreated())
                .andReturn();
        return result.getResponse().getCookie("ba_session");
    }

    private void watch(Cookie session, String ticker) throws Exception {
        mvc.perform(post("/api/v1/me/watchlist").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"ticker\":\"" + ticker + "\",\"rateThreshold\":0.1}"))
                .andExpect(status().isCreated());
    }

    @Test
    void postThroughSameOriginProxyIsNotBlockedByCors() throws Exception {
        // Trình duyệt gắn Origin của trang (Next.js :3000); proxy chuyển tiếp kèm X-Forwarded-Host.
        mvc.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .header("Origin", "http://localhost:3000")
                        .header("X-Forwarded-Host", "localhost:3000")
                        .header("X-Forwarded-Proto", "http")
                        .content("{\"amount\":100000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void userFixesMistypedEmailWithCurrentPassword() throws Exception {
        Cookie session = register("hoa@gamil.com", "Hoa");
        register("da-dung@example.test", "Người khác");

        mvc.perform(put("/api/v1/me/email").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"newEmail\":\"hoa@gmail.com\",\"currentPassword\":\"sai-mat-khau1\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("WRONG_PASSWORD"));
        mvc.perform(put("/api/v1/me/email").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"newEmail\":\"da-dung@example.test\",\"currentPassword\":\"matkhau123\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.errorCode").value("EMAIL_TAKEN"));

        MvcResult changed = mvc.perform(put("/api/v1/me/email").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"newEmail\":\"Hoa@Gmail.com\",\"currentPassword\":\"matkhau123\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.email").value("hoa@gmail.com"))
                .andExpect(jsonPath("$.data.emailVerified").value(false))
                .andReturn();
        assertNotNull(changed.getResponse().getCookie("ba_session"));

        // Đăng nhập bằng email mới được; email gõ nhầm cũ thì không còn.
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"hoa@gmail.com\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isOk());
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"hoa@gamil.com\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void crossOriginWriteWithSessionCookieIsRejected() throws Exception {
        // Trang ở origin khác gửi request kèm cookie phiên (CSRF): bộ lọc CORS chặn trước khi tới controller.
        Cookie session = register("dung@example.test", "Dũng");
        mvc.perform(post("/api/v1/me/watchlist").cookie(session).contentType(MediaType.APPLICATION_JSON)
                        .header("Origin", "http://trang-la.test")
                        .content("{\"ticker\":\"ACB\"}"))
                .andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/me/watchlist").cookie(session))
                .andExpect(jsonPath("$.data", hasSize(0)));
    }

    @Test
    void repeatedWrongPasswordsAreThrottledPerEmailAndIp() throws Exception {
        register("chi@example.test", "Chi");
        for (int i = 0; i < 5; i++) {
            mvc.perform(post("/api/v1/auth/login").with(fromIp("10.0.0.1")).contentType(MediaType.APPLICATION_JSON)
                            .content("{\"email\":\"chi@example.test\",\"password\":\"sai-mat-khau1\"}"))
                    .andExpect(status().isUnauthorized());
        }
        // Lần thứ 6 bị chặn, kể cả khi nhập đúng mật khẩu.
        mvc.perform(post("/api/v1/auth/login").with(fromIp("10.0.0.1")).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"chi@example.test\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().exists("Retry-After"))
                .andExpect(jsonPath("$.errorCode").value("TOO_MANY_REQUESTS"));
        // Máy khác vẫn đăng nhập được: kẻ xấu không khóa được tài khoản người khác chỉ bằng cách nhập sai.
        mvc.perform(post("/api/v1/auth/login").with(fromIp("10.0.0.2")).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"chi@example.test\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isOk());
    }

    private static RequestPostProcessor fromIp(String ip) {
        return request -> {
            request.setRemoteAddr(ip);
            return request;
        };
    }

    @Test
    void sessionEndpointReturnsNullForGuests() throws Exception {
        mvc.perform(get("/api/v1/auth/session"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.success").value(true))
                .andExpect(jsonPath("$.data").doesNotExist());
    }

    @Test
    void staleCookieDoesNotBreakPublicPages() throws Exception {
        mvc.perform(get("/api/v1/overview").cookie(new Cookie("ba_session", "token-hong")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.market.banksRaised").value(1))
                .andExpect(jsonPath("$.data.market.banksUnchanged").value(1));
    }

    @Test
    void overviewSummarisesCounterChannelSeparately() throws Exception {
        // 12 tháng tại quầy: VCB 5,0 giữ nguyên; ACB 5,2 mới xuất hiện (có số hôm nay nhưng không tính tăng/giảm).
        mvc.perform(get("/api/v1/overview"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.market.highest.ticker").value("ACB"))
                .andExpect(jsonPath("$.data.market.highest.rate").value(6.1))
                .andExpect(jsonPath("$.data.counterMarket.referenceTermMonths").value(12))
                .andExpect(jsonPath("$.data.counterMarket.highest.ticker").value("ACB"))
                .andExpect(jsonPath("$.data.counterMarket.highest.rate").value(5.2))
                .andExpect(jsonPath("$.data.counterMarket.median").value(5.1))
                .andExpect(jsonPath("$.data.counterMarket.lowest").value(5.0))
                .andExpect(jsonPath("$.data.counterMarket.banksQuoted").value(2))
                .andExpect(jsonPath("$.data.counterMarket.banksRaised").value(0))
                .andExpect(jsonPath("$.data.counterMarket.banksUnchanged").value(1));
    }

    // ===== Phân quyền: quyền theo chức năng, khóa tài khoản, thu hồi phiên =====

    @Test
    void userSeesOwnPermissionsAndIsDeniedAdminEndpoints() throws Exception {
        Cookie session = register("pq-user@example.test", "Người dùng");
        mvc.perform(get("/api/v1/auth/me").cookie(session))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.role").value("USER"))
                .andExpect(jsonPath("$.data.permissions", hasSize(1)))
                .andExpect(jsonPath("$.data.permissions[0]").value("PERSONAL_DATA"));
        mvc.perform(get("/api/v1/admin/users").cookie(session))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("FORBIDDEN"));
        mvc.perform(get("/api/v1/admin/imports").cookie(session))
                .andExpect(status().isForbidden());
    }

    @Test
    void lockedAccountLosesOpenSessionsAndCannotLogIn() throws Exception {
        register("pq-admin@example.test", "Quản trị");
        promoteToAdmin("pq-admin@example.test");
        Cookie admin = login("pq-admin@example.test");
        mvc.perform(get("/api/v1/auth/me").cookie(admin))
                .andExpect(jsonPath("$.data.permissions", hasSize(4)));

        Cookie user = register("pq-khoa@example.test", "Bị khóa");
        mvc.perform(get("/api/v1/me/watchlist").cookie(user)).andExpect(status().isOk());

        MvcResult list = mvc.perform(get("/api/v1/admin/users").param("q", "pq-khoa").cookie(admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.users.items", hasSize(1)))
                .andExpect(jsonPath("$.data.users.items[0].status").value("ACTIVE"))
                .andExpect(jsonPath("$.data.stats.admins", greaterThanOrEqualTo(1)))
                .andReturn();
        int userId = JsonPath.read(list.getResponse().getContentAsString(), "$.data.users.items[0].id");

        // Khóa phải có lý do.
        mvc.perform(patch("/api/v1/admin/users/" + userId).cookie(admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"LOCKED\"}"))
                .andExpect(status().isBadRequest());
        mvc.perform(patch("/api/v1/admin/users/" + userId).cookie(admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"LOCKED\",\"reason\":\"Thử khóa\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.status").value("LOCKED"));

        // Phiên đang mở bị chặn ngay ở request kế tiếp; đăng nhập lại cũng bị chặn.
        mvc.perform(get("/api/v1/me/watchlist").cookie(user))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("ACCOUNT_LOCKED"));
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"pq-khoa@example.test\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("ACCOUNT_LOCKED"));

        // Mở khóa: đăng nhập lại được, nhưng phiên cũ không sống lại.
        mvc.perform(patch("/api/v1/admin/users/" + userId).cookie(admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"ACTIVE\"}"))
                .andExpect(jsonPath("$.data.status").value("ACTIVE"));
        mvc.perform(get("/api/v1/me/watchlist").cookie(user)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/me/watchlist").cookie(login("pq-khoa@example.test"))).andExpect(status().isOk());
    }

    @Test
    void adminCannotLockOrDemoteSelf() throws Exception {
        register("pq-tu-khoa@example.test", "Quản trị");
        promoteToAdmin("pq-tu-khoa@example.test");
        Cookie admin = login("pq-tu-khoa@example.test");
        long selfId = userRepository.findByEmail("pq-tu-khoa@example.test").orElseThrow().getId();
        mvc.perform(patch("/api/v1/admin/users/" + selfId).cookie(admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"role\":\"USER\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.errorCode").value("CANNOT_MODIFY_SELF"));
    }

    @Test
    void revokeAllSessionsEndsEveryOpenLogin() throws Exception {
        Cookie first = register("pq-dang-xuat@example.test", "Nhiều máy");
        Cookie second = login("pq-dang-xuat@example.test");
        mvc.perform(post("/api/v1/me/sessions/revoke-all").cookie(first)).andExpect(status().isOk());
        mvc.perform(get("/api/v1/me/watchlist").cookie(second))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.errorCode").value("UNAUTHORIZED"));
    }

    @Test
    void writesNeedTheCsrfTokenFromTheCookie() throws Exception {
        // MockMvc không có token CSRF mặc định: đi đúng đường của trình duyệt (cookie XSRF-TOKEN → header X-XSRF-TOKEN).
        MockMvc browser = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
        Cookie xsrf = browser.perform(get("/api/v1/auth/session"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getCookie("XSRF-TOKEN");
        assertNotNull(xsrf, "trang công khai phải cấp cookie XSRF-TOKEN");
        assertTrue(!xsrf.isHttpOnly(), "JavaScript của trang phải đọc được cookie XSRF-TOKEN");
        String body = "{\"email\":\"csrf@example.test\",\"displayName\":\"Csrf\",\"password\":\"matkhau123\"}";
        browser.perform(post("/api/v1/auth/register").cookie(xsrf).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("CSRF_TOKEN_INVALID"));
        browser.perform(post("/api/v1/auth/register").cookie(xsrf).header("X-XSRF-TOKEN", "gia-tri-doan-bua")
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isForbidden());
        browser.perform(post("/api/v1/auth/register").cookie(xsrf).header("X-XSRF-TOKEN", xsrf.getValue())
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated());
        // Công cụ tính chỉ đọc dữ liệu nên không cần token.
        browser.perform(post("/api/v1/advisor/savings").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\":100000000,\"termMonths\":12,\"channel\":\"ONLINE\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void personalWritesWithSessionCookieStillNeedCsrfToken() throws Exception {
        // Cookie phiên được đọc như bearer token; oauth2ResourceServer từng tắt kiểm tra CSRF cho các request này
        // (phát hiện khi kiểm thử bổ sung 10/11/2026). Có cookie phiên mà thiếu header X-XSRF-TOKEN thì phải bị chặn.
        Cookie session = register("csrf-phien@example.test", "Csrf phiên");
        MockMvc browser = MockMvcBuilders.webAppContextSetup(context).apply(springSecurity()).build();
        String need = "{\"purpose\":\"SAVINGS\",\"label\":\"Gửi 500 triệu\",\"amount\":500000000,"
                + "\"termMonths\":12,\"channel\":\"ONLINE\"}";
        browser.perform(post("/api/v1/me/needs").cookie(session).contentType(MediaType.APPLICATION_JSON).content(need))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.errorCode").value("CSRF_TOKEN_INVALID"));
        browser.perform(post("/api/v1/me/needs").cookie(session).with(TestCsrf.xsrf())
                        .contentType(MediaType.APPLICATION_JSON).content(need))
                .andExpect(status().isCreated());
    }

    @Test
    void apiPathsNotListedAsPublicStayClosed() throws Exception {
        // GET /api/v1/** không còn mở cả loạt: đường dẫn chưa khai báo công khai bị chặn, kể cả khi đã đăng nhập
        // (cookie phiên chỉ được đọc ở đường dẫn cần đăng nhập, nên request vẫn là khách → 401).
        mvc.perform(get("/api/v1/khong-co-api-nay")).andExpect(status().isUnauthorized());
        Cookie session = register("pq-duong-la@example.test", "Đường lạ");
        mvc.perform(get("/api/v1/khong-co-api-nay").cookie(session)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/banks/acb/rates")).andExpect(status().isOk());
    }

    @Test
    void changingPasswordKeepsThisBrowserAndEndsOtherSessions() throws Exception {
        Cookie first = register("doi-mat-khau@example.test", "Đổi mật khẩu");
        Cookie second = login("doi-mat-khau@example.test");
        mvc.perform(put("/api/v1/me/password").cookie(first).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"sai-mat-khau1\",\"newPassword\":\"matkhaumoi456\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("WRONG_PASSWORD"));
        mvc.perform(put("/api/v1/me/password").cookie(first).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"matkhau123\",\"newPassword\":\"ngan\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("VALIDATION_FAILED"));
        Cookie renewed = mvc.perform(put("/api/v1/me/password").cookie(first).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"currentPassword\":\"matkhau123\",\"newPassword\":\"matkhaumoi456\"}"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getCookie("ba_session");
        mvc.perform(get("/api/v1/me/watchlist").cookie(second)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/me/watchlist").cookie(first)).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/me/watchlist").cookie(renewed)).andExpect(status().isOk());
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"doi-mat-khau@example.test\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isUnauthorized());
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"doi-mat-khau@example.test\",\"password\":\"matkhaumoi456\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void passwordResetNeedsEmailAndAValidLink() throws Exception {
        // Bộ test này chạy với email tắt; luồng gửi link thật nằm ở EmailNotificationIntegrationTests.
        mvc.perform(post("/api/v1/auth/password-reset").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"ai-do@example.test\"}"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.errorCode").value("EMAIL_DISABLED"));
        mvc.perform(post("/api/v1/auth/password-reset/confirm").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"khong-phai-token\",\"newPassword\":\"matkhaumoi456\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errorCode").value("PASSWORD_RESET_INVALID"));
    }

    @Test
    void adminActionsAreWrittenToTheAuditLog() throws Exception {
        register("nk-quan-tri@example.test", "Quản trị nhật ký");
        promoteToAdmin("nk-quan-tri@example.test");
        Cookie admin = login("nk-quan-tri@example.test");
        Cookie user = register("nk-nguoi-dung@example.test", "Người dùng nhật ký");
        long userId = userRepository.findByEmail("nk-nguoi-dung@example.test").orElseThrow().getId();

        mvc.perform(patch("/api/v1/admin/users/" + userId).cookie(admin).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"status\":\"LOCKED\",\"reason\":\"Thử nhật ký\"}"))
                .andExpect(status().isOk());
        mvc.perform(post("/api/v1/admin/imports").cookie(admin)).andExpect(status().isOk());
        mvc.perform(get("/api/v1/admin/audit?size=5").cookie(admin))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.items[0].action").value("DATA_IMPORT"))
                .andExpect(jsonPath("$.data.items[0].actorEmail").value("nk-quan-tri@example.test"))
                .andExpect(jsonPath("$.data.items[1].action").value("USER_LOCK"))
                .andExpect(jsonPath("$.data.items[1].targetEmail").value("nk-nguoi-dung@example.test"))
                .andExpect(jsonPath("$.data.items[1].detail").value("Lý do: Thử nhật ký"));
        // Người dùng thường không xem được nhật ký (tài khoản vừa bị khóa thì càng không).
        Cookie other = register("nk-khac@example.test", "Khác");
        mvc.perform(get("/api/v1/admin/audit").cookie(other)).andExpect(status().isForbidden());
        mvc.perform(get("/api/v1/admin/audit").cookie(user)).andExpect(status().isForbidden());
    }

    private Cookie login(String email) throws Exception {
        return mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"" + email + "\",\"password\":\"matkhau123\"}"))
                .andExpect(status().isOk())
                .andReturn().getResponse().getCookie("ba_session");
    }

    /** Test không có tài khoản quản trị khởi tạo: nâng quyền thẳng trong CSDL (phiên cũ bị thu hồi, phải đăng nhập lại). */
    private void promoteToAdmin(String email) {
        AppUser user = userRepository.findByEmail(email).orElseThrow();
        user.changeRole(Role.ADMIN);
        userRepository.save(user);
    }
}
