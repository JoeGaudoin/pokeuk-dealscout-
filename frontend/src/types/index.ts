// API Types

export type Platform =
  | "ebay"
  | "cardmarket"
  | "vinted"
  | "facebook"
  | "magicmadhouse"
  | "chaoscards";

export type Condition = "NM" | "LP" | "MP" | "HP" | "DMG";

export interface Deal {
  id: number;
  external_id: string;
  platform: Platform;
  url: string;
  card_id: string | null;
  title: string;
  condition: Condition | null;
  listing_price: number;
  shipping_cost: number;
  platform_fee: number;
  total_cost: number;
  market_value: number | null;
  deal_score: number | null;
  seller_name: string | null;
  image_url: string | null;
  is_buy_now: boolean;
  is_active: boolean;
  found_at: string;
  last_seen_at: string;
}

export interface DealListResponse {
  deals: Deal[];
  total: number;
  limit: number;
  offset: number;
}

export interface Card {
  id: string;
  name: string;
  set_id: string;
  set_name: string;
  number: string;
  rarity: string | null;
  image_small: string | null;
  image_large: string | null;
  market_value_nm: number | null;
  market_value_lp: number | null;
  market_value_mp: number | null;
  market_value_hp: number | null;
}

export interface PokemonSet {
  id: string;
  name: string;
  series: string;
  total_cards: number | null;
  release_date: string | null;
  logo_url: string | null;
  symbol_url: string | null;
  era: string | null;
}

export interface SetListResponse {
  sets: PokemonSet[];
  total: number;
}

export interface Era {
  id: string;
  name: string;
  description: string;
  sets: string[];
}

export interface DealFilters {
  platform?: Platform;
  condition?: Condition;
  set_id?: string;
  min_price?: number;
  max_price?: number;
  min_deal_score?: number;
}
