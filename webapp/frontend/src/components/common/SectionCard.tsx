import { Box, Card, CardContent, Stack, Tooltip, Typography, type SxProps, type Theme } from "@mui/material";
import { IconInfoCircle } from "@tabler/icons-react";
import type { ReactNode } from "react";

interface SectionCardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  /** Giải thích dài (cách tính, nguồn): hiện trong tooltip của biểu tượng (i) cạnh tiêu đề. */
  info?: string;
  action?: ReactNode;
  children: ReactNode;
  /** Bỏ padding nội dung (bảng tràn sát mép thẻ). */
  flush?: boolean;
  id?: string;
  sx?: SxProps<Theme>;
}

/** Thẻ dashboard: tiêu đề gọn + dòng phụ nhỏ, thao tác (bộ lọc, nút) bên phải cùng hàng. */
export function SectionCard({ title, subtitle, info, action, children, flush, id, sx }: SectionCardProps) {
  return (
    <Card id={id} sx={{ scrollMarginTop: 80, display: "flex", flexDirection: "column", ...sx }}>
      {(title || action) && (
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.5}
          sx={{
            alignItems: { xs: "flex-start", sm: "center" },
            justifyContent: "space-between",
            px: 2.5,
            pt: 2,
            pb: flush ? 1.5 : 0,
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            {title && (
              <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
                <Typography variant="h3" component="h2">
                  {title}
                </Typography>
                {info && (
                  <Tooltip title={info}>
                    <Box
                      component="span"
                      tabIndex={0}
                      aria-label={info}
                      sx={{ display: "inline-flex", color: "text.disabled", cursor: "help", "&:hover": { color: "text.secondary" } }}
                    >
                      <IconInfoCircle size={16} stroke={1.8} aria-hidden />
                    </Box>
                  </Tooltip>
                )}
              </Stack>
            )}
            {subtitle && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25, fontSize: "0.8125rem" }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          {action && <Box sx={{ flexShrink: 0, maxWidth: "100%" }}>{action}</Box>}
        </Stack>
      )}
      {flush ? children : <CardContent sx={{ px: 2.5, pt: 2, flex: 1, "&:last-child": { pb: 2.5 } }}>{children}</CardContent>}
    </Card>
  );
}
