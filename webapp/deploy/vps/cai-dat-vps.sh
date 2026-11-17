#!/bin/sh
# Cài BankAdvisor lên một VPS Ubuntu 24.04 mới (2 vCPU / 2 GB RAM trở lên). Chạy bằng root, một lần:
#
#   curl -fsSL https://raw.githubusercontent.com/<chủ repo>/<repo>/main/webapp/deploy/vps/cai-dat-vps.sh -o cai-dat-vps.sh
#   sudo REPO_URL=https://github.com/<chủ repo>/<repo>.git DEPLOY_USER=deploy sh cai-dat-vps.sh
#
# Có tên miền đã trỏ về VPS: thêm LE_DOMAINS=ten-mien LE_EMAIL=email-lien-he để dùng chứng chỉ Let's Encrypt tự gia hạn
# (đặt LE_EMAIL là đồng ý Subscriber Agreement của Let's Encrypt).
#
# Làm gì:
#   1. Cập nhật hệ điều hành, bật tự cập nhật bản vá bảo mật (unattended-upgrades), giờ Asia/Ho_Chi_Minh.
#   2. Tường lửa ufw: chỉ mở SSH, 80, 443. fail2ban chặn dò mật khẩu SSH.
#   3. Thêm swap 2 GB nếu máy chưa có (JVM + Chromium lúc crawl).
#   4. Cài Docker Engine + Compose plugin; tạo tài khoản DEPLOY_USER (trong nhóm docker) để deploy qua SSH.
#   5. Clone repo vào /opt/bankadvisor, tạo webapp/.env với mật khẩu CSDL và khóa JWT ngẫu nhiên.
#   6. Cài 2 systemd timer: pipeline dữ liệu 15:30 hằng ngày (docker compose --profile job run --rm pipeline).
#   7. Khởi động: docker compose up -d (HTTP 80 + HTTPS 443; chưa có tên miền thì dùng chứng chỉ tự ký).
#
# Chưa chạy thử trên VPS thật (máy phát triển là Windows); mới kiểm cú pháp (sh -n).
set -eu

REPO_URL="${REPO_URL:?Đặt REPO_URL=https://github.com/<chủ>/<repo>.git}"
DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR=/opt/bankadvisor
LE_DOMAINS="${LE_DOMAINS:-}"
LE_EMAIL="${LE_EMAIL:-}"
if [ -n "$LE_DOMAINS" ]; then
    : "${LE_EMAIL:?Có LE_DOMAINS thì đặt cả LE_EMAIL}"
    PUBLIC_HOST="${PUBLIC_HOST:-${LE_DOMAINS%%,*}}"
fi
PUBLIC_HOST="${PUBLIC_HOST:-$(curl -fsS https://api.ipify.org || hostname -I | cut -d' ' -f1)}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Chạy bằng root (sudo)." >&2
    exit 1
fi

echo "== 1. Hệ điều hành"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get upgrade -y -q
apt-get install -y -q ca-certificates curl git openssl ufw fail2ban unattended-upgrades
timedatectl set-timezone Asia/Ho_Chi_Minh
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "== 2. Tường lửa"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
systemctl enable --now fail2ban

echo "== 3. Swap"
if [ "$(swapon --show --noheadings | wc -l)" -eq 0 ]; then
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "== 4. Docker"
if ! command -v docker > /dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -q
    apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker
if ! id "$DEPLOY_USER" > /dev/null 2>&1; then
    adduser --disabled-password --gecos "" "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"

echo "== 5. Mã nguồn và cấu hình"
if [ ! -d "$APP_DIR/.git" ]; then
    git clone --depth 1 "$REPO_URL" "$APP_DIR"
fi
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$APP_DIR"
cd "$APP_DIR/webapp"
if [ ! -f .env ]; then
    cp .env.example .env
    sed -i "s|^APP_DB_PASSWORD=.*|APP_DB_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=')|" .env
    sed -i "s|^APP_JWT_SECRET=.*|APP_JWT_SECRET=$(openssl rand -base64 48 | tr -d '/+=')|" .env
    sed -i "s|^HTTP_PORT=.*|HTTP_PORT=80|; s|^HTTPS_PORT=.*|HTTPS_PORT=443|" .env
    sed -i "s|^APP_WEB_BASE_URL_HTTPS=.*|APP_WEB_BASE_URL_HTTPS=https://$PUBLIC_HOST|" .env
    if [ -n "$LE_DOMAINS" ]; then
        sed -i "s|^COMPOSE_PROFILES=.*|COMPOSE_PROFILES=letsencrypt|; s|^LE_DOMAINS=.*|LE_DOMAINS=$LE_DOMAINS|; s|^LE_EMAIL=.*|LE_EMAIL=$LE_EMAIL|" .env
    fi
    chmod 600 .env
    chown "$DEPLOY_USER:$DEPLOY_USER" .env
    echo "   Đã tạo webapp/.env. Điền APP_ADMIN_EMAIL / APP_ADMIN_PASSWORD (và SMTP nếu gửi email) rồi chạy lại bước 7."
fi
if [ ! -f deploy/certs/server.crt ]; then
    sh deploy/tao-chung-chi-tu-ky.sh "$PUBLIC_HOST"
    chown -R "$DEPLOY_USER:$DEPLOY_USER" deploy/certs
fi

echo "== 6. Lịch chạy pipeline"
sed "s|^User=.*|User=$DEPLOY_USER|; s|/opt/bankadvisor|$APP_DIR|" deploy/vps/bankadvisor-pipeline.service \
    > /etc/systemd/system/bankadvisor-pipeline.service
install -m 0644 deploy/vps/bankadvisor-pipeline.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now bankadvisor-pipeline.timer

echo "== 7. Khởi động"
su "$DEPLOY_USER" -c "cd $APP_DIR/webapp && docker compose -f docker-compose.yml -f docker-compose.https.yml up -d --build"
if [ -n "$LE_DOMAINS" ]; then
    echo "Xong. Mở https://$PUBLIC_HOST sau khoảng 2 phút (xem tiến trình: docker compose logs certbot)."
else
    echo "Xong. Mở https://$PUBLIC_HOST (chứng chỉ tự ký: trình duyệt sẽ cảnh báo)."
fi
