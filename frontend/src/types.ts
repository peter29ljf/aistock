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
