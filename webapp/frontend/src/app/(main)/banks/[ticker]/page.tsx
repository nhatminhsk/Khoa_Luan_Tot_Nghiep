import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { LoadingBlock } from "@/components/common/States";
import { BankProfileView } from "@/features/banks/profile/BankProfileView";
import { fetchBank } from "@/lib/http/server-api";

export async function generateMetadata(props: PageProps<"/banks/[ticker]">): Promise<Metadata> {
  const { ticker } = await props.params;
  const bank = await fetchBank(ticker);
  return { title: bank ? `${bank.shortName} (${bank.ticker})` : ticker.toUpperCase() };
}

export default async function BankProfilePage(props: PageProps<"/banks/[ticker]">) {
  const { ticker } = await props.params;
  const bank = await fetchBank(ticker);
  // Mã không thuộc 22 ngân hàng → trang 404. Nếu backend chưa chạy (undefined) thì để phía client báo lỗi và cho thử lại.
  if (bank === null) notFound();

  return (
    <Suspense fallback={<LoadingBlock height={480} />}>
      <BankProfileView ticker={ticker.toUpperCase()} />
    </Suspense>
  );
}
