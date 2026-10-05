"use client";

import {
  Box,
  InputAdornment,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TableSortLabel,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { IconSearch } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { Fragment, useMemo, useState } from "react";
import { BankLabel } from "@/components/common/BankLabel";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { useBanks } from "@/hooks/use-banks";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { formatNumber, formatPercent, formatQuarter } from "@/utils/format";
import { formatIndicator } from "@/utils/indicator";

/** Cột chỉ tiêu hiển thị trong bảng (mã trong indicators.csv). */
const COLUMNS = ["car", "npl", "casa", "nim", "roe", "total_assets"] as const;
type SortKey = "ticker" | "rate12" | "app" | (typeof COLUMNS)[number];

export function BankListView() {
  const { banks, isLoading: banksLoading } = useBanks();
  const snapshot = useQuery({ queryKey: queryKeys.indicatorSnapshot, queryFn: marketRepository.indicatorSnapshot });
  const rates = useQuery({ queryKey: queryKeys.depositTable("ONLINE"), queryFn: () => marketRepository.depositTable("ONLINE") });
  const apps = useQuery({ queryKey: queryKeys.appScores, queryFn: marketRepository.appScores });
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; desc: boolean }>({ key: "ticker", desc: false });

  const indicators = useMemo(
    () => new Map((snapshot.data?.indicators ?? []).map((indicator) => [indicator.code, indicator])),
    [snapshot.data],
  );

  const rows = useMemo(() => {
    const valuesByTicker = new Map((snapshot.data?.rows ?? []).map((row) => [row.ticker, row.values]));
    const rateByTicker = new Map((rates.data?.rows ?? []).map((row) => [row.ticker, row.cells["12"]?.rate ?? null]));
    const appByTicker = new Map((apps.data ?? []).map((a) => [a.ticker, a.googlePlayScore ?? a.appStoreScore]));
    const q = filter.trim().toLowerCase();
    const list = banks
      .filter((b) => !q || [b.ticker, b.shortName, b.fullName].some((v) => v.toLowerCase().includes(q)))
      .map((bank) => ({
        bank,
        values: valuesByTicker.get(bank.ticker) ?? {},
        rate12: rateByTicker.get(bank.ticker) ?? null,
        app: appByTicker.get(bank.ticker) ?? null,
      }));
    const value = (row: (typeof list)[number]): number | string | null => {
      if (sort.key === "ticker") return row.bank.ticker;
      if (sort.key === "rate12") return row.rate12;
      if (sort.key === "app") return row.app;
      return row.values[sort.key]?.value ?? null;
    };
    return list.sort((a, b) => {
      const va = value(a);
      const vb = value(b);
      if (va === null) return 1; // ô trống luôn xuống cuối
      if (vb === null) return -1;
      const cmp = typeof va === "string" ? va.localeCompare(vb as string) : va - (vb as number);
      return sort.desc ? -cmp : cmp;
    });
  }, [banks, snapshot.data, rates.data, apps.data, filter, sort]);

  const sortBy = (key: SortKey) =>
    setSort((current) => (current.key === key ? { key, desc: !current.desc } : { key, desc: key !== "ticker" }));

  const header = (key: SortKey, label: string, tooltip?: string) => (
    <TableCell align={key === "ticker" ? "left" : "right"} sortDirection={sort.key === key ? (sort.desc ? "desc" : "asc") : false}>
      <Tooltip title={tooltip ?? ""} disableHoverListener={!tooltip}>
        <TableSortLabel active={sort.key === key} direction={sort.desc ? "desc" : "asc"} onClick={() => sortBy(key)}>
          {label}
        </TableSortLabel>
      </Tooltip>
    </TableCell>
  );

  const loading = banksLoading || snapshot.isLoading;

  return (
    <>
      <PageHeader
        title="Hồ sơ ngân hàng"
        description={`22 ngân hàng thương mại niêm yết. Chỉ tiêu tài chính lấy số gần nhất trong 4 quý (mới nhất ${formatQuarter(
          snapshot.data?.latestPeriod,
        )}); lãi suất là mức 12 tháng trực tuyến hôm nay. Bấm tiêu đề cột để sắp xếp, bấm tên để xem hồ sơ.`}
      />
      <SectionCard
        flush
        title="Danh sách ngân hàng"
        action={
          <TextField
            size="small"
            placeholder="Lọc theo mã hoặc tên"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            slotProps={{
              htmlInput: { "aria-label": "Lọc ngân hàng" },
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <IconSearch size={16} aria-hidden />
                  </InputAdornment>
                ),
              },
            }}
            sx={{ width: { xs: 180, sm: 240 } }}
          />
        }
      >
        {snapshot.isError ? (
          <Box sx={{ p: 2.5 }}>
            <ErrorState error={snapshot.error} onRetry={() => snapshot.refetch()} />
          </Box>
        ) : loading ? (
          <Box sx={{ p: 2.5 }}>
            <LoadingBlock height={520} />
          </Box>
        ) : rows.length === 0 ? (
          <EmptyState title="Không có ngân hàng khớp bộ lọc" />
        ) : (
          <TableContainer>
            <Table
              size="small"
              aria-label="Chỉ tiêu chính của 22 ngân hàng"
              sx={{ "& th, & td": { px: 1.25 }, "& th:first-of-type, & td:first-of-type": { pl: 2.5 } }}
            >
              <TableHead>
                <TableRow>
                  {header("ticker", "Ngân hàng")}
                  {header("rate12", "Lãi 12T", "Lãi suất 12 tháng trực tuyến hôm nay")}
                  {COLUMNS.map((code) => {
                    const indicator = indicators.get(code);
                    return (
                      <Fragment key={code}>
                        {header(code, shortLabel(code, indicator?.name), indicator?.description ?? undefined)}
                      </Fragment>
                    );
                  })}
                  {header("app", "Điểm app", "Điểm trên Google Play (không có thì App Store)")}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map(({ bank, values, rate12, app }) => (
                  <TableRow key={bank.ticker} hover>
                    <TableCell>
                      <BankLabel ticker={bank.ticker} shortName={bank.shortName} />
                    </TableCell>
                    <TableCell align="right" sx={{ fontWeight: 600 }}>
                      {formatPercent(rate12)}
                    </TableCell>
                    {COLUMNS.map((code) => {
                      const cell = values[code];
                      const indicator = indicators.get(code);
                      const stale = cell && cell.period !== snapshot.data?.latestPeriod;
                      return (
                        <TableCell key={code} align="right">
                          {cell ? formatIndicator(cell.value, indicator?.unit ?? "PERCENT") : "—"}
                          {stale && (
                            <Typography variant="caption" color="text.secondary" component="div">
                              {formatQuarter(cell.period)}
                            </Typography>
                          )}
                        </TableCell>
                      );
                    })}
                    <TableCell align="right">{formatNumber(app, 1)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </SectionCard>
    </>
  );
}

const SHORT_LABELS: Record<string, string> = {
  car: "CAR",
  npl: "Nợ xấu",
  casa: "CASA",
  nim: "NIM",
  roe: "ROE",
  total_assets: "Tổng tài sản",
};

function shortLabel(code: string, fallback?: string): string {
  return SHORT_LABELS[code] ?? fallback ?? code;
}
