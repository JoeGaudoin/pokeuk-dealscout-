"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getDeals } from "@/lib/api";
import { DealCard } from "./DealCard";
import { Loader2 } from "lucide-react";
import type { DealFilters } from "@/types";

export function DealGrid() {
  const [filters, setFilters] = useState<DealFilters>({
    min_price: 10,
    min_deal_score: 15,
  });

  const {
    data,
    isLoading,
    error,
    isFetching,
  } = useQuery({
    queryKey: ["deals", filters],
    queryFn: () => getDeals(filters),
    refetchInterval: 60000, // Refresh every 60 seconds
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-pokemon-yellow" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-center">
        <p className="text-red-400">Failed to load deals</p>
        <p className="text-sm text-gray-400 mt-1">
          Make sure the API server is running
        </p>
      </div>
    );
  }

  const deals = data?.deals || [];

  return (
    <div>
      {/* Results header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold">
            {deals.length} Deal{deals.length !== 1 ? "s" : ""} Found
          </h2>
          {isFetching && (
            <Loader2 className="w-4 h-4 animate-spin text-pokemon-yellow" />
          )}
        </div>
        <span className="text-sm text-gray-400">
          Sorted by deal score (highest first)
        </span>
      </div>

      {/* Grid */}
      {deals.length === 0 ? (
        <div className="bg-pokemon-dark rounded-lg p-8 text-center">
          <p className="text-gray-400">No deals found matching your filters</p>
          <p className="text-sm text-gray-500 mt-1">
            Try adjusting the filters or wait for new listings
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {deals.map((deal) => (
            <DealCard key={deal.id} deal={deal} />
          ))}
        </div>
      )}
    </div>
  );
}
