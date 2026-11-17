"use client";

import { useMediaQuery, useTheme } from "@mui/material";
import { useEffect, useRef, useState } from "react";

/**
 * Sau mỗi lần bấm "Xem kết quả": khi kết quả của đúng tiêu chí vừa gửi đã về (không phải dữ liệu cũ giữ chỗ), cuộn tới đầu
 * khối kết quả và chuyển focus vào đó. Chỉ trên điện thoại (dưới sm), nơi thanh lọc xếp dọc che hết màn hình đầu; từ sm
 * thanh lọc chỉ một–hai hàng, kết quả đã nằm ngay dưới nên không cuộn.
 * Gửi lại đúng tiêu chí cũ (dữ liệu đã có trong cache) cũng cuộn, nhờ bộ đếm lượt gửi.
 *
 * @param currentQuery chuỗi truy vấn đang trên URL (searchParams.toString())
 * @param ready dữ liệu của currentQuery đã về thành công: không phải placeholder, không đang tải
 * @param failed lần tải của currentQuery lỗi: bỏ lượt chờ (không cuộn tới khối lỗi, không cuộn trễ khi tự tải lại sau đó)
 */
export function useScrollToResults(currentQuery: string, ready: boolean, failed: boolean) {
  // Ref dạng hàm (lưu phần tử vào state): trả useRef ra ngoài thì view phải đọc `.ref` lúc render, lint React Compiler chặn.
  const [target, setTarget] = useState<HTMLElement | null>(null);
  const pending = useRef<string | null>(null);
  const [submits, setSubmits] = useState(0);
  const theme = useTheme();
  const stacked = useMediaQuery(theme.breakpoints.down("sm"));

  useEffect(() => {
    if (pending.current === null || pending.current !== currentQuery) return;
    if (failed) {
      pending.current = null;
      return;
    }
    if (!ready) return;
    pending.current = null;
    const el = target;
    if (!stacked || !el) return;
    // Nhảy thẳng (không "smooth"): cuộn mượt bị bỏ qua ở một số trình duyệt nhúng, người dùng sẽ không thấy gì xảy ra.
    el.scrollIntoView({ block: "start" });
    el.focus({ preventScroll: true });
  }, [currentQuery, ready, failed, submits, stacked, target]);

  /** Gọi khi gửi form, với chuỗi truy vấn sắp đặt lên URL. */
  const expect = (query: string) => {
    pending.current = query;
    setSubmits((n) => n + 1);
  };
  return [setTarget, expect] as const;
}
