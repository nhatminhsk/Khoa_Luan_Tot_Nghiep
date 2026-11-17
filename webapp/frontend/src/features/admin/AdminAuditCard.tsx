"use client";

import { Box, Chip, Table, TableBody, TableCell, TableContainer, TableHead, TablePagination, TableRow, Typography } from "@mui/material";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { queryKeys } from "@/lib/query/keys";
import { adminRepository } from "@/repositories/admin.repository";
import type { AdminAction } from "@/types/api";
import { formatDateTime } from "@/utils/format";

const ACTION_LABEL: Record<AdminAction, string> = {
  USER_LOCK: "Khóa tài khoản",
  USER_UNLOCK: "Mở khóa",
  ROLE_CHANGE: "Đổi vai trò",
  SESSIONS_REVOKE: "Thu hồi phiên",
  DATA_IMPORT: "Nạp lại dữ liệu",
  EMAIL_DISPATCH: "Gửi email ngay",
};

const ACTION_COLOR: Partial<Record<AdminAction, "warning" | "success" | "secondary" | "info">> = {
  USER_LOCK: "warning",
  USER_UNLOCK: "success",
  ROLE_CHANGE: "secondary",
  DATA_IMPORT: "info",
};

/** Nhật ký thao tác quản trị, mới nhất trước. Chỉ xem: không có thao tác sửa / xóa nhật ký. */
export function AdminAuditCard() {
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(10);
  const audit = useQuery({
    queryKey: queryKeys.adminAudit(page, size),
    queryFn: () => adminRepository.audit(page, size),
    placeholderData: keepPreviousData,
  });

  return (
    <SectionCard
      title="Nhật ký thao tác quản trị"
      subtitle="Ai đã khóa / mở tài khoản, đổi vai trò, thu hồi phiên, nạp lại dữ liệu hay gửi email ngay"
      flush
    >
      {audit.isError ? (
        <Box sx={{ p: 2.5 }}>
          <ErrorState error={audit.error} onRetry={() => audit.refetch()} />
        </Box>
      ) : !audit.data ? (
        <Box sx={{ p: 2.5 }}>
          <LoadingBlock height={160} />
        </Box>
      ) : audit.data.items.length === 0 ? (
        <EmptyState title="Chưa có thao tác quản trị nào" />
      ) : (
        <>
          <TableContainer>
            <Table size="small" aria-label="Nhật ký thao tác quản trị">
              <TableHead>
                <TableRow>
                  <TableCell sx={{ pl: 2 }}>Thời gian</TableCell>
                  <TableCell>Thao tác</TableCell>
                  <TableCell>Đối tượng</TableCell>
                  <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Chi tiết</TableCell>
                  <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>Người làm</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {audit.data.items.map((entry) => (
                  <TableRow key={entry.id} hover>
                    <TableCell sx={{ pl: 2, whiteSpace: "nowrap" }}>{formatDateTime(entry.createdAt)}</TableCell>
                    <TableCell>
                      <Chip size="small" variant="outlined" color={ACTION_COLOR[entry.action] ?? "default"} label={ACTION_LABEL[entry.action]} />
                    </TableCell>
                    <TableCell sx={{ wordBreak: "break-all" }}>
                      {entry.targetEmail ?? "—"}
                      {/* Điện thoại: chi tiết gộp dưới đối tượng vì cột Chi tiết bị ẩn. */}
                      {entry.detail && (
                        <Typography variant="caption" color="text.secondary" component="div" sx={{ display: { md: "none" } }}>
                          {entry.detail}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>{entry.detail ?? "—"}</TableCell>
                    <TableCell sx={{ display: { xs: "none", sm: "table-cell" }, wordBreak: "break-all" }}>{entry.actorEmail}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div"
            count={audit.data.totalItems}
            page={page}
            rowsPerPage={size}
            rowsPerPageOptions={[10, 20, 50]}
            onPageChange={(_, p) => setPage(p)}
            onRowsPerPageChange={(e) => {
              setSize(Number(e.target.value));
              setPage(0);
            }}
            labelRowsPerPage="Số dòng"
            labelDisplayedRows={({ from, to, count }) => `${from}–${to} / ${count}`}
          />
        </>
      )}
    </SectionCard>
  );
}
