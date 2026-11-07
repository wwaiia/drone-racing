import type { EventItem } from "@/lib/types";
import { formatPrize } from "@/lib/api";

const MONTHS: Record<number, string> = {
  1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
  7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
};

const STATUS: Record<string, { label: string; cls: string }> = {
  anons: { label: "Анонс", cls: "bg-amber-400/15 text-amber-300 border-amber-400/30" },
  registration_open: { label: "Регистрация открыта", cls: "bg-emerald-400/15 text-emerald-300 border-emerald-400/30" },
  registration_closed: { label: "Регистрация закрыта", cls: "bg-orange-400/15 text-orange-300 border-orange-400/30" },
  ongoing: { label: "Идёт сейчас", cls: "bg-yellow-300/20 text-yellow-200 border-yellow-300/40" },
  finished: { label: "Завершено", cls: "bg-zinc-400/15 text-zinc-400 border-zinc-400/25" },
  postponed: { label: "Перенесено", cls: "bg-red-400/15 text-red-300 border-red-400/30" },
  cancelled: { label: "Отменено", cls: "bg-red-400/15 text-red-300 border-red-400/30" },
};

function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m]} ${y}`;
}

export default function EventCard({ ev }: { ev: EventItem }) {
  const st = STATUS[ev.status] ?? STATUS.anons;
  const prize = ev.prize_fund_visibility === "amount" && ev.prize_fund_amount
    ? formatPrize(ev.prize_fund_amount)
    : null;

  return (
    <article
      className="group relative overflow-hidden rounded-2xl border border-zinc-800 bg-[#26262A]
                 transition hover:border-amber-400/40 hover:shadow-[0_0_30px_rgba(255,193,19,0.07)]"
    >
      <span className="absolute inset-y-0 left-0 w-1 bg-amber-400" aria-hidden />
      <div className="p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              {ev.event_type === "national" && (
                <span className="rounded-md bg-amber-400 px-2 py-0.5 text-[11px] font-bold uppercase tracking-wide text-black">
                  Всероссийский
                </span>
              )}
              <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${st.cls}`}>
                {st.label}
              </span>
            </div>
            <h3 className="text-lg font-bold leading-snug text-zinc-100 group-hover:text-amber-300 sm:text-xl">
              {ev.title}
            </h3>
            {ev.organizer && (
              <p className="mt-1 text-sm text-zinc-500">{ev.organizer}</p>
            )}
          </div>
          {prize && (
            <div className="shrink-0 rounded-xl bg-amber-400 px-3 py-2 text-center shadow-[0_0_18px_rgba(255,193,19,0.25)]">
              <div className="text-[10px] font-bold uppercase tracking-wider text-black/70">Призовой фонд</div>
              <div className="text-base font-extrabold text-black sm:text-lg">{prize}</div>
            </div>
          )}
        </div>

        <div className="mt-4 grid gap-2 text-sm text-zinc-400">
          <div className="flex items-center gap-2">
            <span aria-hidden>📅</span>
            <span className="text-zinc-300">
              {formatDate(ev.event_date)}
              {ev.event_time ? `, ${ev.event_time}` : ""}
              {ev.date_time_precision === "approx" && <em className="text-zinc-500"> (дата уточняется)</em>}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span aria-hidden>📍</span>
            <span className="text-zinc-300">
              {[ev.region_name, ev.city, ev.venue].filter(Boolean).join(", ") || "Место уточняется"}
            </span>
          </div>
        </div>

        {ev.prize_fund_visibility === "none" && (
          <p className="mt-3 text-sm text-zinc-500">Без призового фонда</p>
        )}
        {ev.prize_fund_visibility === "tbd" && (
          <p className="mt-3 text-sm text-amber-300/80">Призовой фонд: будет объявлен</p>
        )}
        {ev.prize_fund_visibility === "hidden" && (
          <p className="mt-3 text-sm text-zinc-500">Призовой фонд: уточняется</p>
        )}
        {ev.prize_fund_note && ev.prize_fund_visibility === "amount" && (
          <p className="mt-2 line-clamp-1 text-xs text-zinc-500">{ev.prize_fund_note}</p>
        )}

        <div className="mt-5 flex flex-wrap gap-3">
          {ev.registration_url && (
            <a
              href={ev.registration_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-xl bg-amber-400 px-4 py-2 text-sm font-bold text-black transition hover:bg-amber-300"
            >
              Перейти к регистрации
            </a>
          )}
          <a
            href={ev.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl border border-zinc-700 px-4 py-2 text-sm font-semibold text-zinc-300 transition hover:border-amber-400/50 hover:text-amber-300"
          >
            Подробнее об ивенте ↗
          </a>
        </div>
      </div>
    </article>
  );
}
