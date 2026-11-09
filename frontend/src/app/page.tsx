"use client";

import { useEffect, useMemo, useState } from "react";
import EventCard, { formatDate } from "@/components/EventCard";
import RegionPicker from "@/components/RegionPicker";
import { api } from "@/lib/api";
import type { EventItem, RegionItem } from "@/lib/types";

type Mode = "all" | "regional" | "national";
type View = "list" | "calendar";

const MODES: { value: Mode; label: string }[] = [
  { value: "all", label: "ВСЕ" },
  { value: "regional", label: "РЕГИОНАЛЬНЫЕ" },
  { value: "national", label: "ВСЕРОССИЙСКИЕ" },
];

const STATUSES = [
  { value: "", label: "— все статусы —" },
  { value: "registration_open", label: "Регистрация открыта" },
  { value: "anons", label: "Анонс" },
  { value: "ongoing", label: "Идёт сейчас" },
];

const MONTH_NAMES = [
  "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ",
  "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ",
];
const WEEKDAYS = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"];

function iso(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export default function Home() {
  const [mode, setMode] = useState<Mode>("all");
  const [view, setView] = useState<View>("list");
  const [regions, setRegions] = useState<RegionItem[]>([]);
  const [regionId, setRegionId] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const [upcomingItems, setUpcomingItems] = useState<EventItem[]>([]);
  const [archiveItems, setArchiveItems] = useState<EventItem[]>([]);
  const [archiveTotal, setArchiveTotal] = useState(0);
  const [calEvents, setCalEvents] = useState<EventItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pastPage, setPastPage] = useState(1);
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  useEffect(() => {
    api.regions(true).then(setRegions).catch(() => {});
  }, []);

  const today = iso(new Date());
  const yesterday = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return iso(d);
  }, []);

  const filterKey = `${mode}|${regionId ?? ""}|${status}`;

  useEffect(() => {
    setLoading(true);
    setError(null);
    setPastPage(1);
    api
      .events({
        mode,
        region_id: regionId ?? undefined,
        status: status || undefined,
        only_upcoming: true,
        limit: 100,
      })
      .then((p) => setUpcomingItems(p.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filterKey]);

  useEffect(() => {
    api
      .events({
        mode,
        region_id: regionId ?? undefined,
        status: status || undefined,
        only_upcoming: false,
        limit: 100,
      })
      .then((p) => setCalEvents(p.items))
      .catch(() => {});
  }, [filterKey]);

  useEffect(() => {
    api
      .events({
        mode,
        region_id: regionId ?? undefined,
        status: status || undefined,
        only_upcoming: false,
        date_to: yesterday,
        limit: 9,
        page: pastPage,
      })
      .then((p) => {
        setArchiveItems(p.items);
        setArchiveTotal(p.total);
      })
      .catch(() => {});
  }, [filterKey, pastPage, yesterday]);

  const { ongoing, upcoming } = useMemo(() => {
    const sorted = [...upcomingItems].sort((a, b) => (a.event_date < b.event_date ? -1 : 1));
    const ongoing = sorted.filter(
      (e) => e.status === "ongoing" || (e.event_date === today && e.status !== "finished"),
    );
    const ongoingIds = new Set(ongoing.map((e) => e.id));
    const upcoming = sorted.filter(
      (e) => e.event_date >= today && e.status !== "finished" && !ongoingIds.has(e.id),
    );
    return { ongoing, upcoming };
  }, [upcomingItems, today]);

  const PAGE_SIZE = 9;
  const pastPages = Math.max(1, Math.ceil(archiveTotal / PAGE_SIZE));

  const calendarCells = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const daysInMonth = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate();
    const offset = (first.getDay() + 6) % 7;
    const byDate = new Map<string, EventItem[]>();
    for (const e of calEvents) {
      const arr = byDate.get(e.event_date) ?? [];
      arr.push(e);
      byDate.set(e.event_date, arr);
    }
    const cells: { date: string | null; day: number | null; events: EventItem[] }[] = [];
    for (let i = 0; i < offset; i++) cells.push({ date: null, day: null, events: [] });
    for (let d = 1; d <= daysInMonth; d++) {
      const key = iso(new Date(month.getFullYear(), month.getMonth(), d));
      cells.push({ date: key, day: d, events: byDate.get(key) ?? [] });
    }
    while (cells.length % 7 !== 0) cells.push({ date: null, day: null, events: [] });
    return cells;
  }, [calEvents, month]);

  const regionLabel = regions.find((r) => r.id === regionId)?.name;

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-[260px] flex-col border-r border-[#232326] bg-[#0d0d0f] lg:flex">
        <div className="flex items-center gap-2 border-b border-[#232326] px-5 py-4">
          <span className="font-display text-[22px] font-bold uppercase tracking-tight text-white">
            ДРОН
          </span>
          <span className="rounded-[3px] bg-[#ff4d1c] px-1.5 py-0.5 text-[9px] font-extrabold uppercase tracking-widest text-black">
            Агрегатор
          </span>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 text-[12px] font-bold uppercase tracking-[0.12em]">
          <p className="px-2 pb-2 text-[10px] tracking-[0.2em] text-[#5a5a60]">Основное</p>
          <button
            onClick={() => { setView("list"); window.scrollTo({ top: 0 }); }}
            className={`mb-1 flex w-full items-center gap-3 border-l-2 px-3 py-2 text-left transition ${
              view === "list"
                ? "border-[#ff4d1c] bg-[#1a1210] text-[#ff7a4d]"
                : "border-transparent text-[#8b8b90] hover:text-white"
            }`}
          >
            <span className="text-[14px]">▤</span> Мероприятия
          </button>
          <button
            onClick={() => { setView("calendar"); window.scrollTo({ top: 0 }); }}
            className={`mb-1 flex w-full items-center gap-3 border-l-2 px-3 py-2 text-left transition ${
              view === "calendar"
                ? "border-[#ff4d1c] bg-[#1a1210] text-[#ff7a4d]"
                : "border-transparent text-[#8b8b90] hover:text-white"
            }`}
          >
            <span className="text-[14px]">▦</span> Календарь
          </button>

          <p className="px-2 pb-2 pt-6 text-[10px] tracking-[0.2em] text-[#5a5a60]">Скачать</p>
          <a
            href="https://github.com/wwaiia/drone-racing"
            target="_blank"
            rel="noopener noreferrer"
            className="mb-1 flex items-center gap-3 border-l-2 border-transparent px-3 py-2 text-[#8b8b90] transition hover:text-white"
          >
            <span className="text-[14px]">↓</span> Локальная версия
          </a>
        </nav>

        <div className="border-t border-[#232326] px-5 py-3 text-[10px] uppercase tracking-widest text-[#5a5a60]">
          v1.0 · 2026
        </div>
      </aside>

      <div className="min-w-0 flex-1 lg:pl-[260px]">
        <header className="flex h-14 items-center justify-between border-b border-[#232326] px-5 sm:px-8">
          <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-[#8b8b90]">
            <span className="text-white/85">ДРОН РЕЙСИНГ</span>
            <span className="text-[#3d3d44]">/</span>
            <span className="text-[#ff7a4d]">МЕРОПРИЯТИЯ</span>
          </div>
          <div className="flex items-center gap-3 text-[11px] font-bold uppercase tracking-[0.18em] text-[#8b8b90]">
            <span className="text-white/85">RU</span>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1240px] px-5 pb-20 pt-8 sm:px-8">
          <h1 className="font-display text-[42px] font-bold uppercase leading-none tracking-tight text-white sm:text-[56px]">
            Мероприятия
          </h1>
          <p className="mt-3 text-[13px] text-[#8b8b90]">
            <b className="text-white/90">{ongoing.length + upcoming.length}</b> предстоящих ·{" "}
            <b className="text-white/90">{archiveTotal}</b> в архиве
          </p>

          <div className="mt-7 flex flex-wrap items-center gap-x-7 gap-y-3 border-b border-[#232326]">
            {(["list", "calendar"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`-mb-px flex items-center gap-2 border-b-2 pb-3 text-[12px] font-bold uppercase tracking-[0.14em] transition ${
                  view === v
                    ? "border-[#ff4d1c] text-[#ff7a4d]"
                    : "border-transparent text-[#8b8b90] hover:text-white"
                }`}
              >
                <span>{v === "list" ? "☰" : "▦"}</span>
                {v === "list" ? "Список" : "Календарь"}
              </button>
            ))}
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-3">
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-transparent">
              {MODES.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMode(m.value)}
                  className={`border-b-2 pb-1.5 text-[12px] font-bold uppercase tracking-[0.14em] transition ${
                    mode === m.value
                      ? "border-[#ff4d1c] text-[#ff7a4d]"
                      : "border-transparent text-[#8b8b90] hover:text-white"
                  }`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <RegionPicker regions={regions} value={regionId} onChange={setRegionId} />
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
                className="h-9 min-w-[170px] rounded-[4px] border border-[#2e2e33] bg-[#0f0f11] px-3 text-[12px] font-semibold uppercase tracking-wide text-[#d6d6da] outline-none transition hover:border-[#3d3d44] focus:border-[#ff4d1c]/70"
              >
                {STATUSES.map((s) => (
                  <option key={s.value || "all"} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {error && (
            <div className="mt-8 rounded-[4px] border border-[#ff4d1c]/35 bg-[#ff4d1c]/10 p-4 text-[13px] text-[#ff9a7a]">
              Не удалось загрузить данные: API недоступен.
            </div>
          )}

          {loading && <p className="py-12 text-center text-[13px] text-[#8b8b90]">Загрузка…</p>}

          {!loading && !error && view === "list" && (
            <>
              <Section title="Идут сейчас" count={ongoing.length}>
                {ongoing.length ? (
                  <Grid items={ongoing} />
                ) : (
                  <Empty text="Сейчас активных мероприятий нет." />
                )}
              </Section>

              <Section title="Предстоящие" count={upcoming.length}>
                {upcoming.length ? (
                  <Grid items={upcoming} />
                ) : (
                  <Empty text="Пока нет предстоящих мероприятий — попробуйте другой регион или тип." />
                )}
              </Section>

              <Section title="Прошедшие" count={archiveTotal}>
                {archiveItems.length ? (
                  <>
                    <Grid items={archiveItems} />
                    {pastPages > 1 && (
                      <div className="mt-5 flex items-center justify-between text-[11px] font-bold uppercase tracking-[0.14em] text-[#8b8b90]">
                        <button
                          onClick={() => setPastPage((p) => Math.max(1, p - 1))}
                          disabled={pastPage <= 1}
                          className="transition hover:text-white disabled:opacity-30"
                        >
                          ← Назад
                        </button>
                        <span>
                          Стр. {pastPage} из {pastPages}
                        </span>
                        <button
                          onClick={() => setPastPage((p) => Math.min(pastPages, p + 1))}
                          disabled={pastPage >= pastPages}
                          className="transition hover:text-white disabled:opacity-30"
                        >
                          Вперёд →
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <Empty text="Архив пуст." />
                )}
              </Section>
            </>
          )}

          {!loading && !error && view === "calendar" && (
            <div className="mt-8 rounded-[4px] border border-[#232326] bg-[#0f0f11]">
              <div className="flex items-center justify-between border-b border-[#232326] px-4 py-3">
                <button
                  onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
                  className="text-[12px] font-bold uppercase tracking-widest text-[#8b8b90] transition hover:text-white"
                >
                  ← 
                </button>
                <span className="font-display text-[18px] font-bold uppercase tracking-wide text-white">
                  {MONTH_NAMES[month.getMonth()]} {month.getFullYear()}
                </span>
                <button
                  onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
                  className="text-[12px] font-bold uppercase tracking-widest text-[#8b8b90] transition hover:text-white"
                >
                   →
                </button>
              </div>
              <div className="grid grid-cols-7 border-b border-[#232326] text-center">
                {WEEKDAYS.map((w) => (
                  <div key={w} className="py-2 text-[10px] font-bold uppercase tracking-[0.18em] text-[#5a5a60]">
                    {w}
                  </div>
                ))}
              </div>
              <div className="grid grid-cols-7">
                {calendarCells.map((c, i) => (
                  <div
                    key={i}
                    className={`min-h-[92px] border-b border-r border-[#1b1b1e] p-1.5 ${
                      c.date === today ? "bg-[#ff4d1c]/[0.06]" : ""
                    }`}
                  >
                    {c.day && (
                      <div
                        className={`mb-1 inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                          c.date === today ? "bg-[#ff4d1c] text-black" : "text-[#8b8b90]"
                        }`}
                      >
                        {c.day}
                      </div>
                    )}
                    {c.events.slice(0, 2).map((e) => (
                      <a
                        key={e.id}
                        href={e.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={e.title}
                        className="mb-0.5 block truncate rounded-[2px] border-l-2 border-[#ff4d1c] bg-[#ff4d1c]/10 px-1 py-0.5 text-[10px] font-semibold text-[#ffb9a3] hover:bg-[#ff4d1c]/20"
                      >
                        {e.title}
                      </a>
                    ))}
                    {c.events.length > 2 && (
                      <span className="text-[9px] text-[#5a5a60]">+{c.events.length - 2}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <footer className="mt-14 flex flex-wrap items-center justify-between gap-2 border-t border-[#232326] pt-5 text-[11px] uppercase tracking-[0.14em] text-[#5a5a60]">
            <span>© 2026 ДРОН РЕЙСИНГ{regionLabel ? ` · ${regionLabel}` : ""}</span>
            <span>Данные собираются автоматически · {formatDate(today)}</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

function Section({
  title,
  count,
  children,
}: {
  title: string;
  count: number;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-9">
      <div className="mb-4 flex items-center justify-between border-t border-[#232326] pt-3">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.22em] text-[#8b8b90]">{title}</h2>
        <span className="text-[11px] font-bold text-[#5a5a60]">{count}</span>
      </div>
      {children}
    </section>
  );
}

function Grid({ items }: { items: EventItem[] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((ev) => (
        <EventCard key={ev.id} ev={ev} />
      ))}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-[4px] border border-dashed border-[#2e2e33] p-8 text-center text-[13px] text-[#8b8b90]">
      {text}
    </div>
  );
}
