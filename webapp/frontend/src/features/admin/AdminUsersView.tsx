"use client";

import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Grid,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { IconDevicesOff, IconLock, IconLockOpen, IconMailCheck, IconShieldCheck, IconUserCheck, IconUsers } from "@tabler/icons-react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { StatTile } from "@/components/common/StatTile";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/common/States";
import { useNotify } from "@/components/providers/NotifierProvider";
import { useAuth } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { adminRepository } from "@/repositories/admin.repository";
import type { AdminUser, Role, UpdateUserInput, UserStatus } from "@/types/api";
import { formatDateTime, formatNumber } from "@/utils/format";
import { AdminAuditCard } from "./AdminAuditCard";

const ROLE_LABEL: Record<Role, string> = { USER: "Người dùng", ADMIN: "Quản trị viên" };
const STATUS_LABEL: Record<UserStatus, string> = { ACTIVE: "Đang hoạt động", LOCKED: "Bị khóa" };

/** Thao tác đang chờ xác nhận trong hộp thoại. */
type Pending =
  | { kind: "lock"; user: AdminUser }
  | { kind: "unlock"; user: AdminUser }
  | { kind: "role"; user: AdminUser; role: Role }
  | { kind: "revoke"; user: AdminUser };

/**
 * Quản lý người dùng (quyền USER_MANAGE): thống kê nhanh, tìm kiếm / lọc, khóa – mở tài khoản, đổi vai trò, thu hồi phiên.
 * Khóa hay đổi vai trò đều thu hồi mọi phiên đang mở của người đó; không tự khóa / tự đổi vai trò của chính mình.
 */
export function AdminUsersView() {
  const { can, user: me, isLoading } = useAuth();
  const allowed = can("USER_MANAGE");
  const queryClient = useQueryClient();
  const notify = useNotify();

  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [role, setRole] = useState<Role | "">("");
  const [status, setStatus] = useState<UserStatus | "">("");
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(20);
  const [pending, setPending] = useState<Pending | null>(null);
  const [reason, setReason] = useState("");

  // Gõ tìm kiếm: chờ 300 ms sau lần gõ cuối mới gọi API.
  useEffect(() => {
    const timer = setTimeout(() => setQ(search.trim()), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const params = { q, role: role || undefined, status: status || undefined, page, size };
  const users = useQuery({
    queryKey: queryKeys.adminUsers(params),
    queryFn: () => adminRepository.users(params),
    enabled: allowed,
    placeholderData: keepPreviousData,
  });

  const done = (message: string) => {
    queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    notify(message, "success");
    setPending(null);
    setReason("");
  };
  const update = useMutation({
    mutationFn: ({ id, input }: { id: number; input: UpdateUserInput }) => adminRepository.updateUser(id, input),
    onSuccess: (u) => done(`Đã cập nhật ${u.email}`),
    onError: (e) => notify(errorMessage(e), "error"),
  });
  const revoke = useMutation({
    mutationFn: (id: number) => adminRepository.revokeUserSessions(id),
    onSuccess: () => done("Đã thu hồi mọi phiên đăng nhập"),
    onError: (e) => notify(errorMessage(e), "error"),
  });

  if (isLoading) return <LoadingBlock height={300} />;
  if (!allowed) return <Alert severity="warning">Trang này chỉ dành cho quản trị viên có quyền quản lý người dùng.</Alert>;

  const stats = users.data?.stats;
  const confirm = () => {
    if (!pending) return;
    if (pending.kind === "lock") update.mutate({ id: pending.user.id, input: { status: "LOCKED", reason: reason.trim() } });
    else if (pending.kind === "unlock") update.mutate({ id: pending.user.id, input: { status: "ACTIVE" } });
    else if (pending.kind === "role") update.mutate({ id: pending.user.id, input: { role: pending.role } });
    else revoke.mutate(pending.user.id);
  };

  return (
    <>
      <PageHeader
        title="Quản lý người dùng"
        description="Khóa tài khoản thì người đó không đăng nhập được và mọi phiên đang mở bị thu hồi ngay. Quản trị viên không xem được nhu cầu đã lưu của người dùng."
      />
      <Stack spacing={2.5}>
        <Grid container spacing={2}>
          {[
            { label: "Tổng người dùng", value: stats?.total, icon: <IconUsers size={18} aria-hidden />, tone: "primary" as const },
            { label: "Đang hoạt động", value: stats?.active, icon: <IconUserCheck size={18} aria-hidden />, tone: "success" as const },
            { label: "Bị khóa", value: stats?.locked, icon: <IconLock size={18} aria-hidden />, tone: "warning" as const },
            { label: "Quản trị viên", value: stats?.admins, icon: <IconShieldCheck size={18} aria-hidden />, tone: "secondary" as const },
            { label: "Đã xác minh email", value: stats?.emailVerified, icon: <IconMailCheck size={18} aria-hidden />, tone: "info" as const },
          ].map((tile) => (
            <Grid key={tile.label} size={{ xs: 6, sm: 4, lg: "grow" }}>
              <StatTile label={tile.label} value={tile.value === undefined ? "—" : formatNumber(tile.value, 0)} icon={tile.icon} tone={tile.tone} />
            </Grid>
          ))}
        </Grid>

        <SectionCard title="Danh sách tài khoản" flush>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} useFlexGap sx={{ px: 2, pb: 2 }}>
            <TextField
              size="small"
              label="Tìm theo email hoặc tên"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(0);
              }}
              sx={{ flex: 1, minWidth: 220 }}
            />
            <TextField
              select
              size="small"
              label="Vai trò"
              value={role}
              onChange={(e) => {
                setRole(e.target.value as Role | "");
                setPage(0);
              }}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="">Tất cả</MenuItem>
              <MenuItem value="USER">{ROLE_LABEL.USER}</MenuItem>
              <MenuItem value="ADMIN">{ROLE_LABEL.ADMIN}</MenuItem>
            </TextField>
            <TextField
              select
              size="small"
              label="Trạng thái"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value as UserStatus | "");
                setPage(0);
              }}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value="">Tất cả</MenuItem>
              <MenuItem value="ACTIVE">{STATUS_LABEL.ACTIVE}</MenuItem>
              <MenuItem value="LOCKED">{STATUS_LABEL.LOCKED}</MenuItem>
            </TextField>
          </Stack>

          {users.isError ? (
            <Box sx={{ p: 2.5 }}>
              <ErrorState error={users.error} onRetry={() => users.refetch()} />
            </Box>
          ) : !users.data ? (
            <Box sx={{ p: 2.5 }}>
              <LoadingBlock height={240} />
            </Box>
          ) : users.data.users.items.length === 0 ? (
            <EmptyState title="Không có tài khoản nào khớp bộ lọc" />
          ) : (
            <>
              <TableContainer>
                <Table size="small" aria-label="Danh sách tài khoản">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ pl: 2 }}>Tài khoản</TableCell>
                      <TableCell>Vai trò</TableCell>
                      <TableCell>Trạng thái</TableCell>
                      <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>Đăng nhập gần nhất</TableCell>
                      <TableCell sx={{ display: { xs: "none", lg: "table-cell" } }}>Ngày tạo</TableCell>
                      <TableCell align="right">Thao tác</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {users.data.users.items.map((u) => {
                      const self = u.id === me?.id;
                      return (
                        <TableRow key={u.id} hover>
                          <TableCell sx={{ pl: 2 }}>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {u.displayName}
                              {self && (
                                <Typography component="span" variant="caption" color="text.secondary">
                                  {" "}
                                  (bạn)
                                </Typography>
                              )}
                            </Typography>
                            <Typography variant="caption" color="text.secondary" component="div">
                              {u.email}
                              {u.emailVerified ? " · đã xác minh" : ""}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip size="small" variant="outlined" color={u.role === "ADMIN" ? "secondary" : "default"} label={ROLE_LABEL[u.role]} />
                          </TableCell>
                          <TableCell>
                            <Chip size="small" variant="outlined" color={u.status === "ACTIVE" ? "success" : "warning"} label={STATUS_LABEL[u.status]} />
                          </TableCell>
                          <TableCell sx={{ whiteSpace: "nowrap", display: { xs: "none", md: "table-cell" } }}>
                            {u.lastLoginAt ? formatDateTime(u.lastLoginAt) : "Chưa đăng nhập"}
                          </TableCell>
                          <TableCell sx={{ whiteSpace: "nowrap", display: { xs: "none", lg: "table-cell" } }}>
                            {formatDateTime(u.createdAt)}
                          </TableCell>
                          <TableCell align="right">
                            <Tooltip title={self ? "Không tự khóa hoặc tự đổi vai trò của chính mình" : ""}>
                              <Stack direction="row" spacing={0.5} useFlexGap sx={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
                                {u.status === "ACTIVE" ? (
                                  <Button size="small" color="warning" startIcon={<IconLock size={16} />} disabled={self} onClick={() => setPending({ kind: "lock", user: u })}>
                                    Khóa
                                  </Button>
                                ) : (
                                  <Button size="small" startIcon={<IconLockOpen size={16} />} disabled={self} onClick={() => setPending({ kind: "unlock", user: u })}>
                                    Mở khóa
                                  </Button>
                                )}
                                <Button
                                  size="small"
                                  disabled={self}
                                  onClick={() => setPending({ kind: "role", user: u, role: u.role === "ADMIN" ? "USER" : "ADMIN" })}
                                >
                                  {u.role === "ADMIN" ? "Hạ quyền" : "Cấp quản trị"}
                                </Button>
                                <Button size="small" startIcon={<IconDevicesOff size={16} />} onClick={() => setPending({ kind: "revoke", user: u })}>
                                  Thu hồi phiên
                                </Button>
                              </Stack>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div"
                count={users.data.users.totalItems}
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

        <AdminAuditCard />
      </Stack>

      <ConfirmDialog
        pending={pending}
        reason={reason}
        onReason={setReason}
        busy={update.isPending || revoke.isPending}
        onCancel={() => {
          setPending(null);
          setReason("");
        }}
        onConfirm={confirm}
      />
    </>
  );
}

function ConfirmDialog({
  pending,
  reason,
  onReason,
  busy,
  onCancel,
  onConfirm,
}: {
  pending: Pending | null;
  reason: string;
  onReason: (value: string) => void;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const titleId = useId();
  if (!pending) return null;
  const who = `${pending.user.displayName} (${pending.user.email})`;
  const text = {
    lock: { title: "Khóa tài khoản", body: `${who} sẽ không đăng nhập được và mọi phiên đang mở bị thu hồi ngay.`, action: "Khóa" },
    unlock: { title: "Mở khóa tài khoản", body: `${who} đăng nhập lại được. Các phiên cũ không tự mở lại.`, action: "Mở khóa" },
    role: {
      title: "Đổi vai trò",
      body:
        pending.kind === "role"
          ? `Đổi ${who} thành ${ROLE_LABEL[pending.role].toLowerCase()}. Người đó phải đăng nhập lại để nhận quyền mới.`
          : "",
      action: "Đổi vai trò",
    },
    revoke: { title: "Thu hồi mọi phiên", body: `${who} bị đăng xuất trên mọi thiết bị; tài khoản vẫn dùng được.`, action: "Thu hồi" },
  }[pending.kind];
  const needsReason = pending.kind === "lock";

  return (
    <Dialog open onClose={onCancel} fullWidth maxWidth="xs" aria-labelledby={titleId}>
      <DialogTitle id={titleId}>{text.title}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: needsReason ? 2 : 0 }}>{text.body}</DialogContentText>
        {needsReason && (
          <TextField
            autoFocus
            fullWidth
            size="small"
            label="Lý do khóa (bắt buộc)"
            value={reason}
            onChange={(e) => onReason(e.target.value)}
            slotProps={{ htmlInput: { maxLength: 200 } }}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>Hủy</Button>
        <Button
          variant="contained"
          color={pending.kind === "lock" ? "warning" : "primary"}
          loading={busy}
          disabled={needsReason && reason.trim() === ""}
          onClick={onConfirm}
        >
          {text.action}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
