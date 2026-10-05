import type { Metadata } from "next";
import { WatchlistView } from "@/features/watchlist/WatchlistView";

export const metadata: Metadata = { title: "Theo dõi và thông báo" };

export default function WatchlistPage() {
  return <WatchlistView />;
}
