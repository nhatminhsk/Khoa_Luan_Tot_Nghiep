"use client";

import { Button } from "@mui/material";
import { IconStar, IconStarFilled } from "@tabler/icons-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useNotify } from "@/components/providers/NotifierProvider";
import { useAuth } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/http/api-error";
import { queryKeys } from "@/lib/query/keys";
import { meRepository } from "@/repositories/me.repository";

/** Nút theo dõi / bỏ theo dõi một ngân hàng (báo khi lãi suất đổi). */
export function WatchButton({ ticker, shortName }: { ticker: string; shortName: string }) {
  const { isAuthenticated } = useAuth();
  const pathname = usePathname();
  const notify = useNotify();
  const queryClient = useQueryClient();
  const watchlist = useQuery({ queryKey: queryKeys.watchlist, queryFn: meRepository.watchlist, enabled: isAuthenticated });
  const watched = watchlist.data?.some((item) => item.ticker === ticker) ?? false;

  const toggle = useMutation({
    mutationFn: async () => {
      if (watched) await meRepository.unwatch(ticker);
      else await meRepository.watch(ticker);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.watchlist });
      notify(watched ? `Đã bỏ theo dõi ${shortName}` : `Đang theo dõi ${shortName}. Bạn sẽ nhận thông báo khi lãi suất đổi.`);
    },
    onError: (error) => notify(errorMessage(error), "error"),
  });

  if (!isAuthenticated) {
    return (
      <Button component={Link} href={`/login?next=${encodeURIComponent(pathname)}`} variant="outlined" startIcon={<IconStar size={18} />}>
        Theo dõi
      </Button>
    );
  }

  return (
    <Button
      variant={watched ? "contained" : "outlined"}
      startIcon={watched ? <IconStarFilled size={18} /> : <IconStar size={18} />}
      onClick={() => toggle.mutate()}
      loading={toggle.isPending || watchlist.isLoading}
      aria-pressed={watched}
    >
      {watched ? "Đang theo dõi" : "Theo dõi"}
    </Button>
  );
}
