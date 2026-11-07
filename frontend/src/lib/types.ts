export type EventStatus =
  | "anons"
  | "registration_open"
  | "registration_closed"
  | "ongoing"
  | "finished"
  | "postponed"
  | "cancelled";

export type EventItem = {
  id: number;
  title: string;
  organizer: string | null;
  event_date: string;
  event_time: string | null;
  date_time_precision: string;
  event_type: "regional" | "national";
  status: EventStatus;
  region_id: number | null;
  region_name: string | null;
  city: string | null;
  venue: string | null;
  prize_fund_amount: number | null;
  prize_fund_visibility: "hidden" | "none" | "amount" | "tbd";
  prize_fund_note: string | null;
  registration_url: string | null;
  source_url: string;
  confidence: number;
  moderation: string;
};

export type EventPage = {
  items: EventItem[];
  total: number;
  page: number;
  limit: number;
};

export type RegionItem = {
  id: number;
  name: string;
  federal_district: string;
  center_city: string | null;
  slug: string;
  upcoming_events: number;
};

export type Stats = {
  upcoming_total: number;
  upcoming_regional: number;
  upcoming_national: number;
  regions_with_events: number;
  with_prize: number;
};
