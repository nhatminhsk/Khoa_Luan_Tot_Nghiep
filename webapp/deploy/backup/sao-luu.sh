#!/bin/sh
# Sao lưu PostgreSQL bằng pg_dump (định dạng custom, nén sẵn), chạy trong container "backup" của docker-compose.yml.
#
#   sao-luu.sh          chạy mãi: mỗi ngày một lần lúc BACKUP_AT (giờ theo TZ), giữ 7 bản ngày + 4 bản tuần (Chủ nhật)
#   sao-luu.sh ngay     sao lưu một lần rồi thoát (docker compose exec backup sh /sao-luu.sh ngay)
#
# Mỗi bản được kiểm bằng pg_restore --list trước khi giữ lại; bản hỏng bị xóa và báo lỗi ra log.
# Khôi phục: xem webapp/README.md (mục "Sao lưu và khôi phục").
set -eu

: "${PGHOST:=db}" "${PGUSER:=bankadvisor}" "${PGDATABASE:=bankadvisor}" "${BACKUP_AT:=02:00}"
DIR=/backups
KEEP_DAILY=7
KEEP_WEEKLY=4

backup_once() {
    mkdir -p "$DIR/daily" "$DIR/weekly"
    file="$DIR/daily/$PGDATABASE-$(date +%Y%m%d-%H%M).dump"
    if ! pg_dump -Fc -f "$file.tmp" "$PGDATABASE"; then
        rm -f "$file.tmp"
        echo "$(date -Iseconds) LỖI: pg_dump thất bại" >&2
        return 1
    fi
    if ! pg_restore --list "$file.tmp" > /dev/null; then
        rm -f "$file.tmp"
        echo "$(date -Iseconds) LỖI: bản sao lưu không đọc lại được" >&2
        return 1
    fi
    mv "$file.tmp" "$file"
    echo "$(date -Iseconds) Đã sao lưu $(basename "$file") ($(du -h "$file" | cut -f1))"
    # Chủ nhật: giữ thêm một bản tuần.
    if [ "$(date +%u)" = "7" ]; then
        cp "$file" "$DIR/weekly/"
    fi
    # Bản mới nhất đứng đầu; xóa từ bản thứ KEEP+1 trở đi.
    ls -1t "$DIR"/daily/*.dump 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm -f
    ls -1t "$DIR"/weekly/*.dump 2>/dev/null | tail -n +$((KEEP_WEEKLY + 1)) | xargs -r rm -f
}

seconds_until() {
    # Số giây từ bây giờ tới lần kế tiếp của HH:MM (hôm nay nếu chưa qua, không thì ngày mai).
    target_h=$(echo "$1" | cut -d: -f1 | sed 's/^0//')
    target_m=$(echo "$1" | cut -d: -f2 | sed 's/^0//')
    now_h=$(date +%H | sed 's/^0//')
    now_m=$(date +%M | sed 's/^0//')
    now_s=$(date +%S | sed 's/^0//')
    target=$(( ${target_h:-0} * 3600 + ${target_m:-0} * 60 ))
    now=$(( ${now_h:-0} * 3600 + ${now_m:-0} * 60 + ${now_s:-0} ))
    wait=$(( target - now ))
    [ "$wait" -le 0 ] && wait=$(( wait + 86400 ))
    echo "$wait"
}

if [ "${1:-}" = "ngay" ]; then
    backup_once
    exit $?
fi

echo "$(date -Iseconds) Bắt đầu: sao lưu $PGDATABASE mỗi ngày lúc $BACKUP_AT, giữ $KEEP_DAILY bản ngày + $KEEP_WEEKLY bản tuần"
while true; do
    sleep "$(seconds_until "$BACKUP_AT")"
    backup_once || true
    sleep 60
done
