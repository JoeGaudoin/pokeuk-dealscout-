"use client";

import Image from "next/image";
import { ExternalLink, TrendingUp, Package } from "lucide-react";
import type { Deal } from "@/types";
import {
  formatPrice,
  formatDealScore,
  getDealScoreClass,
  getPlatformClass,
  getPlatformName,
  getConditionClass,
  formatTimeAgo,
  truncate,
} from "@/lib/utils";

interface DealCardProps {
  deal: Deal;
}

export function DealCard({ deal }: DealCardProps) {
  const dealScoreClass = getDealScoreClass(deal.deal_score);
  const platformClass = getPlatformClass(deal.platform);
  const conditionClass = getConditionClass(deal.condition);

  return (
    <div className="bg-pokemon-dark rounded-lg overflow-hidden border border-gray-800 hover:border-pokemon-yellow transition-colors">
      {/* Image */}
      <div className="relative h-48 bg-gray-900">
        {deal.image_url ? (
          <Image
            src={deal.image_url}
            alt={deal.title}
            fill
            className="object-contain p-2"
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <Package className="w-16 h-16 text-gray-700" />
          </div>
        )}

        {/* Deal Score Badge */}
        {deal.deal_score !== null && (
          <div
            className={`absolute top-2 right-2 px-2 py-1 rounded text-sm font-bold ${dealScoreClass} bg-black/70`}
          >
            {formatDealScore(deal.deal_score)}
          </div>
        )}

        {/* Platform Badge */}
        <div
          className={`absolute top-2 left-2 px-2 py-1 rounded text-xs font-medium ${platformClass}`}
        >
          {getPlatformName(deal.platform)}
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="font-medium text-sm mb-2 line-clamp-2" title={deal.title}>
          {truncate(deal.title, 60)}
        </h3>

        {/* Prices */}
        <div className="flex items-baseline gap-2 mb-2">
          <span className="text-xl font-bold text-pokemon-yellow">
            {formatPrice(deal.listing_price)}
          </span>
          {deal.market_value && (
            <span className="text-sm text-gray-400 line-through">
              {formatPrice(deal.market_value)}
            </span>
          )}
        </div>

        {/* Details */}
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-3">
          {deal.condition && (
            <span className={`px-2 py-0.5 rounded ${conditionClass}`}>
              {deal.condition}
            </span>
          )}
          {deal.shipping_cost > 0 && (
            <span>+{formatPrice(deal.shipping_cost)} shipping</span>
          )}
        </div>

        {/* Profit indicator */}
        {deal.deal_score !== null && deal.market_value && (
          <div className="flex items-center gap-1 text-sm mb-3">
            <TrendingUp className={`w-4 h-4 ${dealScoreClass}`} />
            <span className={dealScoreClass}>
              Potential profit: {formatPrice(deal.market_value - deal.total_cost)}
            </span>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-800">
          <span className="text-xs text-gray-500">
            {formatTimeAgo(deal.found_at)}
          </span>

          {/* Buy Now Button */}
          <a
            href={deal.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 bg-pokemon-yellow text-black px-3 py-1.5 rounded text-sm font-medium hover:bg-yellow-400 transition-colors"
          >
            Buy Now
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </div>
  );
}
