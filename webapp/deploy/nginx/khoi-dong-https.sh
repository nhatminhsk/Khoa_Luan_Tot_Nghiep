#!/bin/sh
# Khởi động nginx ở chế độ HTTPS (docker-compose.https.yml): chạy nền một vòng lặp, thấy server.crt đổi thì tải lại cấu hình.
# Tải lại không ngắt kết nối đang mở, nên gia hạn chứng chỉ không cần khởi động lại container.
# Tải lại lỗi (chứng chỉ không khớp khóa) thì nginx giữ cấu hình cũ và phút sau thử lại.
CRT=/etc/nginx/certs/server.crt

(
    current="$(cksum "$CRT")"
    while sleep 60; do
        latest="$(cksum "$CRT")"
        if [ "$latest" != "$current" ] && nginx -s reload; then
            current="$latest"
        fi
    done
) &

exec /docker-entrypoint.sh nginx -g "daemon off;"
