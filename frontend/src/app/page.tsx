import { Header } from "@/components/Header";
import { DealGrid } from "@/components/DealGrid";
import { LiveTicker } from "@/components/LiveTicker";
import { FilterBar } from "@/components/FilterBar";

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 flex">
        {/* Main content */}
        <div className="flex-1 p-6">
          <FilterBar />
          <DealGrid />
        </div>

        {/* Live Ticker Sidebar */}
        <aside className="w-80 border-l border-gray-800 bg-pokemon-dark">
          <LiveTicker />
        </aside>
      </main>
    </div>
  );
}
