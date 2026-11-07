"use client";

import type { RegionItem } from "@/lib/types";

type Props = {
  regions: RegionItem[];
  value: number | null;
  onChange: (id: number | null) => void;
};

export default function RegionPicker({ regions, value, onChange }: Props) {
  const groups = regions.reduce<Record<string, RegionItem[]>>((acc, r) => {
    (acc[r.federal_district] ??= []).push(r);
    return acc;
  }, {});

  return (
    <select
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      className="w-full rounded-xl border border-zinc-700 bg-[#1b1b1f] px-4 py-2.5 text-sm text-zinc-200
                 outline-none transition focus:border-amber-400/60"
    >
      <option value="">Все регионы</option>
      {Object.entries(groups).map(([district, items]) => (
        <optgroup
          key={district}
          label={`${district} — всего ${items.reduce((s, r) => s + r.upcoming_events, 0)}`}
        >
          {items.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name} ({r.upcoming_events})
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  );
}
