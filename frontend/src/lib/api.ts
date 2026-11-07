import type { EventPage, RegionItem, Stats } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  events(params: Record<string, string | number | boolean | undefined>): Promise<EventPage> {
    const sp = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v === undefined || v === null || v === "") continue;
      sp.set(k, String(v));
    }
    return get<EventPage>(`/api/v1/events?${sp.toString()}`);
  },
  regions(onlyWithEvents = false): Promise<RegionItem[]> {
    return get<RegionItem[]>(`/api/v1/regions?only_with_events=${onlyWithEvents}`);
  },
  stats(): Promise<Stats> {
    return get<Stats>("/api/v1/stats");
  },
};

export function formatPrize(amount: number | null): string {
  if (amount == null) return "";
  return new Intl.NumberFormat("ru-RU").format(amount) + " ₽";
}
