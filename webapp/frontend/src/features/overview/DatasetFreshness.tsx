"use client";

import { Box, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";
import { LoadingBlock } from "@/components/common/States";
import type { DatasetSource } from "@/types/api";
import { formatDate, formatMonth, formatNumber, formatQuarter } from "@/utils/format";
import { FREQUENCY_LABEL } from "@/utils/labels";

/** Ngày/tháng/quý mới nhất có số của từng nguồn, hiển thị theo đúng tần suất của nguồn. */
export function formatLastUpdated(source: DatasetSource): string {
  const value = source.lastUpdated;
  if (!value) return "—";
  if (/^\d{4}-Q\d$/.test(value)) return formatQuarter(value);
  if (/^\d{4}-\d{2}$/.test(value)) return formatMonth(value);
  return formatDate(value);
}

export function DatasetFreshness({ datasets, showRows }: { datasets: DatasetSource[] | undefined; showRows?: boolean }) {
  if (!datasets) {
    return (
      <Box sx={{ p: 2.5 }}>
        <LoadingBlock height={200} />
      </Box>
    );
  }
  return (
    <TableContainer>
      <Table size="small" aria-label="Nguồn dữ liệu và ngày cập nhật">
        <TableHead>
          <TableRow>
            <TableCell>Dữ liệu</TableCell>
            <TableCell>Nguồn</TableCell>
            <TableCell>Tần suất</TableCell>
            <TableCell>Mới nhất</TableCell>
            {showRows && <TableCell align="right">Số dòng</TableCell>}
            <TableCell>Độ phủ</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {datasets.map((source) => (
            <TableRow key={source.dataset} hover>
              <TableCell sx={{ fontWeight: 600 }}>{source.name}</TableCell>
              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {source.source ?? "—"}
                </Typography>
              </TableCell>
              <TableCell sx={{ whiteSpace: "nowrap" }}>{FREQUENCY_LABEL[source.frequency] ?? source.frequency}</TableCell>
              <TableCell sx={{ whiteSpace: "nowrap" }}>{formatLastUpdated(source)}</TableCell>
              {showRows && <TableCell align="right">{formatNumber(source.rowCount, 0)}</TableCell>}
              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {source.coverageNote ?? "—"}
                </Typography>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
