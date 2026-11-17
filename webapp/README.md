# BankAdvisor — web app hỗ trợ chọn ngân hàng gửi tiết kiệm và vay

Giao diện và API của khóa luận. Frontend **Next.js 16** (App Router, TypeScript, MUI 9), backend **Spring Boot 4.1** (Java 25, JPA, Flyway), CSDL **PostgreSQL 17** khi triển khai (Docker) và H2 chế độ PostgreSQL khi phát triển. Dữ liệu lấy từ pipeline Python của khóa luận qua thư mục `data/serving/`.

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

Kiểm thử: `mvnw.cmd test` (backend: 79 test — 30 test API trên H2, **cùng 30 test đó chạy lại trên PostgreSQL 17.5 thật** (nhúng, `PostgresCompatibilityTests`), 5 test gửi email qua máy chủ SMTP chạy trong bộ nhớ, 14 test đơn vị; test không đọc file `.env` của máy dev nhờ `APP_ENV_FILE`), `npx tsc --noEmit` và `npx eslint src` (frontend), `npm run build` (build production).

Dùng PostgreSQL thay H2 khi chạy trên máy (không phải cài PostgreSQL vào Windows): `docker compose -f docker-compose.db.yml up -d` (từ `webapp`, cần `webapp/.env` có `APP_DB_PASSWORD`), điền cùng `APP_DB_PASSWORD` vào `backend/.env`, rồi chạy backend với `SPRING_PROFILES_ACTIVE=postgres`. CSDL mới trống: Flyway tạo bảng, backend nạp lại CSV; tài khoản trong H2 không tự chuyển sang.

Thử gửi email khi chưa có máy chủ thư: chạy backend với `APP_MAIL_MODE=LOG`. Email, kể cả link xác minh, được in ra log của backend.

## Chạy bằng Docker (ít tài nguyên)

Cần Docker Desktop (Windows) hoặc Docker Engine (VPS Linux). Cài trên Windows (đã làm trên máy này 29/10/2026): `wsl --install --no-distribution` (lỗi bật Virtual Machine Platform → `dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all`, khởi động lại); `%UserProfile%\.wslconfig` giới hạn `memory=3GB`, `processors=4`, `swap=1GB`; Docker Desktop cài theo người dùng + WSL 2; ổ ảo đặt ở `D:\docker` (thư mục phải cấp quyền ghi cho tài khoản thường). Từ thư mục `webapp`:

```
copy .env.example .env        (điền APP_DB_PASSWORD, APP_JWT_SECRET, tài khoản quản trị đầu tiên)
docker compose up -d --build
```

Mở http://localhost:8088. Năm container chạy thường trực (thêm `pipeline` chạy theo lịch), chỉ nginx mở cổng; PostgreSQL nằm trong mạng nội bộ không ra Internet:

| Container | Giới hạn | Ghi chú |
|---|---|---|
| `db` (postgres:17-alpine) | 0,5 CPU · 256 MB | `shared_buffers=48MB`, `max_connections=20`, volume `pgdata` |
| `api` (`backend/Dockerfile`) | 1 CPU · 512 MB | JRE 25 Alpine, `SerialGC`, heap 55% giới hạn; Hikari 5 kết nối; CSV `../data/serving` gắn chỉ đọc |
| `web` (`frontend/Dockerfile`) | 0,5 CPU · 256 MB | Next.js `standalone` (build với `NEXT_OUTPUT=standalone`) |
| `nginx` (`deploy/nginx/*.conf.template`) | 0,25 CPU · 64 MB | `/api/*` → api, còn lại → web; ghi đè `X-Forwarded-For`; giới hạn đăng nhập / đăng ký / quên mật khẩu; chặn `/actuator/`, `/api/v1/internal/` |
| `backup` (`deploy/backup/sao-luu.sh`) | 0,25 CPU · 64 MB | `pg_dump` mỗi ngày lúc `BACKUP_AT` (02:00) vào `webapp/backups`, kiểm lại bằng `pg_restore --list`, giữ 7 bản ngày + 4 bản tuần |
| `certbot` (`deploy/certbot/gia-han.sh`, profile `letsencrypt`) | 0,25 CPU · 128 MB | Chỉ chạy khi có tên miền; 12 giờ kiểm gia hạn một lần, chép chứng chỉ vào `deploy/certs` |
| `pipeline` (`../pipeline/Dockerfile`, profile `job`) | 1 CPU · 1 GB | Python 3.11 + Chromium; `docker compose --profile job run --rm pipeline`. Không có gói riêng `vnstock_data` nên 2 bước giá cổ phiếu / VN-Index báo lỗi và được bỏ qua. Trên máy Windows này vẫn dùng Task Scheduler |

Đo bằng `docker stats` (29/10/2026, Docker Desktop + WSL2 giới hạn 3 GB / 4 CPU trong `%UserProfile%\.wslconfig`, sau ~400 request): API 394 MB, web 184 MB, PostgreSQL 56 MB, nginx 12 MB — tổng ~650 MB. Image: api 429 MB, web 318 MB.

**HTTPS** (chưa có tên miền: chứng chỉ tự ký, trình duyệt sẽ cảnh báo):

```
sh deploy/tao-chung-chi-tu-ky.sh
docker compose -f docker-compose.yml -f docker-compose.https.yml up -d
```

Mở https://localhost:8443; http://localhost:8088 tự chuyển sang HTTPS. Bản HTTPS bật cookie `Secure`, TLS 1.2/1.3, HTTP/2. HSTS mặc định tắt (`HSTS_MAX_AGE=0`) vì với localhost nó ép mọi cổng localhost sang HTTPS.

**Có tên miền** (chứng chỉ Let's Encrypt, tự gia hạn). Trỏ bản ghi A về máy chủ, mở cổng 80 và 443 ra Internet (Let's Encrypt xác minh qua đúng cổng 80), rồi đặt trong `.env`:

```
COMPOSE_PROFILES=letsencrypt
LE_DOMAINS=ten-mien.vn,www.ten-mien.vn
LE_EMAIL=email-lien-he@gmail.com
HTTP_PORT=80
HTTPS_PORT=443
APP_WEB_BASE_URL_HTTPS=https://ten-mien.vn
```

Đặt `LE_EMAIL` nghĩa là đồng ý Subscriber Agreement của Let's Encrypt. Chạy lại đúng lệnh `up` ở trên (nginx vẫn cần chứng chỉ tự ký để khởi động lần đầu). Service `certbot` xin chứng chỉ, chép vào `deploy/certs`, nginx tự tải lại trong vòng 1 phút mà không ngắt kết nối; xem tiến trình bằng `docker compose logs certbot`. Xin lỗi (DNS chưa trỏ, cổng 80 chưa mở) thì certbot đợi 1 giờ mới thử lại để không chạm giới hạn của Let's Encrypt. Trình duyệt báo chứng chỉ hợp lệ rồi mới đặt `HSTS_MAX_AGE=31536000`: bật sớm thì trình duyệt không cho bỏ qua cảnh báo trong suốt thời hạn đó. Dùng Cloudflare thì chọn chế độ SSL Full, không chọn Flexible (cổng 80 chuyển hướng sang HTTPS sẽ lặp vô hạn).

**Sao lưu và khôi phục.** Sao lưu ngay: `docker compose exec backup sh /sao-luu.sh ngay`. Khôi phục một bản (ghi đè dữ liệu hiện tại):

```
docker compose exec -T db pg_restore -U bankadvisor -d bankadvisor --clean --if-exists --no-owner < backups/daily/<tên-file>.dump
```

**Chuyển tài khoản từ H2 sang PostgreSQL**: `python deploy/chuyen-tai-khoan-h2.py` (đọc bản sao file H2, chỉ thêm tài khoản chưa có theo email, kèm nhu cầu đã lưu và danh sách theo dõi; mật khẩu giữ nguyên).

**VPS và CI/CD.** `deploy/vps/cai-dat-vps.sh` cài một VPS Ubuntu 24.04 mới (tường lửa ufw chỉ mở 22/80/443, fail2ban, tự cập nhật bản vá, swap, Docker, systemd timer chạy pipeline 15:30; thêm `LE_DOMAINS` + `LE_EMAIL` để bật Let's Encrypt) — chưa chạy thử trên VPS thật. GitHub Actions: `.github/workflows/webapp-ci.yml` (test backend + frontend + build ảnh khi đẩy lên `main`), `webapp-deploy.yml` (bấm tay để đưa lên VPS qua SSH, cần secret `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`).

## Backend: mỗi tính năng một module, bốn tầng

```
src/main/java/vn/kltn/bankadvisor/
├── common/        ApiResponse (vỏ phản hồi chung), ErrorCode + GlobalExceptionHandler, cấu hình
├── security/      JWT trong cookie httpOnly, kiểm phiên mỗi request, phân quyền 2 vai trò × 4 quyền
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
| `ranking` | `/rankings?purpose=` | Đọc kết quả xếp hạng (gửi: bảng 12 tháng trực tuyến mặc định); `NOT_AVAILABLE` khi chưa có |
| `program` | `/programs`, `/banks/{t}/programs` | Tín dụng chính sách |
| `overview` | `/overview` | Gộp dữ liệu trang Tổng quan |
| `dataset` | `/datasets`, `/admin/imports` | Nạp CSV, nhật ký nạp (ADMIN) |
| `user` | `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/session`, `/auth/me`, `/auth/verify-email`, `/me/email-verification`, `PUT /me/email`, `POST /me/sessions/revoke-all`, `/admin/users` | Xác minh email trước khi nhận thông báo qua email; quản lý người dùng (quyền `USER_MANAGE`) |
| `need`, `watchlist` | `/me/needs`, `/me/watchlist`, `/me/notifications`, `/me/notification-settings`, `/admin/email-queue` | Cần đăng nhập; hàng đợi email chỉ ADMIN |

Mọi phản hồi có dạng `{ "success": true, "data": … }` hoặc `{ "success": false, "errorCode": "…", "message": "…", "fieldErrors": {…} }`.

**Cơ sở dữ liệu.** Schema ở `src/main/resources/db/migration` (Flyway), viết cú pháp chung H2/PostgreSQL. Ba nhóm bảng: dữ liệu dùng chung (nạp từ CSV, chỉ đọc), kết quả thuật toán (rỗng tới khi mô hình chốt), dữ liệu riêng từng người (tài khoản + cài đặt thông báo, nhu cầu, theo dõi, lịch sử thông báo). Không lưu dữ liệu tài chính cá nhân. PostgreSQL: profile `postgres` (`application-postgres.yml`, biến `APP_DB_URL`, `APP_DB_USERNAME`, `APP_DB_PASSWORD`, `APP_DB_POOL_SIZE`); cùng một bộ migration V1→V9 chạy trên cả hai CSDL.

**Nạp dữ liệu.** `module/dataset/importer/ServingDatasets.java` là bản đặc tả "file nào → bảng nào, cột nào, kiểu gì". Mỗi file một transaction; file có checksum không đổi thì bỏ qua; mã ngân hàng / chỉ tiêu lạ bị bỏ qua (không lỗi). Nạp xong phát `DatasetImportedEvent` → module `watchlist` tạo thông báo khi lãi suất ngân hàng người dùng theo dõi đổi từ ngưỡng trở lên, hoặc khi có xếp hạng quý mới.

**Thông báo qua email.** Thông báo luôn hiện trong ứng dụng; người dùng chọn kênh "Trong ứng dụng và email" thì nhận thêm một bản qua email.
- `app.mail.mode` (biến `APP_MAIL_MODE`): `OFF` tắt (mặc định, giao diện khóa lựa chọn email), `LOG` in email ra log (thử khi chưa có máy chủ thư), `SMTP` gửi thật (`APP_SMTP_*`, cổng 587, bắt buộc STARTTLS và kiểm tra chứng chỉ máy chủ). Xem `.env.example`.
- Phải **xác minh email** trước khi chọn kênh email, vì đăng ký không kiểm tra email: nếu không xác minh, ai cũng có thể dùng hệ thống gửi thư tới địa chỉ người khác. Email xác minh có hai cách: **mã 6 số** (nhập ở trang Theo dõi; hiệu lực 15 phút, sai 5 lần thì hủy; lưu băm BCrypt) — dùng được khi đọc thư trên điện thoại — và **link** (hạn 24 giờ; trỏ về `APP_WEB_BASE_URL`, nên khi chạy trên `localhost` chỉ mở được trên chính máy đó). Gửi lại cách nhau tối thiểu 60 giây. Token trong link ký bằng khóa riêng suy ra từ khóa phiên, nên không dùng làm cookie đăng nhập được.
- Gõ nhầm email: trang Đăng ký gợi ý sửa tên miền phổ biến bị gõ nhầm (`gamil.com` → `gmail.com`); người dùng tự **đổi email** được (`PUT /me/email`, cần mật khẩu hiện tại), email mới phải xác minh lại.
- **Hàng đợi (outbox) trên bảng `notification`:** khi tạo thông báo cho người chọn email, dòng đó có `email_status = PENDING`. `NotificationEmailDispatcher` quét mỗi phút, gom thông báo theo người nhận (mỗi người một email), gửi ngoài transaction CSDL, rồi ghi `SENT`; lỗi thì thử lại sau 5, 10 phút, hết 3 lần thì `FAILED` kèm lỗi cuối. Thông báo đã đọc trong ứng dụng, hoặc người dùng đã tắt email trước khi tới lượt, thì `SKIPPED`. Trang Quản trị có mục "Email thông báo": số email theo trạng thái, lỗi gần nhất, nút gửi ngay.
- Thiết kế cho một tiến trình backend. Chạy nhiều bản thì cần khóa phân tán (ShedLock) hoặc `SELECT … FOR UPDATE SKIP LOCKED` trên PostgreSQL.

**Bảo mật.**
- **Phân quyền** (RBAC tĩnh trong `Role`): `USER` có `PERSONAL_DATA`; `ADMIN` có thêm `DATA_MANAGE`, `USER_MANAGE`, `EMAIL_MANAGE`. `SecurityConfig` kiểm theo quyền: `/admin/users/**` → `USER_MANAGE`, `/admin/imports/**` → `DATA_MANAGE`, `/admin/email-queue/**` → `EMAIL_MANAGE`, `/admin/**` khác và `/internal/**` → chặn, `/me/**` → `PERSONAL_DATA`. `/auth/me` trả `permissions` để giao diện ẩn / hiện menu (`useAuth().can(...)`).
- **Phiên thu hồi được**: JWT mang `ver = token_version`; `SessionAuthenticationConverter` đọc `app_user` ở mọi request cần đăng nhập, từ chối khi tài khoản bị khóa (403 `ACCOUNT_LOCKED`) hoặc `ver` lệch (401), và cấp quyền theo vai trò **hiện hành**. Khóa, đổi vai trò, "Đăng xuất mọi thiết bị", thu hồi phiên từ trang quản trị đều tăng `token_version`. Hạn phiên: ADMIN 8 giờ (`app.jwt.admin-ttl`), USER 7 ngày.
- **Quản lý người dùng** (`/admin/users`): thống kê, tìm, lọc; khóa (bắt buộc lý do) / mở; đổi vai trò; thu hồi phiên. Không tự sửa mình (`CANNOT_MODIFY_SELF`), không khóa / hạ quyền ADMIN hoạt động cuối (`LAST_ADMIN`).
- **Nhật ký thao tác quản trị** (bảng `admin_audit`, V10): khóa / mở, đổi vai trò, thu hồi phiên, nạp lại dữ liệu, gửi email ngay — ai, lúc nào, với ai, lý do. Ghi cùng transaction với thao tác; xem ở cuối trang Quản lý người dùng (`GET /admin/audit`, quyền `USER_MANAGE`); không có API sửa / xóa.
- **Token CSRF** (double-submit cookie): backend đặt cookie `XSRF-TOKEN` (JavaScript đọc được) ở mọi response (`CsrfCookieFilter`); POST/PUT/PATCH/DELETE phải gửi lại giá trị đó trong header `X-XSRF-TOKEN` (`api-client` tự gửi, gặp `CSRF_TOKEN_INVALID` thì đọc cookie mới và thử lại một lần). Trừ công cụ tính `/advisor/*` (chỉ đọc). Là lớp thứ ba, thêm vào cookie `SameSite=Lax` và CORS.
- **API công khai liệt kê từng nhóm** (`SecurityConfig.PUBLIC_GET`, `PUBLIC_POST`): đường dẫn mới mặc định bị chặn cho tới khi được thêm vào danh sách.
- **Đổi mật khẩu** (`PUT /me/password`, menu tài khoản): cần mật khẩu hiện tại, sai thì tính vào giới hạn đăng nhập sai; thiết bị khác bị đăng xuất, trình duyệt này nhận phiên mới. **Quên mật khẩu** (`/forgot-password` → thư → `/reset-password`): luôn trả cùng kết quả dù email có tài khoản hay không; mỗi email một thư / 60 giây; link là JWT ký bằng khóa riêng, hạn 30 phút, mang dấu vân tay của hash mật khẩu nên chỉ dùng được một lần (không cần bảng token); đặt xong thì thu hồi mọi phiên và ghi email là đã xác minh.
- JWT (HS256) nằm trong cookie `httpOnly`, `SameSite=Lax`; JavaScript không đọc được token; cookie hết hạn cùng token.
- Trình duyệt chỉ gọi API qua proxy của Next.js (cùng origin), nên không cần mở CORS; backend đọc `X-Forwarded-*` (`server.forward-headers-strategy`). Khi triển khai, không mở cổng backend ra ngoài.
- Chống CSRF ba lớp: cookie `SameSite=Lax` không đi kèm POST/PUT/DELETE từ site khác, bộ lọc CORS trả 403 cho mọi request mang `Origin` lạ, và token CSRF ở trên (đều có test).
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
│   ├── (main)/admin/         /admin       Quản trị dữ liệu (quyền DATA_MANAGE)
│   ├── (main)/admin/users/   /admin/users Quản lý người dùng (quyền USER_MANAGE)
│   └── (auth)/login, register, verify-email, forgot-password, reset-password
│                             (verify-email, reset-password: trang mở từ link trong email)
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

## Kết quả thuật toán: xếp hạng tổng hợp (từ 03/11/2026)

Pipeline ghi `rankings.csv` (`python -m serving.rankings`, MCDM × Monte Carlo trên ảnh chụp đã đóng băng; schema trong `data/serving/README.md`). Backend nạp ở lần chạy kế tiếp (hoặc "Nạp file mới" ở trang Quản trị); migration V11 thêm cột kỳ hạn, kênh, mốc tiền, tần suất top 1/top 3.
- Gửi tiết kiệm: `RankingService.savings` chọn bảng đúng kỳ hạn × kênh và mốc tiền lớn nhất không vượt số tiền gửi. Trọng số an toàn tăng theo phần tiền vượt hạn mức bảo hiểm tiền gửi 350 triệu, nên trang không còn thanh "mức ưu tiên" (trường `weights` vẫn nhận để link cũ và nhu cầu đã lưu mở được).
- Vay và Tổng quan: bảng vay; bảng gửi 12 tháng trực tuyến ở trọng số mặc định.
- Kỳ hạn × kênh không có bảng (nguồn lãi không có 9, 13 tháng): `NOT_AVAILABLE` với `reason = TERM_NOT_RANKED`.

Đã gỡ (migration V8, 29/10/2026) vì không thuộc hệ thống gợi ý: điểm / đánh giá ứng dụng ngân hàng (module `app`, 3 bảng) và dự báo chỉ tiêu (module `forecast`, bảng `forecast_point`, tab Dự báo ở hồ sơ ngân hàng); cột `bank.app_name`.
