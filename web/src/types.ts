export type Point = [number, number];
export type Config = {
  kind: "generated" | "hybrid" | "western_chess" | "standard_shogi";
  seed: number;
  board_size: number;
  preset: string;
  mode: "pve" | "pvp";
  human: 0 | 1;
  think_seconds: number;
};
export type Action = {
  kind: string;
  from?: Point;
  to?: Point;
  base_type_id?: string;
  actor_type_id?: string;
  promotion_target_id?: string | null;
  pattern_id?: string;
  geometry_id?: string;
};
export type Offer = { id: string; action: Action; label: string };
export type Piece = {
  owner: number;
  type: string;
  base_type: string;
  promoted: boolean;
  name: string;
};
export type Square = {
  file: number;
  rank: number;
  piece: Piece | null;
  last_from: boolean;
  last_to: boolean;
  check: boolean;
};
export type State = {
  id: string;
  revision: number;
  config: Config;
  board_size: number;
  side_to_move: number;
  squares: Square[];
  hands: { type_id: string; count: number }[][];
  types: Record<string, { id: string; name: string; anchor: boolean }>;
  fingerprint: string;
  seed: number | null;
  ply: number;
  displayed_ply: number | null;
  result: { status: string; winner: number | null };
  history: { ply: number; player: number; label: string; action: Action }[];
  actions: Offer[];
  can_undo: boolean;
  active: boolean;
  ai: {
    thinking: boolean;
    queued: boolean;
    paused: boolean;
    error: string | null;
  };
  storage_error: string | null;
  rules: {
    piece_types: [string, string, string[]][];
    promotion_relations: string[];
    drop_summary: string;
    terminal_summary: string;
  };
};
export type Saved = {
  id: string;
  config: Config;
  updated: number;
  ply: number;
};
export const defaults: Config = {
  kind: "generated",
  seed: 42,
  board_size: 8,
  preset: "classic_like",
  mode: "pve",
  human: 0,
  think_seconds: 1,
};
export const titles: Record<string, string> = {
  generated: "生成棋",
  hybrid: "混合生成棋",
  western_chess: "国际象棋",
  standard_shogi: "将棋",
};
