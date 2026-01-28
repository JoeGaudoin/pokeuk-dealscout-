"use client";

import { useQuery } from "@tanstack/react-query";
import { getHealth } from "@/lib/api";
import { Activity, RefreshCw } from "lucide-react";

export function Header() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30000,
  });

  const isHealthy = health?.status === "healthy";

  return (
    <header className="bg-pokemon-dark border-b border-gray-800 px-6 py-4">
      <div className="flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-pokemon-yellow rounded-full flex items-center justify-center">
            <span className="text-black font-bold text-lg">P</span>
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">
              PokeUK <span className="text-pokemon-yellow">DealScout</span>
            </h1>
            <p className="text-xs text-gray-400">
              Real-time Pokemon TCG arbitrage
            </p>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-4">
          {/* Auto-refresh indicator */}
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>Auto-refresh: 60s</span>
          </div>

          {/* Health status */}
          <div className="flex items-center gap-2">
            <Activity
              className={`w-4 h-4 ${
                isHealthy ? "text-green-400" : "text-red-400"
              }`}
            />
            <span
              className={`text-sm ${
                isHealthy ? "text-green-400" : "text-red-400"
              }`}
            >
              {isHealthy ? "Connected" : "Disconnected"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
