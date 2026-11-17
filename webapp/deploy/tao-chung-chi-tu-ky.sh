#!/bin/sh
# Tạo chứng chỉ TLS tự ký cho HTTPS khi chưa có tên miền (dùng cho docker-compose.https.yml).
# Trình duyệt sẽ cảnh báo vì chứng chỉ không do tổ chức tin cậy cấp; dữ liệu vẫn được mã hóa trên đường truyền.
# Có tên miền vẫn cần chạy một lần: nginx phải khởi động được thì service certbot mới xác minh tên miền và thay chứng chỉ thật.
#
#   sh deploy/tao-chung-chi-tu-ky.sh                 # cho localhost
#   sh deploy/tao-chung-chi-tu-ky.sh 203.0.113.10    # cho IP của VPS
#
# Cần openssl (có sẵn trong Git Bash trên Windows và trên Ubuntu). Khóa riêng nằm ở deploy/certs/server.key:
# không đưa lên git (.gitignore đã chặn thư mục certs).
set -eu
# Git Bash trên Windows tự đổi "/CN=..." thành đường dẫn Windows; tắt việc đó (không ảnh hưởng Linux).
export MSYS_NO_PATHCONV=1

HOST="${1:-localhost}"
DIR="$(cd "$(dirname "$0")" && pwd)/certs"
mkdir -p "$DIR"

case "$HOST" in
    localhost) SAN="DNS:localhost,IP:127.0.0.1" ;;
    *[!0-9.]*) SAN="DNS:$HOST,DNS:localhost,IP:127.0.0.1" ;;
    *) SAN="IP:$HOST,DNS:localhost,IP:127.0.0.1" ;;
esac

# Đường dẫn tương đối: với MSYS_NO_PATHCONV, openssl trên Windows không hiểu đường dẫn dạng /d/...
cd "$DIR"
openssl req -x509 -newkey rsa:2048 -nodes -days 825 -sha256 \
    -subj "/CN=$HOST/O=BankAdvisor" \
    -addext "subjectAltName=$SAN" \
    -keyout server.key -out server.crt 2> /dev/null
chmod 600 server.key
echo "Đã tạo $DIR/server.crt (hạn 825 ngày, $SAN)"
