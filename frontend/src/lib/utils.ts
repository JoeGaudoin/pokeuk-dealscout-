import { clsx, type ClassValue } from "clsx";
import { formatDistanceToNow } from "date-fns";
import type { Platform, Condition } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatPrice(price: number): string {
  return `£${price.toFixed(2)}`;
}

export function formatDealScore(score: number | null): string {
  if (score === null) return "N/A";
  return `${score >= 0 ? "+" : ""}${score.toFixed(1)}%`;
}

export function getDealScoreClass(score: number | null): string {
  if (score === null) return "";
  if (score >= 30) return "deal-score-excellent";
  if (score >= 20) return "deal-score-good";
  if (score >= 10) return "deal-score-fair";
  return "deal-score-poor";
}

export function getPlatformClass(platform: Platform): string {
  return `platform-${platform}`;
}

export function getConditionClass(condition: Condition | null): string {
  if (!condition) return "";
  return `condition-${condition.toLowerCase()}`;
}

export function getPlatformName(platform: Platform): string {
  const names: Record<Platform, string> = {
    ebay: "eBay",
    cardmarket: "Cardmarket",
    vinted: "Vinted",
    facebook: "Facebook",
    magicmadhouse: "Magic Madhouse",
    chaoscards: "Chaos Cards",
  };
  return names[platform] || platform;
}

export function formatTimeAgo(dateString: string): string {
  return formatDistanceToNow(new Date(dateString), { addSuffix: true });
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}
