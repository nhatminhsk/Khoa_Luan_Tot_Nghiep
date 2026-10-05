# BankAdvisor — web app hỗ trợ chọn ngân hàng gửi tiết kiệm và vay

Giao diện và API của khóa luận. Frontend **Next.js 16** (App Router, TypeScript, MUI 9), backend **Spring Boot 4.1** (Java 25, JPA, Flyway, H2). Dữ liệu lấy từ pipeline Python của khóa luận qua thư mục `data/serving/`.

```
Trình duyệt ──► Next.js :3000 ──(/api/* rewrite)──► Spring Boot :8080 ──► H2 (file .data/)
                  trang + gọi API                     Controller → Service → Repository → Entity
                                                                         ▲
Pipeline Python ── python -m serving.export ──► data/serving/*.csv ──────┘  (nạp khi khởi động + 16:00 hằng ngày)
```

## Chạy trên máy

Yêu cầu: JDK 25 trở lên (máy đang có JDK 27), Node.js 20 trở lên, Python của pipeline.

1. **Xuất dữ liệu cho web** (từ `D:\KLTN`). Lần crawl hằng ngày (`run_daily_crawl.py`, 15:30) đã tự chạy bước này ở cuối; chỉ cần chạy tay sau khi dựng lại panel/đặc trưng hoặc khi mô hình ghi kết quả mới:
   ```
   python -m serving.export
   ```
2. **Backend** (từ `webapp/backend`). Lần đầu: sao chép `.env.example` thành `.env` và điền `APP_JWT_SECRET` (≥ 32 ký tự ngẫu nhiên), `APP_ADMIN_EMAIL`, `APP_ADMIN_PASSWORD`.
   ```
   mvnw.cmd spring-boot:run
   ```
   API ở http://localhost:8080. Khi khởi động, backend tạo schema (Flyway), tạo tài khoản quản trị nếu chưa có, và nạp `data/serving/`.
3. **Frontend** (từ `webapp/frontend`):
   ```
   npm install
   npm run dev
   ```
   Mở http://localhost:3000.

Kiểm thử: `mvnw.cmd test` (backend: 33 test, trong đó có test gửi email thật qua máy chủ SMTP chạy trong bộ nhớ; test không đọc file `.env` của máy dev nhờ `APP_ENV_FILE`), `npx tsc --noEmit` và `npx eslint src` (frontend), `npm run build` (build production).

Thử gửi email khi chưa có máy chủ thư: chạy backend với `APP_MAIL_MODE=LOG` (cấu hình `api-email-log` trong `.claude/launch.json`). Email, kể cả link xác minh, được in ra log của backend.

## Backend: mỗi tính năng một module, bốn tầng

```
src/main/java/vn/kltn/bankadvisor/
├── common/        ApiResponse (vỏ phản hồi chung), ErrorCode + GlobalExceptionHandler, cấu hình
├── security/      JWT trong cookie httpOnly, phân quyền USER/ADMIN
└── module/<tính năng>/
    ├── controller/   nhận request, kiểm tra đầu vào (@Valid), trả ApiResponse — không chứa logic
    ├── service/      nghiệp vụ, transaction
    ├── repository/   Spring Data JPA — truy vấn CSDL
    ├── entity/       ánh xạ bảng (model)
    └── dto/          request/response dạng record — không trả entity ra ngoài
```

| Module | Endpoint chính | Ghi chú |
|---|---|---|
| `bank` | `GET /api/v1/banks`, `/banks/{ticker}` | 22 ngân hàng, kèm cơ cấu sở hữu (nhà nước, nước ngoài) |
| `macro` | `/macro/inflation` | Lạm phát theo tháng (CPI so cùng kỳ) để tính lãi suất thực = lãi niêm yết − lạm phát |
| `indicator` | `/indicators`, `/indicators/snapshot`, `/indicators/{code}/comparison`, `/banks/{t}/indicators` | Chỉ tiêu CAMELS, trung vị 22 NH, thứ hạng từng chỉ tiêu |
| `rate` | `/rates/deposit`, `/rates/deposit/best`, `/rates/deposit/trend`, `/rates/lending`, `/banks/{t}/rates` | Lãi suất tiết kiệm theo ngày, cho vay bình quân theo tháng |
| `advisor` | `POST /advisor/savings`, `POST /advisor/loans` | Tiền lãi / tiền trả ước tính (công thức), kèm xếp hạng |
| `ranking`, `forecast` | `/rankings?purpose=`, `/banks/{t}/forecasts` | Đọc kết quả thuật toán; `NOT_AVAILABLE` khi chưa có |
| `app` | `/app-scores`, `/banks/{t}/app` | Điểm kho ứng dụng, review theo tháng, khía cạnh (NLP) |
| `program` | `/programs`, `/banks/{t}/programs` | Tín dụng chính sách |
| `overview` | `/overview` | Gộp dữ liệu trang Tổng quan |
| `dataset` | `/datasets`, `/admin/imports` | Nạp CSV, nhật ký nạp (ADMIN) |
| `user` | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/session`, `/auth/me`, `/auth/verify-email`, `/me/email-verification` | Xác minh email trước khi nhận thông báo qua email |
| `need`, `watchlist` | `/me/needs`, `/me/watchlist`, `/me/notifications`, `/me/notification-settings`, `/admin/email-queue` | Cần đăng nhập; hàng đợi email chỉ ADMIN |

Mọi phản hồi có dạng `{ "success": true, "data": … }` hoặc `{ "success": false, "errorCode": "…", "message": "…", "fieldErrors": {…} }`.

**Cơ sở dữ liệu.** Schema ở `src/main/resources/db/migration` (Flyway), viết cú pháp chung H2/PostgreSQL. Ba nhóm bảng: dữ liệu dùng chung (nạp từ CSV, chỉ đọc), kết quả thuật toán (rỗng tới khi mô hình chốt), dữ liệu riêng từng người (tài khoản + cài đặt thông báo, nhu cầu, theo dõi, lịch sử thông báo). Không lưu dữ liệu tài chính cá nhân. Chuyển sang PostgreSQL: thêm driver `org.postgresql:postgresql`, đổi `spring.datasource.url/username/password`.

**Nạp dữ liệu.** `module/dataset/importer/ServingDatasets.java` là bản đặc tả "file nào → bảng nào, cột nào, kiểu gì". Mỗi file một transaction; file có checksum không đổi thì bỏ qua; mã ngân hàng / chỉ tiêu lạ bị bỏ qua (không lỗi). Nạp xong phát `DatasetImportedEvent` → module `watchlist` tạo thông báo khi lãi suất ngân hàng người dùng theo dõi đổi từ ngưỡng trở lên, hoặc khi có xếp hạng quý mới.

**Thông báo qua email.** Thông báo luôn hiện trong ứng dụng; người dùng chọn kênh "Trong ứng dụng và email" thì nhận thêm một bản qua email.
- `app.mail.mode` (biến `APP_MAIL_MODE`): `OFF` tắt (mặc định, giao diện khóa lựa chọn email), `LOG` in email ra log (thử khi chưa có máy chủ thư), `SMTP` gửi thật (`APP_SMTP_*`, cổng 587, bắt buộc STARTTLS và kiểm tra chứng chỉ máy chủ). Xem `.env.example`.
- Phải **xác minh email** trước khi chọn kênh email, vì đăng ký không kiểm tra email: nếu không xác minh, ai cũng có thể dùng hệ thống gửi thư tới địa chỉ người khác. Email xác minh có hai cách: **mã 6 số** (nhập ở trang Theo dõi; hiệu lực 15 phút, sai 5 lần thì hủy; lưu băm BCrypt) — dùng được khi đọc thư trên điện thoại — và **link** (hạn 24 giờ; trỏ về `APP_WEB_BASE_URL`, nên khi chạy trên `localhost` chỉ mở được trên chính máy đó). Gửi lại cách nhau tối thiểu 60 giây. Token trong link ký bằng khóa riêng suy ra từ khóa phiên, nên không dùng làm cookie đăng nhập được.
- Gõ nhầm email: trang Đăng ký gợi ý sửa tên miền phổ biến bị gõ nhầm (`gamil.com` → `gmail.com`); người dùng tự **đổi email** được (`PUT /me/email`, cần mật khẩu hiện tại), email mới phải xác minh lại.
- **Hàng đợi (outbox) trên bảng `notification`:** khi tạo thông báo cho người chọn email, dòng đó có `email_status = PENDING`. `NotificationEmailDispatcher` quét mỗi phút, gom thông báo theo người nhận (mỗi người một email), gửi ngoài transaction CSDL, rồi ghi `SENT`; lỗi thì thử lại sau 5, 10 phút, hết 3 lần thì `FAILED` kèm lỗi cuối. Thông báo đã đọc trong ứng dụng, hoặc người dùng đã tắt email trước khi tới lượt, thì `SKIPPED`. Trang Quản trị có mục "Email thông báo": số email theo trạng thái, lỗi gần nhất, nút gửi ngay.
- Thiết kế cho một tiến trình backend. Chạy nhiều bản thì cần khóa phân tán (ShedLock) hoặc `SELECT … FOR UPDATE SKIP LOCKED` trên PostgreSQL.

**Bảo mật.**
- JWT (HS256) nằm trong cookie `httpOnly`, `SameSite=Lax`; JavaScript không đọc được token; cookie hết hạn cùng token.
- Trình duyệt chỉ gọi API qua proxy của Next.js (cùng origin), nên không cần mở CORS; backend đọc `X-Forwarded-*` (`server.forward-headers-strategy`). Khi triển khai, không mở cổng backend ra ngoài.
- Chống CSRF không cần token: cookie `SameSite=Lax` không đi kèm POST/PUT/DELETE từ site khác, và bộ lọc CORS trả 403 cho mọi request mang `Origin` lạ (có test).
- Token chỉ được đọc ở đường dẫn cần đăng nhập, nên cookie hết hạn không làm hỏng trang công khai.
- Mật khẩu băm bằng BCrypt; đăng nhập sai email hay sai mật khẩu trả cùng một lỗi.
- Giới hạn đăng nhập sai: 5 lần / 15 phút cho mỗi cặp (email, IP) và 20 lần / 15 phút cho mỗi email; vượt thì trả 429 kèm `Retry-After`. Đếm theo cặp để người khác không khóa được tài khoản của mình chỉ bằng cách cố tình nhập sai. IP lấy từ `X-Forwarded-For`, mà Next.js chuyển nguyên header này nếu trình duyệt tự gửi, nên khi triển khai, reverse proxy đứng trước Next.js phải ghi đè nó bằng IP thật (nginx: `proxy_set_header X-Forwarded-For $remote_addr;`).
- Next.js gửi header bảo mật cho mọi trang (`next.config.ts`): Content-Security-Policy (chỉ tài nguyên cùng origin, `frame-ancestors 'none'`, `object-src 'none'`), `Referrer-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, `Permissions-Policy`. Trang `/verify-email` đặt thêm `referrer: no-referrer` để token trong URL không lọt ra ngoài. HSTS đặt ở reverse proxy khi có HTTPS.

## Frontend: định tuyến theo thư mục

```
src/
├── app/                      Mỗi thư mục là một đường dẫn (App Router)
│   ├── layout.tsx            Gốc: font, theme sáng/tối, provider
│   ├── (main)/layout.tsx     Khung chính: menu trái + thanh trên (AppShell)
│   ├── (main)/page.tsx       /            Tổng quan
│   ├── (main)/savings/       /savings     Gửi tiết kiệm
│   ├── (main)/loans/         /loans       Vay
│   ├── (main)/banks/         /banks, /banks/[ticker]   Hồ sơ ngân hàng
│   ├── (main)/compare/       /compare     So sánh
│   ├── (main)/watchlist/     /watchlist   Theo dõi và thông báo (cần đăng nhập)
│   ├── (main)/methodology/   /methodology Phương pháp và dữ liệu
│   ├── (main)/admin/         /admin       Quản trị dữ liệu (ADMIN)
│   └── (auth)/login, register, verify-email   (verify-email: trang mở từ link xác minh trong email)
├── proxy.ts                  Chưa có cookie phiên → chuyển tới /login (kiểm tra sớm; quyền thật do backend)
├── config/navigation.ts      Cấu hình menu — sidebar dựng từ đây
├── lib/http/api-client.ts    Gọi API (fetch), bóc vỏ ApiResponse, chuẩn hóa lỗi
├── repositories/             Một file một nhóm endpoint; component không gọi fetch trực tiếp
├── lib/query/keys.ts         Khóa cache TanStack Query (thay cho state toàn cục)
├── features/<trang>/         Component của từng trang (form, bảng, biểu đồ)
├── components/               Dùng chung: layout, bảng/thẻ/trạng thái, form (react-hook-form), biểu đồ
├── theme/                    Theme MUI sáng/tối, bảng màu biểu đồ đã kiểm tra an toàn mù màu
└── types/api.ts              Kiểu dữ liệu khớp 1–1 với DTO của backend
```

Luồng một thao tác, ví dụ bấm "Xem kết quả" ở trang Gửi tiết kiệm:
`SavingsForm` (react-hook-form + zod) → ghi tiêu chí lên URL → `SavingsView` đọc URL, `useQuery` gọi `advisorRepository.savings()` → `apiClient.post("/advisor/savings")` → Next.js chuyển tiếp → `AdvisorController.savings()` → `SavingsAdvisorService.advise()` → `RateService.snapshot()` → `DepositRateRepository` → bảng `deposit_rate`.

Tiêu chí tìm kiếm nằm trên URL nên chép link là mở lại đúng kết quả. Người dùng lưu nhu cầu thì trang Theo dõi mở lại bằng chính URL đó.

Tính năng mô tả số liệu (không phải kết quả thuật toán, làm ngày 30/09 sau khi tham khảo các trang dữ liệu tài chính):
- **Lãi suất thực** (`utils/real-rate.ts`): lãi niêm yết − lạm phát so cùng kỳ của tháng mới nhất. Cột "Lãi thực" ở trang Gửi tiết kiệm, thẻ "Lãi suất thực" và đường lạm phát trên biểu đồ diễn biến lãi suất ở trang Tổng quan.
- **Tóm tắt nhanh** đầu hồ sơ (`utils/bank-summary.ts`): câu mô tả tự sinh (quy mô, thay đổi so cùng kỳ của nợ xấu, CAR, NIM, ROE, CASA) và điểm mạnh/yếu = chỉ tiêu nằm trong 3 hạng đầu/cuối.
- **Bảng nhiều kỳ** trong tab Chỉ tiêu (`IndicatorTable.tsx`): theo năm (số quý 4) hoặc theo quý, kèm trung vị và thứ hạng.
- **Cơ cấu sở hữu** ở đầu hồ sơ: nhà nước chi phối / có vốn nhà nước / không có vốn nhà nước, tỷ lệ nước ngoài.
- **Chọn khoảng thời gian** cho biểu đồ (`PeriodToggle`, `utils/period-presets.ts`): 1T/3T/6T/Từ đầu năm/1N/Tất cả cho lãi suất; 3 năm/5 năm/Tất cả cho chỉ tiêu quý. Mốc tính từ ngày có số liệu mới nhất.

## Kết quả thuật toán: cắm vào không cần sửa giao diện

Ba chỗ đang hiện "chưa có kết quả": xếp hạng (trang Tổng quan, Gửi tiết kiệm, Vay), dự báo (hồ sơ ngân hàng), khía cạnh review (hồ sơ ngân hàng). Khi mô hình chốt, pipeline ghi `rankings.csv`, `forecasts.csv`, `app_aspects.csv` vào `data/serving/` đúng schema trong `data/serving/README.md`. Backend nạp ở lần chạy kế tiếp (hoặc bấm "Nạp file mới" ở trang Quản trị) và giao diện tự hiện.

Việc còn lại phía backend khi có thuật toán xếp hạng: tính lại bước cuối của TOPSIS theo mức ưu tiên người dùng chọn. Chỗ đặt: `RankingService` (xem chú thích trong lớp này); trọng số đã được gửi lên trong `SavingsAdviceRequest.weights`.
