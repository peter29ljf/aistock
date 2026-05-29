export interface Strategy {
  sid: string;
  name?: string;
  description?: string;
  created_at?: string;
  kind?: string;
}

export interface Position {
  symbol: string;
  buy_price: number;
  quantity: number;
  note?: string;
  current_price?: number;
  pnl_pct?: number;
  pnl_value?: number;
}

export interface ChatEvent {
  ts?: string;
  type?: string;
  role?: string;
  kind?: string;
  content?: string;
  message?: unknown;
  [k: string]: unknown;
}

export interface Alert {
  id: number;
  sid: string;
  symbol: string;
  target: number;
  direction: "above" | "below";
  status: "active" | "fired" | "cancelled";
  note?: string;
  created_at?: string;
  fired_at?: string;
  fired_price?: number;
}

export interface Schedule {
  task_id: string;
  sid?: string;
  note?: string;
  kind?: string;
  expr?: string;
  run_at?: string;
  next_run_time?: string;
}
