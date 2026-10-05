-- Dữ liệu dùng chung bổ sung (nạp từ data/serving, chỉ đọc):
--   macro_cpi      lạm phát theo tháng, để tính lãi suất thực = lãi niêm yết − lạm phát so cùng kỳ;
--   bank_ownership tỷ lệ sở hữu nhà nước / nước ngoài của từng ngân hàng (ảnh chụp mới nhất).

-- Cột tháng tên cpi_month vì MONTH là từ khóa của H2.
CREATE TABLE macro_cpi (
    cpi_month       VARCHAR(7)       PRIMARY KEY,
    cpi_yoy_percent DOUBLE PRECISION NOT NULL,
    cpi_mom_percent DOUBLE PRECISION,
    source_url      VARCHAR(500)
);

CREATE TABLE bank_ownership (
    ticker               VARCHAR(8)       PRIMARY KEY REFERENCES bank (ticker),
    as_of_date           DATE             NOT NULL,
    state_own_percent    DOUBLE PRECISION,
    foreign_own_percent  DOUBLE PRECISION,
    foreign_room_percent DOUBLE PRECISION,
    source               VARCHAR(120)
);
