"use client";

import {
  Alert,
  Box,
  Button,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { IconDatabaseImport, IconRefresh, IconSend } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { useNotify } from "@/components/providers/NotifierProvider";
import { useAuth } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { adminRepository } from "@/repositories/admin.repository";
import type { ImportSummary, MailMode } from "@/types/api";
import { formatDateTime, formatNumber } from "@/utils/format";

const OUTCOME_LABEL: Record<ImportSummary["outcomes"][number]["status"], { label: string; color: "success" | "default" | "error" }> = {
  IMPORTED: { label: "Đã nạp", color: "success" },
  UNCHANGED: { label: "Không đổi", color: "default" },
  MISSING: { label: "Chưa có file", color: "default" },
  FAILED: { label: "Lỗi", color: "error" },
};

export function AdminView() {
  const { can, isLoading } = useAuth();
  const isAdmin = can("DATA_MANAGE");
  const queryClient = useQueryClient();
  const notify = useNotify();
  const runs = useQuery({ queryKey: queryKeys.importRuns, queryFn: adminRepository.importRuns, enabled: isAdmin });
  const run = useMutation({
    mutationFn: (force: boolean) => adminRepository.runImport(force),
    onSuccess: (summary) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.importRuns });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
      // Dữ liệu dùng chung có thể đã đổi: làm mới mọi truy vấn công khai.
      queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "auth" && q.queryKey[0] !== "admin" });
      const failed = summary.outcomes.filter((o) => o.status === "FAILED").length;
      notify(failed ? `Nạp xong, ${failed} tập lỗi` : "Nạp dữ liệu xong", failed ? "warning" : "success");
    },
    onError: (e) => notify(errorMessage(e), "error"),
  });

  if (isLoading) return <LoadingBlock height={300} />;
  if (!isAdmin) {
    return <Alert severity="warning">Trang này chỉ dành cho quản trị viên.</Alert>;
  }

  return (
    <>
      <PageHeader
        title="Quản trị dữ liệu"
        description="Backend tự nạp data/serving khi khởi động và mỗi ngày lúc 16:00 (sau lần crawl 15:30). Chỉ file có nội dung thay đổi mới được nạp lại."
        actions={
          <>
            <Button variant="contained" startIcon={<IconDatabaseImport size={18} />} loading={run.isPending} onClick={() => run.mutate(false)}>
              Nạp file mới
            </Button>
            <Button variant="outlined" startIcon={<IconRefresh size={18} />} disabled={run.isPending} onClick={() => run.mutate(true)}>
              Nạp lại toàn bộ
            </Button>
          </>
        }
      />
      <Stack spacing={2.5}>
        {run.data && (
          <SectionCard title="Kết quả lượt nạp vừa chạy" flush>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Tập dữ liệu</TableCell>
                    <TableCell>Kết quả</TableCell>
                    <TableCell align="right">Số dòng</TableCell>
                    <TableCell align="right">Bỏ qua</TableCell>
                    <TableCell>Ghi chú</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {run.data.outcomes.map((o) => (
                    <TableRow key={o.dataset}>
                      <TableCell>
                        {o.dataset}
                        <Typography variant="caption" color="text.secondary" component="div">
                          {o.fileName}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip size="small" variant="outlined" color={OUTCOME_LABEL[o.status].color} label={OUTCOME_LABEL[o.status].label} />
                      </TableCell>
                      <TableCell align="right">{o.status === "IMPORTED" ? formatNumber(o.loaded, 0) : "—"}</TableCell>
                      <TableCell align="right">{o.skipped ? formatNumber(o.skipped, 0) : "—"}</TableCell>
                      <TableCell>{o.message ?? ""}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </SectionCard>
        )}

        <SectionCard title="Nhật ký nạp dữ liệu" subtitle="100 lượt gần nhất." flush>
          {runs.isError ? (
            <Box sx={{ p: 2.5 }}>
              <ErrorState error={runs.error} onRetry={() => runs.refetch()} />
            </Box>
          ) : !runs.data ? (
            <Box sx={{ p: 2.5 }}>
              <LoadingBlock height={240} />
            </Box>
          ) : runs.data.length === 0 ? (
            <EmptyState title="Chưa có lượt nạp nào" />
          ) : (
            <TableContainer>
              <Table size="small" aria-label="Nhật ký nạp dữ liệu">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ display: { xs: "none", sm: "table-cell" } }}>Thời gian</TableCell>
                    {/* Ô Thời gian bị ẩn trên điện thoại nên ô này thành cột đầu: giữ lề mép bảng 16px. */}
                    <TableCell sx={{ pl: 2 }}>Tập dữ liệu</TableCell>
                    <TableCell>Trạng thái</TableCell>
                    <TableCell align="right">Số dòng</TableCell>
                    <TableCell>Ghi chú</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {runs.data.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell sx={{ whiteSpace: "nowrap", display: { xs: "none", sm: "table-cell" } }}>
                        {formatDateTime(r.startedAt)}
                      </TableCell>
                      <TableCell sx={{ pl: 2 }}>
                        {r.dataset}
                        {/* Điện thoại: thời gian gộp dưới tên tập dữ liệu để cột Trạng thái hiện trong màn hình. */}
                        <Typography variant="caption" color="text.secondary" sx={{ display: { xs: "block", sm: "none" }, whiteSpace: "nowrap" }}>
                          {formatDateTime(r.startedAt)}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          variant="outlined"
                          color={r.status === "SUCCESS" ? "success" : r.status === "FAILED" ? "error" : "default"}
                          label={r.status === "SUCCESS" ? "Thành công" : r.status === "FAILED" ? "Lỗi" : "Đang chạy"}
                        />
                      </TableCell>
                      <TableCell align="right">{formatNumber(r.rowCount, 0)}</TableCell>
                      <TableCell sx={{ maxWidth: 420 }}>
                        <Typography variant="body2" color="text.secondary">
                          {r.message ?? ""}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </SectionCard>

        <EmailQueueCard />
      </Stack>
    </>
  );
}

const MAIL_MODE_LABEL: Record<MailMode, string> = {
  OFF: "Đang tắt",
  LOG: "Chỉ in ra log (thử nghiệm)",
  SMTP: "Gửi qua SMTP",
};

/** Hàng đợi email thông báo: số thư theo trạng thái, lỗi gần nhất, nút gửi ngay. */
function EmailQueueCard() {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const queue = useQuery({ queryKey: queryKeys.emailQueue, queryFn: adminRepository.emailQueue });
  const dispatch = useMutation({
    mutationFn: adminRepository.dispatchEmails,
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.emailQueue });
      queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
      notify(
        `Đã gửi ${r.emailsSent} email${r.emailsFailed ? `, lỗi ${r.emailsFailed}` : ""}${
          r.notificationsSkipped ? `, bỏ qua ${r.notificationsSkipped} thông báo` : ""
        }`,
        r.emailsFailed ? "warning" : "success",
      );
    },
    onError: (e) => notify(errorMessage(e), "error"),
  });

  const data = queue.data;
  return (
    <SectionCard
      title="Email thông báo"
      subtitle="Thông báo của người chọn nhận qua email được gom theo người và gửi mỗi phút; gửi lỗi thì thử lại tối đa 3 lần."
      action={
        data &&
        data.mode !== "OFF" && (
          <Button size="small" variant="outlined" startIcon={<IconSend size={16} />} loading={dispatch.isPending} onClick={() => dispatch.mutate()}>
            Gửi ngay
          </Button>
        )
      }
    >
      {queue.isError ? (
        <ErrorState error={queue.error} onRetry={() => queue.refetch()} />
      ) : !data ? (
        <LoadingBlock height={120} />
      ) : (
        <Stack spacing={2}>
          <Typography variant="body2">
            Chế độ: <strong>{MAIL_MODE_LABEL[data.mode]}</strong>
            {data.mode === "OFF" && " — đặt APP_MAIL_MODE=LOG hoặc SMTP trong file .env của backend để bật."}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", rowGap: 1 }}>
            <Chip variant="outlined" label={`Chờ gửi: ${formatNumber(data.pending, 0)}`} />
            <Chip variant="outlined" color="success" label={`Đã gửi: ${formatNumber(data.sent, 0)}`} />
            <Chip variant="outlined" color={data.failed ? "error" : "default"} label={`Lỗi: ${formatNumber(data.failed, 0)}`} />
            <Chip variant="outlined" label={`Bỏ qua: ${formatNumber(data.skipped, 0)}`} />
          </Stack>
          {data.recentFailures.length > 0 && (
            <TableContainer>
              <Table size="small" aria-label="Email gửi lỗi gần nhất">
                <TableHead>
                  <TableRow>
                    <TableCell>Thời gian</TableCell>
                    <TableCell>Người nhận</TableCell>
                    <TableCell>Thông báo</TableCell>
                    <TableCell align="right">Số lần thử</TableCell>
                    <TableCell>Lỗi cuối</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.recentFailures.map((f) => (
                    <TableRow key={f.notificationId}>
                      <TableCell sx={{ whiteSpace: "nowrap" }}>{formatDateTime(f.createdAt)}</TableCell>
                      <TableCell>{f.recipient}</TableCell>
                      <TableCell>{f.title}</TableCell>
                      <TableCell align="right">{f.attempts}</TableCell>
                      <TableCell sx={{ maxWidth: 360 }}>
                        <Typography variant="body2" color="text.secondary" sx={{ wordBreak: "break-word" }}>
                          {f.lastError ?? ""}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Stack>
      )}
    </SectionCard>
  );
}
