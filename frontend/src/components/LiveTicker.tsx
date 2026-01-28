"use client";

import { useQuery } from "@tanstack/react-query";
import { getRecentDeals } from "@/lib/api";
import { Clock, ExternalLink, TrendingUp } from "lucide-react";
import {
  formatPrice,
  formatDealScore,
  getDealScoreClass,
  getPlatformName,
  formatTimeAgo,
  truncate,
} from "@/lib/utils";
import type { Deal } from "@/types";

function TickerItem({ deal }: { deal: Deal }) {
  const dealScoreClass = getDealScoreClass(deal.deal_score);

  return (
    <a
      href={deal.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block p-3 bg-pokemon-darker rounded-lg hover:bg-gray-800 transition-colors animate-slide-in"
    >
      <div className="flex items-start gap-3">
        {/* Image thumbnail */}
        {deal.image_url && (
          <div className="w-12 h-12 rounded bg-gray-900 overflow-hidden flex-shrink-0">
            <img
              src={deal.image_url}
              alt=""
              className="w-full h-full object-contain"
            />
          </div>
        )}

        <div className="flex-1 min-w-0">
          {/* Title */}
          <p className="text-sm font-medium truncate" title={deal.title}>
            {truncate(deal.title, 40)}
          </p>

          {/* Price and score */}
          <div className="flex items-center gap-2 mt-1">
            <span className="text-pokemon-yellow font-bold">
              {formatPrice(deal.listing_price)}
            </span>
            {deal.deal_score !== null && (
              <span className={`text-xs font-medium ${dealScoreClass}`}>
                {formatDealScore(deal.deal_score)}
              </span>
            )}
          </div>

          {/* Meta */}
          <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
            <span>{getPlatformName(deal.platform)}</span>
            <span>·</span>
            <span>{formatTimeAgo(deal.found_at)}</span>
          </div>
        </div>

        <ExternalLink className="w-4 h-4 text-gray-600 flex-shrink-0" />
      </div>
    </a>
  );
}

export function LiveTicker() {
  const { data, isLoading } = useQuery({
    queryKey: ["recent-deals"],
    queryFn: () => getRecentDeals(5),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  const deals = data?.deals || [];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Clock className="w-5 h-5 text-pokemon-yellow" />
            <span className="absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          </div>
          <h2 className="font-semibold">Just Found</h2>
        </div>
        <p className="text-xs text-gray-400 mt-1">Deals from the last 5 minutes</p>
      </div>

      {/* Deals list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <div className="w-6 h-6 border-2 border-pokemon-yellow border-t-transparent rounded-full animate-spin" />
          </div>
        ) : deals.length === 0 ? (
          <div className="text-center py-8">
            <TrendingUp className="w-8 h-8 text-gray-700 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No recent deals</p>
            <p className="text-xs text-gray-600">New deals appear here automatically</p>
          </div>
        ) : (
          deals.map((deal) => <TickerItem key={deal.id} deal={deal} />)
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-800 text-center">
        <p className="text-xs text-gray-500">
          Auto-updates every 30 seconds
        </p>
      </div>
    </div>
  );
}
