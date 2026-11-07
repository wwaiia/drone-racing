"use client";

import { useEffect, useMemo, useState } from "react";
import EventCard from "@/components/EventCard";
import RegionPicker from "@/components/RegionPicker";
import { api } from "@/lib/api";
import type { EventItem, RegionItem, Stats } from "@/lib/types";

type Mode = "by_region" | "national";

const STATUS_FILTERS = [
  { value: "", label: "Все статусы" },
  { value: "registration_open", label: "Регистрация открыта" },
  { value: "anons", label: "Анонс" },
];

export default function Home() {
  const [mode, setMode] = useState<Mode>("by_region");
  const [regions, setRegions] = useState<RegionItem[]>([]);
  const [regionId, setRegionId] = useState<number | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.regions(true).then(setRegions).catch(() => {});
    api.stats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .events({
        mode: mode,
        region_id: regionId ?? undefined,
        status: status || undefined,
      })
      .then((p) => {
        setEvents(p.items);
        setTotal(p.total);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [mode, regionId, status]);

  const selectedRegion = useMemo(
    () => regions.find((r) => r.id === regionId) ?? null,
    [regions, regionId],
  );

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-4 pb-16 sm:px-6">
      <header className="pt-10 pb-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.25em] text-amber-400">
              Drone Racing Events
            </p>
            <h1 className="text-3xl font-extrabold tracking-tight text-zinc-100 sm:text-4xl">
              Гонки дронов — ближайшие старты
            </h1>
            <p className="mt-2 max-w-xl text-sm text-zinc-400">
              Агрегатор соревнований по дрон-рейсингу из ФГДР и региональных сообществ.
              {stats && (
                <>
                  {" "}Сейчас в базе: <b className="text-amber-400">{stats.upcoming_total}</b> предстоящих
                  стартов в <b className="text-amber-400">{stats.regions_with_events}</b> регионах.
                </>
              )}
            </p>
          </div>
        </div>

        <nav className="mt-7 inline-flex rounded-2xl border border-zinc-800 bg-[#1b1b1f] p-1">
          <button
            onClick={() => setMode("by_region")}
            className={`rounded-xl px-5 py-2.5 text-sm font-bold transition ${
              mode === "by_region" ? "bg-amber-400 text-black" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            По регионам
          </button>
          <button
            onClick={() => setMode("national")}
            className={`rounded-xl px-5 py-2.5 text-sm font-bold transition ${
              mode === "national" ? "bg-amber-400 text-black" : "text-zinc-400 hover:text-zinc-200"
            }`}
          >
            Общие соревнования
          </button>
        </nav>
      </header>

      <section className="grid gap-4 rounded-2xl border border-zinc-800 bg-[#1b1b1f] p-5 sm:grid-cols-2">
        <div>
          <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-zinc-500">
            Область / регион
          </label>
          <RegionPicker regions={regions} value={regionId} onChange={setRegionId} />
        </div>
        <div>
          <label className="mb-2 block text-xs font-bold uppercase tracking-wider text-zinc-500">
            Статус
          </label>
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value || "all"}
              onClick={() => setStatus(f.value)}
              className={`mr-2 mt-1 rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                status === f.value
                  ? "border-amber-400/60 bg-amber-400/10 text-amber-300"
                  : "border-zinc-700 text-zinc-400 hover:border-zinc-500"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <div className="mb-4 flex items-baseline justify-between">
          <h2 className="text-lg font-bold text-zinc-200">
          {mode === "national" ? "Все крупные и всероссийские старты" : selectedRegion
            ? selectedRegion.name
            : "Все регионы"}
          </h2>
          <span className="text-sm text-zinc-500">Найдено: {total}</span>
        </div>

        {loading && <p className="py-10 text-center text-sm text-zinc-500">Загрузка…</p>}
        {error && (
          <div className="rounded-2xl border border-red-400/30 bg-red-400/10 p-5 text-sm text-red-300">
            Не удалось загрузить данные: API недоступен. Запустите бэкенд (см. README проекта).
          </div>
        )}
        {!loading && !error && (
          <div className="grid gap-4">
            {events.map((ev) => (
              <EventCard key={ev.id} ev={ev} />
            ))}
            {events.length === 0 && (
              <div className="rounded-2xl border border-dashed border-zinc-700 p-10 text-center text-sm text-zinc-500">
                Пока ничего не найдено. Попробуйте другой регион или статус.
              </div>
            )}
          </div>
        )}
      </section>

      <footer className="mt-16 border-t border-zinc-800 pt-6 text-xs text-zinc-600">
        Информация собирается автоматически из открытых источников (ФГДР, Telegram, VK)
        со ссылкой на первоисточник. Данные носят справочный характер.
      </footer>
    </main>
  );
}
