import type { EventItem } from "@/lib/types";
import { formatPrize } from "@/lib/api";

const MONTHS = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

const STATUS: Record<string, { label: string; cls: string }> = {
  anons: { label: "АНОНС", cls: "border border-white/25 text-white/85 bg-black/40" },
  registration_open: { label: "РЕГИСТРАЦИЯ", cls: "bg-[#ff4d1c] text-black" },
  registration_closed: { label: "ЗАКРЫТА", cls: "border border-white/25 text-white/70 bg-black/40" },
  ongoing: { label: "ИДЁТ", cls: "bg-[#ff4d1c] text-black" },
  finished: { label: "ЗАВЕРШЕНО", cls: "bg-[#2a2a2e] text-white/55" },
  postponed: { label: "ПЕРЕНЕСЕНО", cls: "bg-[#3a2a10] text-[#ffb02e]" },
  cancelled: { label: "ОТМЕНЕНО", cls: "bg-[#3a1414] text-[#ff6b6b]" },
};

export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  if (!y || !m || !d) return iso;
  return `${d} ${MONTHS[m - 1]} ${y}`;
}

export default function EventCard({ ev }: { ev: EventItem }) {
  const st = STATUS[ev.status] ?? STATUS.anons;
  const prize =
    ev.prize_fund_visibility === "amount" && ev.prize_fund_amount
      ? formatPrize(ev.prize_fund_amount)
      : null;
  const place = [ev.city, ev.venue].filter(Boolean).join(", ") || ev.region_name || "Место уточняется";

  return (
    <article className="group flex flex-col overflow-hidden rounded-md border border-[#232326] bg-[#121214] transition hover:border-[#3a3a40]">
      <div className="relative h-24 overflow-hidden bg-[radial-gradient(120%_140%_at_85%_-20%,rgba(255,77,28,0.28),transparent_60%),linear-gradient(160deg,#1b1b1f,#101012)]">
        <div className="absolute inset-0 opacity-[0.14] [background-image:repeating-linear-gradient(115deg,transparent_0_22px,#fff_22px_23px)]" />
        <span className={`absolute left-3 top-3 rounded-[3px] px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${st.cls}`}>
          {st.label}
        </span>
        {ev.event_type === "national" && (
          <span className="absolute right-3 top-3 rounded-[3px] border border-white/20 bg-black/40 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white/70">
            ВСЕРОССИЙСКОЕ
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-4">
        <p className="text-[12px] font-bold uppercase tracking-wide text-[#ff4d1c]">
          {formatDate(ev.event_date)}
          {ev.event_time ? ` · ${ev.event_time}` : ""}
          {ev.date_time_precision === "approx" && <span className="text-white/40"> · дата уточняется</span>}
        </p>
        <h3 className="mt-1.5 line-clamp-2 text-[15px] font-extrabold uppercase leading-snug tracking-wide text-white">
          {ev.title}
        </h3>
        <p className="mt-1 line-clamp-1 text-[13px] text-[#8b8b90]">{place}</p>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {ev.region_name && (
            <span className="rounded-[3px] border border-[#2e2e33] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#b9b9be]">
              {ev.region_name}
            </span>
          )}
          {ev.organizer && (
            <span className="rounded-[3px] border border-[#2e2e33] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#b9b9be]">
              {ev.organizer}
            </span>
          )}
          {prize && (
            <span className="rounded-[3px] border border-[#ff4d1c]/45 bg-[#ff4d1c]/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#ff7a4d]">
              {prize}
            </span>
          )}
          {ev.prize_fund_visibility === "tbd" && (
            <span className="rounded-[3px] border border-[#2e2e33] px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#8b8b90]">
              ФОНД УТОЧНЯЕТСЯ
            </span>
          )}
        </div>

        <div className="mt-auto flex flex-wrap gap-2 pt-4">
          {ev.registration_url && (
            <a
              href={ev.registration_url}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-[4px] bg-[#ff4d1c] px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-black transition hover:bg-[#ff6a3f]"
            >
              Регистрация
            </a>
          )}
          <a
            href={ev.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-[4px] border border-[#2e2e33] px-3 py-1.5 text-[12px] font-bold uppercase tracking-wide text-[#b9b9be] transition hover:border-[#ff4d1c]/60 hover:text-[#ff7a4d]"
          >
            Источник
          </a>
        </div>
      </div>
    </article>
  );
}
