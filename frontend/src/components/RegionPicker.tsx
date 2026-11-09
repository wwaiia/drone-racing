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
      className="h-9 w-full min-w-[180px] rounded-[4px] border border-[#2e2e33] bg-[#0f0f11] px-3 text-[12px] font-semibold uppercase tracking-wide text-[#d6d6da] outline-none transition hover:border-[#3d3d44] focus:border-[#ff4d1c]/70"
    >
      <option value="">— все регионы —</option>
      {Object.entries(groups).map(([district, items]) => (
        <optgroup key={district} label={district}>
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
