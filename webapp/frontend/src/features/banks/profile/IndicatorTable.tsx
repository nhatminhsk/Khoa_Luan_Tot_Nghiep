"use client";

import { Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { Fragment, useMemo } from "react";
import type { BankIndicators } from "@/types/api";
import { formatQuarter } from "@/utils/format";
import { formatIndicator, rankLabel } from "@/utils/indicator";
import { CAMELS_LABEL, CAMELS_ORDER } from "@/utils/labels";

export type TableMode = "YEAR" | "QUARTER";

const YEAR_COLUMNS = 5;
const QUARTER_COLUMNS = 6;

/**
 * Bảng nhiều kỳ của mọi chỉ tiêu (như "điểm nhấn cơ bản" của các trang dữ liệu tài chính).
 * Theo năm: lấy số quý 4 của mỗi năm (chỉ tiêu cộng 4 quý ở quý 4 là số cả năm); năm đang dở lấy quý mới nhất.
 */
export function IndicatorTable({ data, mode }: { data: BankIndicators; mode: TableMode }) {
  const columns = useMemo(() => tableColumns(data, mode), [data, mode]);
  const lastColumn = columns[columns.length - 1];

  if (columns.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ p: 2.5 }}>
        Chưa có số liệu
      </Typography>
    );
  }

  return (
    <TableContainer sx={{ overflowX: "auto" }}>
      <Table size="small" aria-label={mode === "YEAR" ? "Chỉ tiêu tài chính theo năm" : "Chỉ tiêu tài chính theo quý"}>
        <TableHead>
          <TableRow>
            <TableCell sx={stickyFirst}>Chỉ tiêu</TableCell>
            {columns.map((c) => (
              <TableCell key={c.period} align="right" sx={{ whiteSpace: "nowrap" }}>
                {c.label}
              </TableCell>
            ))}
            <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
              Trung vị 22 NH
            </TableCell>
            <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
              Thứ hạng
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {CAMELS_ORDER.map((group) => {
            const rows = data.indicators.filter((s) => s.indicator.camelsGroup === group);
            if (rows.length === 0) return null;
            return (
              <Fragment key={group}>
                <TableRow>
                  <TableCell colSpan={columns.length + 3} sx={{ bgcolor: "action.hover", fontWeight: 700, py: 0.75 }}>
                    {CAMELS_LABEL[group]}
                  </TableCell>
                </TableRow>
                {rows.map((series) => {
                  const values = new Map(series.points.map((p) => [p.period, p]));
                  const median = values.get(lastColumn.period)?.median ?? null;
                  return (
                    <TableRow key={series.indicator.code} hover>
                      <TableCell component="th" scope="row" sx={stickyFirst}>
                        {series.indicator.name}
                      </TableCell>
                      {columns.map((c) => (
                        <TableCell key={c.period} align="right" sx={{ fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
                          {formatIndicator(values.get(c.period)?.value ?? null, series.indicator.unit)}
                        </TableCell>
                      ))}
                      <TableCell align="right" sx={{ color: "text.secondary", fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
                        {formatIndicator(median, series.indicator.unit)}
                      </TableCell>
                      <TableCell align="right" sx={{ color: "text.secondary", whiteSpace: "nowrap" }}>
                        {series.latest
                          ? `${rankLabel(series.latest.rank, series.latest.bankCount, series.indicator.direction)}${
                              series.latest.period !== lastColumn.period ? ` (${formatQuarter(series.latest.period)})` : ""
                            }`
                          : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

/** Cột chỉ tiêu dính bên trái khi bảng cuộn ngang trên màn hình hẹp. */
const stickyFirst = {
  position: "sticky",
  left: 0,
  zIndex: 1,
  bgcolor: "background.paper",
  minWidth: 180,
} as const;

/** Các kỳ làm cột: kỳ mà ngân hàng có ít nhất một chỉ tiêu. */
export function tableColumns(data: BankIndicators, mode: TableMode): { period: string; label: string }[] {
  const periods = [
    ...new Set(data.indicators.flatMap((s) => s.points.filter((p) => p.value !== null).map((p) => p.period))),
  ].sort();
  if (mode === "QUARTER") {
    return periods.slice(-QUARTER_COLUMNS).map((p) => ({ period: p, label: formatQuarter(p) }));
  }
  const byYear = new Map<string, string[]>();
  for (const p of periods) {
    const year = p.slice(0, 4);
    byYear.set(year, [...(byYear.get(year) ?? []), p]);
  }
  const years = [...byYear.keys()].sort();
  return years
    .flatMap((year, i) => {
      const inYear = byYear.get(year)!;
      const q4 = `${year}-Q4`;
      if (inYear.includes(q4)) return [{ period: q4, label: year }];
      // Chỉ năm gần nhất (đang dở) mới dùng quý mới nhất thay cho quý 4.
      return i === years.length - 1 ? [{ period: inYear[inYear.length - 1], label: formatQuarter(inYear[inYear.length - 1]) }] : [];
    })
    .slice(-YEAR_COLUMNS);
}
