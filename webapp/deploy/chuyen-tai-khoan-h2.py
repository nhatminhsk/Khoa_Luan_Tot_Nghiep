from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WEBAPP = Path(__file__).resolve().parents[1]
DEFAULT_H2 = WEBAPP / "backend" / ".data" / "bank-advisor.mv.db"
TABLES = ["app_user", "saved_need", "watch_item"]

# Cột đích và biểu thức lấy từ bảng tạm t (mọi cột tạm là text). Cột H2 chưa có (CSDL cũ trước V9) dùng giá trị mặc định.
USER_COLUMNS = {
    "email": "lower(t.email)",
    "password_hash": "t.password_hash",
    "display_name": "t.display_name",
    "role": "t.role",
    "notify_rate_change": "coalesce(nullif(t.notify_rate_change, '')::boolean, true)",
    "notify_new_ranking": "coalesce(nullif(t.notify_new_ranking, '')::boolean, true)",
    "notify_channel": "coalesce(nullif(t.notify_channel, ''), 'IN_APP')",
    "created_at": "t.created_at::timestamptz",
    "email_verified_at": "nullif(t.email_verified_at, '')::timestamptz",
    "status": "coalesce(nullif(t.status, ''), 'ACTIVE')",
    "last_login_at": "nullif(t.last_login_at, '')::timestamptz",
}
NEED_COLUMNS = ["purpose", "label", "amount", "term_months", "channel", "loan_purpose", "repayment",
                "weight_rate", "weight_safety", "weight_app", "created_at", "updated_at"]
NEED_TYPES = {"amount": "bigint", "term_months": "integer", "weight_rate": "integer", "weight_safety": "integer",
              "weight_app": "integer", "created_at": "timestamptz", "updated_at": "timestamptz"}


def h2_jar() -> Path:
    jars = sorted((Path.home() / ".m2" / "repository" / "com" / "h2database" / "h2").glob("*/h2-*.jar"))
    jars = [j for j in jars if "sources" not in j.name]
    if not jars:
        sys.exit("Không thấy thư viện H2 trong ~/.m2 — chạy backend (mvnw) một lần để Maven tải về.")
    return jars[-1]


def export_csv(h2_file: Path, out: Path) -> dict[str, list[str]]:
    copy = out / "ban-sao.mv.db"
    shutil.copy2(h2_file, copy)
    url = f"jdbc:h2:file:{(out / 'ban-sao').as_posix()};MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;ACCESS_MODE_DATA=r"
    sql = ";".join(f"CALL CSVWRITE('{(out / (t + '.csv')).as_posix()}', 'SELECT * FROM {t}', 'charset=UTF-8')"
                   for t in TABLES)
    subprocess.run(["java", "-cp", str(h2_jar()), "org.h2.tools.Shell", "-url", url, "-user", "sa", "-password", "",
                    "-sql", sql], check=True, capture_output=True)
    columns = {}
    for t in TABLES:
        with open(out / f"{t}.csv", encoding="utf-8", newline="") as f:
            columns[t] = [c.lower() for c in next(csv.reader(f))]
    return columns


def build_sql(columns: dict[str, list[str]]) -> str:
    def temp_table(t: str) -> str:
        cols = ", ".join(f'"{c}" text' for c in columns[t])
        return (f"CREATE TEMP TABLE h2_{t} ({cols}) ON COMMIT DROP;\n"
                f"COPY h2_{t} FROM '/tmp/h2/{t}.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');\n")

    user_cols = [c for c in USER_COLUMNS if c in columns["app_user"] or c in ("status", "notify_channel",
                                                                                 "notify_rate_change", "notify_new_ranking")]
    user_exprs = [USER_COLUMNS[c] if c in columns["app_user"] else USER_COLUMNS[c].replace("t." + c, "NULL")
                  for c in user_cols]
    need_cols = [c for c in NEED_COLUMNS if c in columns["saved_need"]]
    need_exprs = [f"nullif(s.{c}, '')::{NEED_TYPES[c]}" if c in NEED_TYPES else f"nullif(s.{c}, '')" for c in need_cols]
    return (
        "BEGIN;\n"
        + "".join(temp_table(t) for t in TABLES)
        + "CREATE TEMP TABLE moved (old_id text, new_id bigint) ON COMMIT DROP;\n"
        + f"WITH ins AS (\n  INSERT INTO app_user ({', '.join(user_cols)})\n"
        + f"  SELECT {', '.join(user_exprs)} FROM h2_app_user t\n"
        + "  WHERE NOT EXISTS (SELECT 1 FROM app_user u WHERE u.email = lower(t.email))\n"
        + "  RETURNING id, email)\n"
        + "INSERT INTO moved SELECT t.id, ins.id FROM ins JOIN h2_app_user t ON lower(t.email) = ins.email;\n"
        + f"INSERT INTO saved_need (user_id, {', '.join(need_cols)})\n"
        + f"  SELECT m.new_id, {', '.join(need_exprs)} FROM h2_saved_need s JOIN moved m ON m.old_id = s.user_id;\n"
        + "INSERT INTO watch_item (user_id, ticker, rate_threshold, created_at)\n"
        + "  SELECT m.new_id, w.ticker, w.rate_threshold::numeric, w.created_at::timestamptz\n"
        + "  FROM h2_watch_item w JOIN moved m ON m.old_id = w.user_id\n"
        + "  WHERE EXISTS (SELECT 1 FROM bank b WHERE b.ticker = w.ticker)\n"
        + "  ON CONFLICT (user_id, ticker) DO NOTHING;\n"
        + "SELECT 'Tài khoản đã chuyển: ' || count(*) FROM moved;\n"
        + "SELECT 'Nhu cầu đã chuyển: ' || count(*) FROM saved_need WHERE user_id IN (SELECT new_id FROM moved);\n"
        + "SELECT 'Mục theo dõi đã chuyển: ' || count(*) FROM watch_item WHERE user_id IN (SELECT new_id FROM moved);\n"
        + "COMMIT;\n"
    )


def compose(*args: str, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", *args], cwd=WEBAPP, check=True, **kwargs)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    h2_file = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_H2
    if not h2_file.exists():
        sys.exit(f"Không thấy file H2: {h2_file}")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        columns = export_csv(h2_file, out)
        with open(out / "app_user.csv", encoding="utf-8") as f:
            print(f"Đọc từ bản sao {h2_file.name}: {sum(1 for _ in f) - 1} tài khoản")
        container = compose("ps", "-q", "db", capture_output=True, text=True).stdout.strip()
        if not container:
            sys.exit("Container db chưa chạy: docker compose up -d")
        compose("exec", "-T", "db", "mkdir", "-p", "/tmp/h2")
        for t in TABLES:
            subprocess.run(["docker", "cp", str(out / f"{t}.csv"), f"{container}:/tmp/h2/{t}.csv"], check=True,
                           capture_output=True)
        try:
            result = compose("exec", "-T", "db", "psql", "-U", "bankadvisor", "-d", "bankadvisor", "-v",
                             "ON_ERROR_STOP=1", "-At", input=build_sql(columns), capture_output=True, text=True,
                             encoding="utf-8")
            print("\n".join(line for line in result.stdout.splitlines() if ":" in line))
        except subprocess.CalledProcessError as e:
            sys.exit("Chuyển thất bại, không đổi gì trong PostgreSQL:\n" + (e.stderr or ""))
        finally:
            compose("exec", "-T", "db", "rm", "-rf", "/tmp/h2")


if __name__ == "__main__":
    main()
