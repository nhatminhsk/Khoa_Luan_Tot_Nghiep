#!/bin/sh
# Lấy và gia hạn chứng chỉ Let's Encrypt, chạy trong container "certbot" (docker-compose.https.yml, profile letsencrypt).
#
# Mỗi 12 giờ gọi certbot một lần: chưa có chứng chỉ thì xin mới, sắp hết hạn thì gia hạn, còn lại không làm gì.
# Xác minh qua cổng 80 (HTTP-01): certbot ghi tệp vào volume acme-webroot, nginx phục vụ tệp đó tại /.well-known/acme-challenge/.
# Chứng chỉ được chép ra deploy/certs với tên nginx đang đọc; nginx tự tải lại (deploy/nginx/khoi-dong-https.sh).
# Thất bại (DNS chưa trỏ, cổng 80 chưa mở) thì đợi 1 giờ mới thử lại: Let's Encrypt giới hạn số lần xác minh sai.
set -u

: "${LE_DOMAINS:?Đặt LE_DOMAINS (tên miền, nhiều tên cách nhau bằng dấu phẩy) trong webapp/.env}"
: "${LE_EMAIL:?Đặt LE_EMAIL (email liên hệ với Let's Encrypt) trong webapp/.env}"

LIVE=/etc/letsencrypt/live/bankadvisor

copy_certificate() {
    cmp -s "$LIVE/fullchain.pem" /certs/server.crt && return 0
    cp -L "$LIVE/privkey.pem" /certs/server.key.tmp
    cp -L "$LIVE/fullchain.pem" /certs/server.crt.tmp
    chmod 600 /certs/server.key.tmp
    # Khóa trước, chứng chỉ sau: nginx tải lại khi thấy server.crt đổi, lúc đó cặp khóa đã khớp.
    mv /certs/server.key.tmp /certs/server.key
    mv /certs/server.crt.tmp /certs/server.crt
    echo "$(date -Iseconds) Đã chép chứng chỉ mới vào deploy/certs"
}

while true; do
    if certbot certonly --webroot -w /var/www/certbot --cert-name bankadvisor -d "$LE_DOMAINS" \
        --email "$LE_EMAIL" --agree-tos --no-eff-email --non-interactive --keep-until-expiring; then
        copy_certificate
        sleep 43200
    else
        echo "$(date -Iseconds) LỖI: không lấy được chứng chỉ cho $LE_DOMAINS, thử lại sau 1 giờ" >&2
        sleep 3600
    fi
done
