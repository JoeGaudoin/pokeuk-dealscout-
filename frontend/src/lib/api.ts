import axios from "axios";
import type {
  Deal,
  DealListResponse,
  SetListResponse,
  Era,
  DealFilters,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Deals API
export async function getDeals(filters: DealFilters = {}): Promise<DealListResponse> {
  const params = new URLSearchParams();

  if (filters.platform) params.append("platform", filters.platform);
  if (filters.condition) params.append("condition", filters.condition);
  if (filters.set_id) params.append("set_id", filters.set_id);
  if (filters.min_price !== undefined)
    params.append("min_price", filters.min_price.toString());
  if (filters.max_price !== undefined)
    params.append("max_price", filters.max_price.toString());
  if (filters.min_deal_score !== undefined)
    params.append("min_deal_score", filters.min_deal_score.toString());

  const response = await api.get<DealListResponse>(`/deals?${params}`);
  return response.data;
}

export async function getRecentDeals(minutes: number = 5): Promise<DealListResponse> {
  const response = await api.get<DealListResponse>(
    `/deals/recent?minutes=${minutes}`
  );
  return response.data;
}

export async function getDeal(id: number): Promise<Deal> {
  const response = await api.get<Deal>(`/deals/${id}`);
  return response.data;
}

export async function triggerRefresh(): Promise<void> {
  await api.post("/deals/refresh");
}

// Sets API
export async function getSets(era?: string): Promise<SetListResponse> {
  const params = era ? `?era=${era}` : "";
  const response = await api.get<SetListResponse>(`/sets${params}`);
  return response.data;
}

export async function getEras(): Promise<{ eras: Era[] }> {
  const response = await api.get<{ eras: Era[] }>("/sets/eras");
  return response.data;
}

// Health API
export async function getHealth(): Promise<{
  status: string;
  services: { api: boolean; postgres: boolean; redis: boolean };
}> {
  const response = await api.get("/health");
  return response.data;
}
