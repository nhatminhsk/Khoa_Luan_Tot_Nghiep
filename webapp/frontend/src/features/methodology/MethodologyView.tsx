"use client";

import {
  Box,
  Chip,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Step,
  StepContent,
  StepLabel,
  Stepper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { IconCircleCheck, IconClockHour4, IconPointFilled } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/common/PageHeader";
import { SectionCard } from "@/components/common/SectionCard";
import { ErrorState, LoadingBlock } from "@/components/common/States";
import { DatasetFreshness } from "@/features/overview/DatasetFreshness";
import { queryKeys } from "@/lib/query/keys";
import { marketRepository } from "@/repositories/market.repository";
import { formatDateTime, formatNumber } from "@/utils/format";
import { DATASET_LABEL } from "@/utils/labels";

const PIPELINE: { title: string; body: string; done: boolean }[] = [
  {
    title: "Thu thập dữ liệu",
    body: "Hằng ngày (15:30): lãi suất huy động từ hai nguồn có đối chiếu chéo, lãi suất cho vay, giá cổ phiếu. Hằng quý: BCTC và thuyết minh. Hằng tháng: CPI, lãi suất điều hành, tăng trưởng tín dụng, cơ cấu sở hữu, review ứng dụng, chương trình tín dụng chính sách.",
    done: true,
  },
  {
    title: "Kiểm tra và làm sạch",
    body: "Chuẩn hóa mã ngân hàng, kỳ báo cáo, đơn vị; sửa lỗi nguồn đã biết theo BCTC gốc; cổng kiểm tra tự động (lãi suất vượt trần NHNN, số nhảy bất thường, thuyết minh không khớp tổng). Giá trị vô lý chuyển thành ô trống, không đoán số.",
    done: true,
  },
  {
    title: "Bảng ngân hàng – quý",
    body: "Gộp mọi nguồn thành một bảng 22 ngân hàng × 34 quý; không điền khuyết ở tầng này.",
    done: true,
  },
  {
    title: "Đặc trưng và chọn lọc",
    body: "120 đặc trưng ứng viên → 88 giữ (28 biến lõi cho dự báo), lọc theo chất lượng dữ liệu và độ ổn định.",
    done: true,
  },
  {
    title: "Khám phá dữ liệu (EDA)",
    body: "Phân rã phương sai giữa/trong ngân hàng, độ trễ theo lãi suất điều hành, mùa vụ trong năm, quan hệ lãi suất – độ an toàn – điểm ứng dụng.",
    done: true,
  },
  {
    title: "Mô hình",
    body: "Dự báo 6 chỉ tiêu 1–4 quý; phân tích review theo 8 khía cạnh (NLP); xếp hạng riêng cho gửi tiết kiệm và vay, có khoảng hạng. Đang hoàn thiện.",
    done: false,
  },
  {
    title: "Đánh giá",
    body: "So sánh với cách dự báo đơn giản (naive, naive có mùa vụ, drift) bằng kiểm định walk-forward; kiểm tra độ nhạy của xếp hạng.",
    done: false,
  },
  {
    title: "Phục vụ",
    body: "Pipeline ghi kết quả dùng chung; giao diện chỉ đọc, không chạy mô hình khi người dùng mở trang. Mỗi ngày so lãi suất để gửi thông báo; mỗi quý chạy lại mô hình khi có BCTC mới.",
    done: true,
  },
];

const LIMITS = [
  "Số liệu chỉ để tham khảo: lãi suất thực tế do ngân hàng quyết định khi giao dịch.",
  "Không đánh giá khả năng vay của từng người (không chấm điểm tín dụng cá nhân).",
  "Không tư vấn đầu tư cổ phiếu: giá cổ phiếu chỉ là dữ liệu đầu vào.",
  "Chỉ gồm 22 ngân hàng niêm yết; không gồm Agribank, Ngân hàng Chính sách xã hội và khách hàng doanh nghiệp.",
  "Lãi suất cho vay là mức bình quân toàn danh mục ngân hàng công bố, không phải lãi suất một khoản vay cụ thể.",
  "Điểm ứng dụng tính trên review có nội dung, lệch về hai cực (1 và 5 sao); không đại diện cho mọi người dùng.",
  "Lãi suất niêm yết cao không đồng nghĩa ngân hàng kém an toàn (với 22 ngân hàng tại một thời điểm, chưa đủ bằng chứng thống kê); vì vậy lãi suất và độ an toàn là hai tiêu chí riêng.",
];

export function MethodologyView() {
  const datasets = useQuery({ queryKey: queryKeys.datasets, queryFn: marketRepository.datasets });

  return (
    <>
      <PageHeader
        title="Phương pháp và dữ liệu"
        description="Nguồn dữ liệu, ngày cập nhật, độ phủ, quy trình xử lý và giới hạn của hệ thống."
      />
      <Grid container spacing={2.5}>
        <Grid size={12}>
          <SectionCard title="Phạm vi">
            <Typography>
              22 ngân hàng thương mại niêm yết: ACB, BAB, BID, BVB, CTG, EIB, HDB, LPB, MBB, MSB, NAB, NVB (NCB), OCB, PGB, SHB,
              SSB, STB, TCB, TPB, VCB, VIB, VPB. Giai đoạn 2019-Q1 → 2026-Q2; đơn vị phân tích là ngân hàng – quý. Lãi suất niêm
              yết và giá cổ phiếu lấy theo ngày. Người dùng mục tiêu: khách hàng cá nhân cần chọn ngân hàng để gửi tiết kiệm
              hoặc vay.
            </Typography>
          </SectionCard>
        </Grid>

        <Grid size={12}>
          <SectionCard title="Nguồn dữ liệu và độ phủ" flush>
            {datasets.isError ? (
              <Box sx={{ p: 2.5 }}>
                <ErrorState error={datasets.error} onRetry={() => datasets.refetch()} />
              </Box>
            ) : (
              <DatasetFreshness datasets={datasets.data?.sources} showRows />
            )}
          </SectionCard>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <SectionCard title="Kết quả thuật toán" subtitle="Giao diện hiện kết quả ngay khi pipeline ghi file tương ứng." flush>
            {!datasets.data ? (
              <Box sx={{ p: 2.5 }}>
                <LoadingBlock height={140} />
              </Box>
            ) : (
              <TableContainer>
                <Table size="small" aria-label="Trạng thái kết quả thuật toán">
                  <TableHead>
                    <TableRow>
                      <TableCell>Kết quả</TableCell>
                      <TableCell>Trạng thái</TableCell>
                      <TableCell align="right">Số dòng</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {datasets.data.algorithmOutputs.map((output) => (
                      <TableRow key={output.dataset}>
                        <TableCell>
                          {DATASET_LABEL[output.dataset] ?? output.dataset}
                          <Typography variant="caption" color="text.secondary" component="div">
                            {output.fileName}
                            {output.lastImportedAt ? ` · nạp ${formatDateTime(output.lastImportedAt)}` : ""}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {output.status === "AVAILABLE" ? (
                            <Chip size="small" color="success" variant="outlined" icon={<IconCircleCheck size={14} />} label="Đã có" />
                          ) : (
                            <Chip size="small" variant="outlined" icon={<IconClockHour4 size={14} />} label="Đang hoàn thiện" />
                          )}
                        </TableCell>
                        <TableCell align="right">{formatNumber(output.rowCount, 0)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </SectionCard>
        </Grid>

        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard title="Giới hạn và ngoài phạm vi">
            <List dense disablePadding>
              {LIMITS.map((text) => (
                <ListItem key={text} disableGutters sx={{ alignItems: "flex-start" }}>
                  <ListItemIcon sx={{ minWidth: 24, mt: 0.75, color: "text.secondary" }}>
                    <IconPointFilled size={10} aria-hidden />
                  </ListItemIcon>
                  <ListItemText primary={text} />
                </ListItem>
              ))}
            </List>
          </SectionCard>
        </Grid>

        <Grid size={12}>
          <SectionCard title="Quy trình xử lý">
            <Stepper orientation="vertical" nonLinear>
              {PIPELINE.map((step) => (
                <Step key={step.title} active completed={step.done} expanded>
                  <StepLabel
                    optional={
                      !step.done && (
                        <Typography variant="caption" color="text.secondary">
                          Đang hoàn thiện
                        </Typography>
                      )
                    }
                  >
                    {step.title}
                  </StepLabel>
                  <StepContent>
                    <Typography variant="body2" color="text.secondary">
                      {step.body}
                    </Typography>
                  </StepContent>
                </Step>
              ))}
            </Stepper>
          </SectionCard>
        </Grid>
      </Grid>
    </>
  );
}
