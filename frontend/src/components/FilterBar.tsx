"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getEras } from "@/lib/api";
import { Filter, ChevronDown } from "lucide-react";
import type { Platform, Condition, DealFilters } from "@/types";

interface FilterBarProps {
  filters?: DealFilters;
  onFiltersChange?: (filters: DealFilters) => void;
}

const PLATFORMS: { value: Platform | ""; label: string }[] = [
  { value: "", label: "All Platforms" },
  { value: "ebay", label: "eBay UK" },
  { value: "cardmarket", label: "Cardmarket" },
  { value: "vinted", label: "Vinted" },
  { value: "magicmadhouse", label: "Magic Madhouse" },
  { value: "chaoscards", label: "Chaos Cards" },
];

const CONDITIONS: { value: Condition | ""; label: string }[] = [
  { value: "", label: "All Conditions" },
  { value: "NM", label: "Near Mint" },
  { value: "LP", label: "Lightly Played" },
  { value: "MP", label: "Moderately Played" },
  { value: "HP", label: "Heavily Played" },
];

const PRICE_RANGES = [
  { min: 10, max: undefined, label: "£10+" },
  { min: 10, max: 50, label: "£10 - £50" },
  { min: 50, max: 100, label: "£50 - £100" },
  { min: 100, max: 500, label: "£100 - £500" },
  { min: 500, max: undefined, label: "£500+" },
];

export function FilterBar({ filters = {}, onFiltersChange }: FilterBarProps) {
  const [localFilters, setLocalFilters] = useState<DealFilters>(filters);

  const { data: erasData } = useQuery({
    queryKey: ["eras"],
    queryFn: getEras,
  });

  const updateFilter = (key: keyof DealFilters, value: any) => {
    const newFilters = { ...localFilters, [key]: value || undefined };
    setLocalFilters(newFilters);
    onFiltersChange?.(newFilters);
  };

  return (
    <div className="bg-pokemon-dark rounded-lg p-4 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Filter className="w-5 h-5 text-pokemon-yellow" />
        <h2 className="font-semibold">Filters</h2>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        {/* Platform */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Platform</label>
          <select
            value={localFilters.platform || ""}
            onChange={(e) => updateFilter("platform", e.target.value)}
            className="w-full bg-pokemon-darker border border-gray-700 rounded px-3 py-2 text-sm focus:border-pokemon-yellow focus:outline-none"
          >
            {PLATFORMS.map((p) => (
              <option key={p.value} value={p.value}>
                {p.label}
              </option>
            ))}
          </select>
        </div>

        {/* Condition */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Condition</label>
          <select
            value={localFilters.condition || ""}
            onChange={(e) => updateFilter("condition", e.target.value)}
            className="w-full bg-pokemon-darker border border-gray-700 rounded px-3 py-2 text-sm focus:border-pokemon-yellow focus:outline-none"
          >
            {CONDITIONS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* Era */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Era</label>
          <select
            value={localFilters.set_id || ""}
            onChange={(e) => updateFilter("set_id", e.target.value)}
            className="w-full bg-pokemon-darker border border-gray-700 rounded px-3 py-2 text-sm focus:border-pokemon-yellow focus:outline-none"
          >
            <option value="">All Eras</option>
            {erasData?.eras.map((era) => (
              <option key={era.id} value={era.id}>
                {era.name}
              </option>
            ))}
          </select>
        </div>

        {/* Min Price */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Min Price</label>
          <input
            type="number"
            value={localFilters.min_price || ""}
            onChange={(e) =>
              updateFilter("min_price", e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="£10"
            className="w-full bg-pokemon-darker border border-gray-700 rounded px-3 py-2 text-sm focus:border-pokemon-yellow focus:outline-none"
          />
        </div>

        {/* Max Price */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">Max Price</label>
          <input
            type="number"
            value={localFilters.max_price || ""}
            onChange={(e) =>
              updateFilter("max_price", e.target.value ? Number(e.target.value) : undefined)
            }
            placeholder="No limit"
            className="w-full bg-pokemon-darker border border-gray-700 rounded px-3 py-2 text-sm focus:border-pokemon-yellow focus:outline-none"
          />
        </div>

        {/* Min Deal Score */}
        <div>
          <label className="block text-xs text-gray-400 mb-1">
            Min Deal Score
          </label>
          <input
            type="number"
            value={localFilters.min_deal_score || ""}
            onChange={(e) =>
              updateFilter(
                "min_deal_score",
                e.target.value ? Number(e.target.value) : undefined
              )
            }
            placeholder="15%"
            className="w-full bg-pokemon-darker border border-gray-700 rounded px-3 py-2 text-sm focus:border-pokemon-yellow focus:outline-none"
          />
        </div>
      </div>
    </div>
  );
}
