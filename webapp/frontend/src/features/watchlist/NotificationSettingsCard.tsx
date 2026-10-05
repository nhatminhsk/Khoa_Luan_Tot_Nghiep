"use client";

import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  FormControlLabel,
  Radio,
  RadioGroup,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { IconCircleCheck, IconEdit, IconMailForward } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { SectionCard } from "@/components/common/SectionCard";
import { ChangeEmailDialog } from "@/features/account/ChangeEmailDialog";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { useNotify } from "@/components/providers/NotifierProvider";
import { ApiError, errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";
import type { NotificationSettings, NotificationSettingsUpdate, NotifyChannel } from "@/types/api";
import { formatDateTime } from "@/utils/format";

/**
 * Cài đặt thông báo. Thông báo luôn hiện trong ứng dụng; kênh "và email" gửi thêm một bản qua email,
 * chỉ chọn được khi hệ thống bật gửi email và người dùng đã xác minh địa chỉ.
 */
export function NotificationSettingsCard() {
  const queryClient = useQueryClient();
  const notify = useNotify();
  // Người dùng thường bấm link xác minh ở tab khác: quay lại tab này thì tải lại để thấy đã xác minh.
  const settings = useQuery({
    queryKey: queryKeys.notificationSettings,
    queryFn: meRepository.notificationSettings,
    refetchOnWindowFocus: true,
  });
  const [changingEmail, setChangingEmail] = useState(false);
  const save = useMutation({
    mutationFn: (next: NotificationSettingsUpdate) => meRepository.updateNotificationSettings(next),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.notificationSettings, data);
      notify("Đã lưu cài đặt thông báo");
    },
    onError: (e) => notify(errorMessage(e), "error"),
  });

  if (settings.isError) {
    return (
      <SectionCard title="Cài đặt thông báo">
        <ErrorState error={settings.error} onRetry={() => settings.refetch()} />
      </SectionCard>
    );
  }
  if (!settings.data) return <LoadingBlock height={260} />;

  const current = settings.data;
  const change = (patch: Partial<NotificationSettingsUpdate>) =>
    save.mutate({
      notifyRateChange: current.notifyRateChange,
      notifyNewRanking: current.notifyNewRanking,
      channel: current.channel,
      ...patch,
    });
  const canUseEmail = current.emailEnabled && current.emailVerified;

  return (
    <SectionCard id="cai-dat-thong-bao" title="Cài đặt thông báo">
      <Stack spacing={1}>
        <FormControlLabel
          control={<Switch checked={current.notifyRateChange} onChange={(e) => change({ notifyRateChange: e.target.checked })} />}
          label="Báo khi lãi suất ngân hàng đang theo dõi thay đổi"
        />
        <FormControlLabel
          control={<Switch checked={current.notifyNewRanking} onChange={(e) => change({ notifyNewRanking: e.target.checked })} />}
          label="Báo khi có xếp hạng quý mới"
        />
        <Divider sx={{ my: 1 }} />
        <Typography variant="subtitle2" component="h3" id="kenh-nhan">
          Kênh nhận
        </Typography>
        <RadioGroup
          aria-labelledby="kenh-nhan"
          value={current.channel}
          onChange={(e) => change({ channel: e.target.value as NotifyChannel })}
        >
          <FormControlLabel value="IN_APP" control={<Radio />} label="Chỉ trong ứng dụng" disabled={save.isPending} />
          <FormControlLabel
            value="EMAIL"
            control={<Radio />}
            disabled={save.isPending || (!canUseEmail && current.channel !== "EMAIL")}
            label="Trong ứng dụng và email"
          />
        </RadioGroup>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
          <Typography variant="body2" color="text.secondary" sx={{ wordBreak: "break-all" }}>
            Email nhận: <Box component="span" sx={{ color: "text.primary", fontWeight: 600 }}>{current.email}</Box>
          </Typography>
          <Button size="small" startIcon={<IconEdit size={16} />} onClick={() => setChangingEmail(true)} sx={{ minHeight: 36 }}>
            Đổi email
          </Button>
        </Stack>
        <EmailStatus settings={current} />
      </Stack>
      <ChangeEmailDialog open={changingEmail} onClose={() => setChangingEmail(false)} currentEmail={current.email} />
    </SectionCard>
  );
}

function EmailStatus({ settings }: { settings: NotificationSettings }) {
  if (!settings.emailEnabled) {
    return settings.channel === "EMAIL" ? (
      <Alert severity="warning" variant="outlined">
        Hệ thống đang tạm tắt gửi email. Thông báo vẫn hiện trong ứng dụng và ở biểu tượng chuông.
      </Alert>
    ) : (
      <Alert severity="info" variant="outlined">
        Hệ thống chưa bật gửi email. Thông báo hiện trong ứng dụng và ở biểu tượng chuông.
      </Alert>
    );
  }
  if (!settings.emailVerified) return <VerifyEmailPrompt email={settings.email} />;
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center", flexWrap: "wrap", rowGap: 0.5 }}>
      <Chip size="small" color="success" variant="outlined" icon={<IconCircleCheck size={16} />} label="Email đã xác minh" />
      {settings.channel === "EMAIL" && (
        <Typography variant="body2" color="text.secondary">
          Thông báo mới được gom lại, gửi trong vòng vài phút.
        </Typography>
      )}
    </Stack>
  );
}

/**
 * Chưa xác minh: nút gửi email xác minh (có đếm ngược trước khi được gửi lại) và ô nhập mã 6 số. Nhập mã là cách
 * chính khi đọc thư trên điện thoại: link trong thư trỏ về máy chạy web nên có thể không mở được trên điện thoại.
 */
function VerifyEmailPrompt({ email }: { email: string }) {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const status = useQuery({ queryKey: queryKeys.emailVerification, queryFn: meRepository.emailVerification });
  const send = useMutation({
    mutationFn: meRepository.sendEmailVerification,
    onSuccess: (data) => {
      queryClient.setQueryData(queryKeys.emailVerification, data);
      notify(`Đã gửi mã xác minh tới ${data.email}`);
    },
    onError: (e) => {
      notify(errorMessage(e), "error");
      // Lỗi "gửi quá nhanh" kèm thời điểm được gửi lại: tải lại trạng thái để hiện đếm ngược.
      queryClient.invalidateQueries({ queryKey: queryKeys.emailVerification });
    },
  });
  const secondsLeft = useSecondsUntil(status.data?.resendAvailableAt ?? null);
  const sentAt = status.data?.sentAt;
  const codeExpiresAt = status.data?.codeExpiresAt ?? null;

  return (
    <Stack spacing={1.5}>
      <Alert
        severity="info"
        variant="outlined"
        action={
          <Button
            color="inherit"
            size="small"
            startIcon={<IconMailForward size={16} />}
            loading={send.isPending}
            disabled={secondsLeft > 0}
            onClick={() => send.mutate()}
            sx={{ whiteSpace: "nowrap", minHeight: 44 }}
          >
            {secondsLeft > 0 ? `Gửi lại sau ${secondsLeft} giây` : sentAt ? "Gửi lại mã" : "Gửi mã xác minh"}
          </Button>
        }
        sx={{ "& .MuiAlert-action": { alignItems: "center" }, flexWrap: { xs: "wrap", sm: "nowrap" } }}
      >
        {!sentAt
          ? `Xác minh ${email} để nhận thông báo qua email. Hệ thống gửi tới địa chỉ này một mã 6 số.`
          : codeExpiresAt
            ? `Đã gửi tới ${email} một email có mã 6 số. Đọc thư trên điện thoại hay máy tính đều được: nhập mã vào ô bên dưới. Không thấy thư? Kiểm tra mục Thư rác, hoặc bấm “Đổi email” nếu địa chỉ bị gõ nhầm.`
            : `Mã đã gửi tới ${email} hết hạn. Bấm “Gửi lại mã” để nhận mã mới (hoặc bấm link trong thư nếu mở thư trên máy này).`}
      </Alert>
      {codeExpiresAt && <VerifyCodeForm expiresAt={codeExpiresAt} />}
    </Stack>
  );
}

function VerifyCodeForm({ expiresAt }: { expiresAt: string }) {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const digits = code.replace(/\s/g, "");
  const confirm = useMutation({
    mutationFn: () => meRepository.confirmEmailCode(digits),
    onSuccess: () => {
      notify("Đã xác minh email. Bạn có thể chọn nhận thông báo qua email.");
      queryClient.invalidateQueries({ queryKey: queryKeys.notificationSettings });
      queryClient.invalidateQueries({ queryKey: queryKeys.emailVerification });
      queryClient.invalidateQueries({ queryKey: queryKeys.me });
    },
    onError: (e) => {
      setError(errorMessage(e));
      // Mã bị hủy (sai quá số lần) thì tải lại trạng thái để ẩn ô nhập và hiện nút gửi lại.
      if (e instanceof ApiError && e.code === "VERIFICATION_CODE_EXPIRED") {
        queryClient.invalidateQueries({ queryKey: queryKeys.emailVerification });
      }
    },
  });

  return (
    <Stack
      component="form"
      noValidate
      direction={{ xs: "column", sm: "row" }}
      spacing={1.5}
      sx={{ alignItems: { sm: "flex-start" } }}
      onSubmit={(e) => {
        e.preventDefault();
        if (digits.length === 6) confirm.mutate();
      }}
    >
      <TextField
        size="small"
        label="Mã xác minh (6 số)"
        value={code}
        onChange={(e) => {
          setCode(e.target.value.replace(/[^\d ]/g, "").slice(0, 7));
          setError(null);
        }}
        error={error !== null}
        helperText={error ?? `Mã có hiệu lực đến ${formatDateTime(expiresAt)}`}
        slotProps={{ htmlInput: { inputMode: "numeric", autoComplete: "one-time-code", maxLength: 7 } }}
        sx={{ flex: 1 }}
      />
      <Button type="submit" variant="contained" loading={confirm.isPending} disabled={digits.length !== 6} sx={{ minHeight: 40 }}>
        Xác minh
      </Button>
    </Stack>
  );
}

/** Số giây còn lại tới thời điểm {@code targetIso}; tự đếm ngược mỗi giây, 0 khi đã qua hoặc null. */
function useSecondsUntil(targetIso: string | null): number {
  const target = targetIso ? Date.parse(targetIso) : null;
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    if (target === null) return;
    const tick = () => {
      const current = Date.now();
      setNow(current);
      if (current >= target) window.clearInterval(timer);
    };
    const first = window.setTimeout(tick, 0);
    const timer = window.setInterval(tick, 1000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [target]);
  if (target === null || now === null) return 0;
  return Math.max(0, Math.ceil((target - now) / 1000));
}
