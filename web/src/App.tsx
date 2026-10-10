import type { CSSProperties } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronRight,
  Download,
  Flag,
  FlipVertical2,
  History,
  Leaf,
  Menu,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Settings2,
  Shuffle,
  Sparkles,
  Upload,
  X,
  Check,
  Circle,
  CircleHelp,
} from "lucide-react";
import type { Action, Config, Offer, Point, Saved, State } from "./types";
import { defaults, titles } from "./types";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new Error("暂时无法连接服务，请稍后重试。");
  }
  const body = await res.json();
  if (!res.ok)
    throw Object.assign(
      new Error(body.error ?? "暂时无法连接服务，请稍后重试。"),
      { state: body.state },
    );
  return body;
}
const same = (a?: Point | null, b?: Point | null) =>
  !!a && !!b && a[0] === b[0] && a[1] === b[1];
const coordinate = (p: Point) => `${String.fromCharCode(97 + p[0])}${p[1] + 1}`;
const moveLabel = (a: Action) =>
  a.kind === "pass"
    ? "停着"
    : `${a.from ? coordinate(a.from) : "打入"} → ${a.to ? coordinate(a.to) : ""}${a.promotion_target_id ? " · 升变" : ""}`;
const translateName = (name: string) =>
  ({
    King: "王",
    Queen: "后",
    Rook: "车",
    Bishop: "象",
    Knight: "马",
    Pawn: "兵",
    Gold: "金将",
    Silver: "银将",
    Lance: "香车",
    Dragon: "龙王",
    Horse: "龙马",
    Tokin: "成步",
    Companion: "伴子",
    "Piece A": "棋子 A",
    "Piece B": "棋子 B",
    "Piece C": "棋子 C",
  })[name] ?? name;
const sideName = (owner: number) => (owner === 0 ? "先手" : "后手");
const ruleText = (line: string) =>
  line
    .replaceAll("forward", "前")
    .replaceAll("backward", "后")
    .replaceAll("right", "右")
    .replaceAll("left", "左")
    .replaceAll("sideways", "横向")
    .replaceAll(" ray", "滑行")
    .replaceAll(" leap", "跳跃")
    .replaceAll("unlimited", "不限距离")
    .replaceAll("blocked by pieces", "遇棋子阻挡")
    .replaceAll("exactly ", "固定 ")
    .replaceAll("max ", "最多 ")
    .replaceAll("squares", "格")
    .replaceAll("square", "格");
const terminalText = (line: string) =>
  line
    .replace("stalemate=", "无合法行动：")
    .replace("repetition_limit=", "重复局面阈值：")
    .replace("max_ply=", "行动上限：")
    .replaceAll("draw", "和棋")
    .replaceAll("loss", "判负");
const endNames: Record<string, string> = {
  checkmate: "将死",
  stalemate: "无合法行动",
  repetition: "重复局面",
  perpetual_check: "连续将军",
  max_ply: "达到回合上限",
  no_contest: "无胜负",
  action_class_draw: "规则和棋",
  no_progress_draw: "无进展和棋",
  rule_loss: "规则判负",
  resignation: "认输",
  declaration: "宣言终局",
};

export default function App() {
  const [game, setGame] = useState<State | null>(null);
  const current = useRef<State | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(true);
  const [config, setConfig] = useState<Config>(defaults);
  const [setup, setSetup] = useState(false);
  const [menu, setMenu] = useState(false);
  const [selected, setSelected] = useState<Point | null>(null);
  const [hand, setHand] = useState<string | null>(null);
  const [choices, setChoices] = useState<Offer[]>([]);
  const [orientation, setOrientation] = useState(0);
  const [tab, setTab] = useState<"history" | "rules">("history");
  const [reduceMotion, setReduceMotion] = useState(
    () => localStorage.getItem("gc-motion") === "reduced",
  );
  const [inspected, setInspected] = useState<string | null>(null);
  const file = useRef<HTMLInputElement>(null);
  const importKind = useRef("bundle");
  const listSaved = useCallback(
    () =>
      request<{ games: Saved[]; warning: string | null }>("/api/games")
        .then((data) => {
          setSaved(data.games);
          if (data.warning) setError(data.warning);
        })
        .catch((err) => setError(err.message)),
    [],
  );
  const accept = useCallback((state: State) => {
    if (
      current.current &&
      current.current.id === state.id &&
      current.current.revision > state.revision
    )
      return;
    current.current = state;
    setGame(state);
    localStorage.setItem("gc-last-game", state.id);
  }, []);
  useEffect(() => {
    void listSaved();
  }, [listSaved]);
  useEffect(() => {
    setSelected(null);
    setHand(null);
    setChoices([]);
  }, [game?.id, game?.ply, game?.displayed_ply]);
  useEffect(() => {
    if (!setup && !choices.length) return;
    const previous = document.activeElement as HTMLElement | null;
    const timer = window.setTimeout(
      () => document.querySelector<HTMLElement>(".modal button")?.focus(),
      0,
    );
    const keys = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSetup(false);
        setChoices([]);
      }
      if (e.key === "Tab") {
        const items = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".modal button:not(:disabled), .modal input, .modal select",
          ),
        );
        const first = items[0],
          last = items.at(-1);
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", keys);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("keydown", keys);
      previous?.focus();
    };
  }, [setup, choices.length]);
  useEffect(() => {
    if (!game) return;
    let disposed = false;
    let ws: WebSocket;
    let reconnect: number;
    let delay = 400;
    let lastMessage = Date.now();
    function connect() {
      if (
        disposed ||
        !navigator.onLine ||
        ws?.readyState === WebSocket.OPEN ||
        ws?.readyState === WebSocket.CONNECTING
      )
        return;
      const socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/api/games/${game!.id}/events`,
      );
      ws = socket;
      socket.onopen = () => {
        if (!disposed) {
          setConnected(true);
          delay = 400;
          lastMessage = Date.now();
        }
      };
      socket.onmessage = (event) => {
        if (disposed || ws !== socket) return;
        lastMessage = Date.now();
        const data = JSON.parse(event.data);
        if (data.id) accept(data);
      };
      socket.onclose = () => {
        if (disposed || ws !== socket) return;
        setConnected(false);
        reconnect = window.setTimeout(connect, delay);
        delay = Math.min(delay * 2, 5000);
      };
    }
    const offline = () => {
      setConnected(false);
      ws?.close();
    };
    const online = () => {
      clearTimeout(reconnect);
      connect();
    };
    const heartbeat = window.setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        if (Date.now() - lastMessage > 10000) ws.close();
        else ws.send("ping");
      }
    }, 3000);
    window.addEventListener("offline", offline);
    window.addEventListener("online", online);
    connect();
    return () => {
      disposed = true;
      clearTimeout(reconnect);
      clearInterval(heartbeat);
      window.removeEventListener("offline", offline);
      window.removeEventListener("online", online);
      ws?.close();
    };
  }, [game?.id, accept]);
  async function operate(kind: string, extra: Record<string, unknown> = {}) {
    const state = current.current;
    if (!state || busy) return;
    setBusy(true);
    setError("");
    try {
      const next = await request<State>(`/api/games/${state.id}/operations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind,
          expected_revision: state.revision,
          request_id: crypto.randomUUID(),
          ...extra,
        }),
      });
      if (current.current?.id === state.id) accept(next);
      return next;
    } catch (err) {
      const e = err as Error & { state?: State };
      if (e.state && current.current?.id === state.id) accept(e.state);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function start() {
    setBusy(true);
    setError("");
    try {
      const next = await request<State>("/api/games", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config, previous_id: current.current?.id }),
      });
      current.current = null;
      accept(next);
      setOrientation(config.mode === "pve" ? config.human : 0);
      setSetup(false);
      setMenu(false);
      setInspected(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function resume(id: string) {
    setBusy(true);
    setError("");
    try {
      const previous = current.current;
      const next = await request<State>(`/api/games/${id}`);
      const resumed = await request<State>(`/api/games/${id}/operations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          kind: "resume",
          expected_revision: next.revision,
          request_id: crypto.randomUUID(),
        }),
      });
      if (previous && previous.id !== id)
        await request(`/api/games/${previous.id}/operations`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            kind: "suspend",
            expected_revision: previous.revision,
            request_id: crypto.randomUUID(),
          }),
        }).catch(() => {});
      current.current = null;
      accept(resumed);
      setOrientation(resumed.config.mode === "pve" ? resumed.config.human : 0);
      setSetup(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function home() {
    await operate("suspend");
    current.current = null;
    setGame(null);
    setMenu(false);
    void listSaved();
  }
  function choose(offer: Offer) {
    setChoices([]);
    void operate("action", { action_id: offer.id });
  }
  const relevant =
    game?.actions.filter((offer) =>
      hand
        ? offer.action.base_type_id === hand && !offer.action.from
        : same(offer.action.from, selected),
    ) ?? [];
  function squareClicked(point: Point) {
    if (!game || busy) return;
    const square = game.squares.find(
      (sq) => sq.file === point[0] && sq.rank === point[1],
    );
    if (square?.piece) setInspected(square.piece.type);
    const offers = relevant.filter((offer) => same(offer.action.to, point));
    if (offers.length === 1) {
      choose(offers[0]);
      return;
    }
    if (offers.length > 1) {
      setChoices(offers);
      return;
    }
    if (same(selected, point)) {
      setSelected(null);
      setHand(null);
      return;
    }
    setHand(null);
    setSelected(
      square?.piece &&
        game.actions.some((offer) => same(offer.action.from, point))
        ? point
        : null,
    );
  }
  function importFile(kind: string) {
    importKind.current = kind;
    setMenu(false);
    file.current?.click();
  }
  async function readFile(files: FileList | null) {
    const picked = files?.[0];
    if (!picked) return;
    if (picked.size > 4_000_000) {
      setError("文件过大，请选择小于 4 MB 的文件。");
      return;
    }
    try {
      await operate("import", {
        format: importKind.current,
        content: await picked.text(),
      });
      setInspected(null);
    } catch {
      setError("无法读取此文件，请检查后重试。");
    }
  }
  function download(kind: string) {
    if (game) window.location.assign(`/api/games/${game.id}/export/${kind}`);
    setMenu(false);
  }
  const texture = (type: string, owner: number) =>
    game
      ? `/api/games/${game.id}/textures/${encodeURIComponent(type)}/${owner}.svg?fp=${game.fingerprint}`
      : "";
  const preview = game?.displayed_ply !== null;
  const aiBusy = game?.ai.thinking || game?.ai.queued;
  const result = game?.result.status !== "ongoing";
  const humanTurn =
    game?.config.mode === "pvp" || game?.side_to_move === game?.config.human;
  const inspectedInfo = game?.rules.piece_types.find(
    (info) => info[0] === inspected,
  );
  const lastSaved =
    saved.find((item) => item.id === localStorage.getItem("gc-last-game")) ??
    saved[0];
  const statusText = game
    ? preview
      ? `回看第 ${game.displayed_ply} 步`
      : result
        ? game.result.winner === null
          ? "和棋"
          : `${sideName(game.result.winner)}获胜`
        : game.ai.paused
          ? "AI 已暂停"
          : aiBusy
            ? "AI 正在思考"
            : `${sideName(game.side_to_move)}行动`
    : "";
  const topOwner = 1 - orientation;
  function playerBar(owner: number) {
    if (!game) return null;
    const isHuman = game.config.mode === "pvp" || owner === game.config.human;
    return (
      <div
        className={`player-bar ${game.side_to_move === owner && !result ? "is-turn" : ""}`}
      >
        <div className={`avatar owner-${owner}`}>
          {isHuman ? <Circle size={19} /> : <Sparkles size={19} />}
        </div>
        <div className="player-name">
          <strong>
            {isHuman ? (game.config.mode === "pve" ? "你" : "玩家") : "Core AI"}
            <span>{sideName(owner)}</span>
          </strong>
          <small>
            {isHuman
              ? "自由思考，享受每一步"
              : `${game.config.think_seconds} 秒 / 步 · 真实引擎`}
          </small>
        </div>
        {game.side_to_move === owner && !result && (
          <span className={`turn-tag ${!isHuman && aiBusy ? "thinking" : ""}`}>
            {!isHuman && aiBusy ? "思考中" : "当前行动"}
          </span>
        )}
        <div className="hand-tray">
          {game.hands[owner].map((entry) => (
            <button
              key={entry.type_id}
              disabled={
                preview ||
                !humanTurn ||
                owner !== game.side_to_move ||
                aiBusy ||
                busy
              }
              className={hand === entry.type_id ? "selected-hand" : ""}
              title={`${translateName(game.types[entry.type_id]?.name ?? entry.type_id)} · 持子 ${entry.count}`}
              aria-label={`选择持子 ${entry.type_id}`}
              onClick={() => {
                setHand(hand === entry.type_id ? null : entry.type_id);
                setSelected(null);
                setInspected(entry.type_id);
              }}
            >
              <img src={texture(entry.type_id, owner)} alt="" />
              <span>{entry.count}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div
      className={`app ${reduceMotion ? "reduce-motion" : ""} ${orientation === 1 ? "flipped-board" : ""}`}
    >
      <header className="site-header">
        <button
          className="brand"
          onClick={() => (game ? void home() : undefined)}
        >
          <span className="brand-mark">
            <Leaf size={22} />
          </span>
          <span>
            弈境<small>GENERIC CHESS</small>
          </span>
        </button>
        <div className="header-note">
          <span className="live-dot" />
          本机运行 · 专注于棋
        </div>
        <div className="header-actions">
          <button
            className="icon-button"
            aria-label="切换减少动态效果"
            aria-pressed={reduceMotion}
            title="减少动态效果"
            onClick={() => {
              setReduceMotion(!reduceMotion);
              localStorage.setItem(
                "gc-motion",
                !reduceMotion ? "reduced" : "full",
              );
            }}
          >
            <Settings2 size={19} />
          </button>
          {game && (
            <button
              className="button compact"
              onClick={() => {
                setConfig(game.config);
                setSetup(true);
              }}
            >
              <Plus size={17} />
              新对局
            </button>
          )}
        </div>
      </header>
      {error && (
        <div className="error-banner" role="alert">
          {error}
          <button aria-label="关闭提示" onClick={() => setError("")}>
            <X size={16} />
          </button>
        </div>
      )}
      {!game ? (
        <main className="landing">
          <section className="hero">
            <p className="eyebrow">
              <span />
              一张棋盘，无限可能
            </p>
            <h1>
              下一步，
              <br />
              走进未知。
            </h1>
            <p className="hero-description">
              熟悉的棋，新的规则。
              <br />
              与真实 AI 对弈，探索每一局独一无二的可能。
            </p>
            <button
              className="button primary large"
              onClick={() => setSetup(true)}
            >
              开始一局
              <ArrowRight size={19} />
            </button>
            {lastSaved && (
              <button
                className="continue-link"
                disabled={busy}
                onClick={() => void resume(lastSaved.id)}
              >
                <History size={16} />
                继续上次对局 · {titles[lastSaved.config.kind]}
                <ChevronRight size={17} />
              </button>
            )}
            <div className="hero-foot">
              <span>01 — 自由探索</span>
              <span>02 — 真实对弈</span>
              <span>03 — 随时继续</span>
            </div>
          </section>
          <section className="hero-board" aria-label="装饰棋盘">
            <div className="ornament-label">
              <Sparkles size={16} />
              THE NEXT MOVE IS YOURS
            </div>
            <div className="mini-board">
              {Array.from({ length: 64 }, (_, i) => (
                <div
                  key={i}
                  className={(Math.floor(i / 8) + (i % 8)) % 2 ? "dark" : ""}
                >
                  {[0, 7, 56, 63].includes(i) ? (
                    <span className="demo-rook">♜</span>
                  ) : [4, 60].includes(i) ? (
                    <span className="demo-king">♚</span>
                  ) : Math.floor(i / 8) === 1 || Math.floor(i / 8) === 6 ? (
                    <span className={i > 32 ? "light-piece" : ""}>♟</span>
                  ) : null}
                </div>
              ))}
            </div>
            <div className="board-caption">
              <span>秩序之中，发现变化。</span>
              <span>8 × 8</span>
            </div>
          </section>
          <section className="game-cards">
            {(["generated", "western_chess", "standard_shogi"] as const).map(
              (kind, i) => (
                <button
                  key={kind}
                  onClick={() => {
                    setConfig({ ...defaults, kind });
                    setSetup(true);
                  }}
                >
                  <span className="card-number">0{i + 1}</span>
                  <div>
                    <h2>{titles[kind]}</h2>
                    <p>
                      {i === 0
                        ? "随机规则，每次都有新发现"
                        : i === 1
                          ? "经典策略，熟悉的深度"
                          : "持子打入，变化无穷"}
                    </p>
                  </div>
                  <ArrowRight size={18} />
                </button>
              ),
            )}
          </section>
          {saved.length > 1 && (
            <section className="saved-games">
              <h2>最近的棋局</h2>
              {saved.slice(0, 5).map((item) => (
                <button
                  key={item.id}
                  onClick={() => void resume(item.id)}
                  disabled={busy}
                >
                  <span>
                    {titles[item.config.kind]} · {item.ply} 步
                  </span>
                  <small>
                    {new Date(item.updated * 1000).toLocaleString("zh-CN")}
                  </small>
                  <ChevronRight size={16} />
                </button>
              ))}
            </section>
          )}
        </main>
      ) : (
        <main className="game-layout">
          <section className="play-area">
            <div className="match-heading">
              <div>
                <p className="eyebrow">THE BOARD / 棋局</p>
                <h1>
                  {titles[game.config.kind]}
                  <span>
                    {game.board_size} × {game.board_size}
                    {game.seed !== null
                      ? ` · #${game.seed}`
                      : ` · ${game.fingerprint.slice(0, 6)}`}
                  </span>
                </h1>
              </div>
              <button
                className="icon-button"
                aria-label="对局菜单"
                onClick={() => setMenu(!menu)}
              >
                <Menu size={21} />
              </button>
              {menu && (
                <div className="game-menu">
                  <button onClick={() => download("bundle")}>
                    <Download size={16} />
                    导出续局包
                  </button>
                  <button onClick={() => download("record")}>
                    <Download size={16} />
                    导出棋谱
                  </button>
                  <button onClick={() => download("rules")}>
                    <Download size={16} />
                    导出规则
                  </button>
                  <button onClick={() => importFile("bundle")}>
                    <Upload size={16} />
                    导入续局包
                  </button>
                  <button onClick={() => importFile("record")}>
                    <Upload size={16} />
                    导入棋谱
                  </button>
                  <button onClick={() => importFile("rules")}>
                    <Upload size={16} />
                    导入规则
                  </button>
                  <button onClick={() => void home()}>
                    <ArrowLeft size={16} />
                    保存并返回首页
                  </button>
                </div>
              )}
            </div>
            {playerBar(topOwner)}
            <div className="board-frame">
              <div
                className="board"
                role="grid"
                aria-label="棋盘"
                style={{
                  gridTemplateColumns: `repeat(${game.board_size},1fr)`,
                }}
              >
                {Array.from({ length: game.board_size ** 2 }, (_, index) => {
                  const displayFile = index % game.board_size,
                    displayRank = Math.floor(index / game.board_size);
                  const f =
                    orientation === 0
                      ? displayFile
                      : game.board_size - 1 - displayFile;
                  const r =
                    orientation === 0
                      ? game.board_size - 1 - displayRank
                      : displayRank;
                  const sq = game.squares[r * game.board_size + f];
                  const point: Point = [f, r];
                  const legal = relevant.some((offer) =>
                    same(offer.action.to, point),
                  );
                  return (
                    <button
                      role="gridcell"
                      key={`${f}-${r}`}
                      data-square={coordinate(point)}
                      aria-label={`${coordinate(point)}${sq.piece ? ` ${sideName(sq.piece.owner)} ${translateName(sq.piece.name)}` : " 空格"}${legal ? " 可行动" : ""}`}
                      aria-selected={same(selected, point)}
                      className={`square ${(f + r) % 2 === 0 ? "dark-square" : "light-square"} ${same(selected, point) ? "selected-square" : ""} ${sq.last_from || sq.last_to ? "last-move" : ""} ${sq.check ? "check-square" : ""} ${legal && sq.piece ? "legal-capture" : ""}`}
                      onPointerDown={(e) => {
                        if (e.button !== 0) return;
                        if (e.pointerType !== "mouse") e.preventDefault();
                        squareClicked(point);
                      }}
                      onClick={(e) => {
                        if (e.detail === 0) squareClicked(point);
                      }}
                      onKeyDown={(e) => {
                        if (
                          [
                            "ArrowLeft",
                            "ArrowRight",
                            "ArrowUp",
                            "ArrowDown",
                          ].includes(e.key)
                        ) {
                          e.preventDefault();
                          const offset = {
                            ArrowLeft: -1,
                            ArrowRight: 1,
                            ArrowUp: -game.board_size,
                            ArrowDown: game.board_size,
                          }[e.key]!;
                          const elements =
                            e.currentTarget.parentElement!.querySelectorAll<HTMLButtonElement>(
                              '[role="gridcell"]',
                            );
                          elements[
                            Math.max(
                              0,
                              Math.min(elements.length - 1, index + offset),
                            )
                          ].focus();
                        }
                        if (e.key === "Escape") {
                          setSelected(null);
                          setHand(null);
                          setChoices([]);
                        }
                      }}
                    >
                      {displayFile === 0 && (
                        <span className="rank-label">{r + 1}</span>
                      )}
                      {displayRank === game.board_size - 1 && (
                        <span className="file-label">
                          {String.fromCharCode(97 + f)}
                        </span>
                      )}
                      {legal && !sq.piece && <span className="legal-dot" />}
                      {sq.piece && (
                        <img
                          style={(() => {
                            const last = game.history.at(-1)?.action;
                            return sq.last_to && last?.from && last.to
                              ? ({
                                  "--from-x": `${(((last.from[0] - last.to[0]) * 100) / 0.86) * (orientation === 0 ? 1 : -1)}%`,
                                  "--from-y": `${(((last.from[1] - last.to[1]) * 100) / 0.86) * (orientation === 0 ? -1 : 1)}%`,
                                } as CSSProperties)
                              : undefined;
                          })()}
                          className={`piece owner-${sq.piece.owner} ${sq.last_to && !preview ? "just-moved" : ""}`}
                          key={`${sq.piece.owner}-${sq.piece.type}`}
                          src={texture(sq.piece.type, sq.piece.owner)}
                          alt={translateName(sq.piece.name)}
                          draggable={false}
                        />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
            {playerBar(orientation)}
            <div className="board-toolbar">
              <div className="status-pill">
                <span className={aiBusy ? "pulse-dot" : "live-dot"} />
                <span aria-live="polite">{statusText}</span>
                {game.squares.some((sq) => sq.check) && !result && (
                  <strong className="check-label">将军</strong>
                )}
              </div>
              <div className="board-tools">
                <button
                  title="翻转棋盘"
                  aria-label="翻转棋盘"
                  onClick={() => setOrientation(1 - orientation)}
                >
                  <FlipVertical2 size={18} />
                </button>
                <button
                  title="悔棋"
                  aria-label="悔棋"
                  disabled={!game.can_undo || busy || !connected}
                  onClick={() => void operate("undo")}
                >
                  <RotateCcw size={18} />
                </button>
                <button
                  title="重新开局"
                  aria-label="重新开局"
                  disabled={busy || !connected}
                  onClick={() => {
                    if (window.confirm("重新开始这局棋？当前棋谱将清空。"))
                      void operate("restart");
                  }}
                >
                  <Plus size={19} />
                </button>
                <button
                  title={humanTurn ? "认输" : "轮到你时可认输"}
                  aria-label="认输"
                  disabled={
                    !!result || !!preview || busy || !humanTurn || !connected
                  }
                  onClick={() => {
                    if (window.confirm("确定认输并结束本局？"))
                      void operate("resign");
                  }}
                >
                  <Flag size={18} />
                </button>
              </div>
            </div>
            {!connected && (
              <div className="connection-note" role="status">
                连接已断开，正在恢复。未确认的操作不会自动重发。
              </div>
            )}
            {game.storage_error && (
              <div className="connection-note" role="alert">
                {game.storage_error}
              </div>
            )}
            {game.ai.error && (
              <div className="connection-note" role="alert">
                {game.ai.error}
              </div>
            )}
            {game.config.mode === "pve" && !result && !preview && (
              <div className="ai-control">
                <span>
                  {game.ai.paused
                    ? "思考已暂停，棋局已保存"
                    : "人机对局 · 每一步都由真实引擎计算"}
                </span>
                <button
                  disabled={busy || !connected}
                  onClick={() =>
                    void operate(game.ai.paused ? "resume_ai" : "pause_ai")
                  }
                >
                  {game.ai.paused ? <Play size={14} /> : <Pause size={14} />}{" "}
                  {game.ai.paused ? "继续 AI" : "暂停 AI"}
                </button>
              </div>
            )}
            {!!result && !preview && (
              <div className="result-card" role="status">
                <span className="result-symbol">
                  <Check size={23} />
                </span>
                <div>
                  <h2>{statusText}</h2>
                  <p>
                    {endNames[game.result.status] ?? game.result.status} ·
                    棋局已自动保存
                  </p>
                </div>
                <button className="button" onClick={() => setSetup(true)}>
                  再来一局
                  <ArrowRight size={16} />
                </button>
              </div>
            )}
            {game.actions
              .filter((o) => o.action.kind === "pass")
              .map((o) => (
                <button className="button" key={o.id} onClick={() => choose(o)}>
                  停着
                </button>
              ))}
          </section>
          <aside className="sidebar">
            <div className="sidebar-tabs" role="tablist">
              <button
                role="tab"
                aria-selected={tab === "history"}
                className={tab === "history" ? "active" : ""}
                onClick={() => setTab("history")}
              >
                <History size={16} />
                棋谱
              </button>
              <button
                role="tab"
                aria-selected={tab === "rules"}
                className={tab === "rules" ? "active" : ""}
                onClick={() => setTab("rules")}
              >
                <BookOpen size={16} />
                规则
              </button>
            </div>
            {tab === "history" ? (
              <div className="history-pane">
                <div className="pane-heading">
                  <h2>每一步，都有意义。</h2>
                  <span>{game.ply} 步</span>
                </div>
                {!game.history.length ? (
                  <div className="empty-history">
                    <History size={34} strokeWidth={1} />
                    <p>棋局，始于第一步。</p>
                    <small>走过的每一步，都会记录在这里。</small>
                  </div>
                ) : (
                  <div className="move-list">
                    <button
                      className={game.displayed_ply === 0 ? "active" : ""}
                      disabled={busy || !connected}
                      onClick={() => void operate("history", { ply: 0 })}
                    >
                      <span className="move-num">—</span>
                      <span>初始局面</span>
                    </button>
                    {game.history.map((entry) => (
                      <button
                        key={entry.ply}
                        disabled={busy || !connected}
                        className={
                          game.displayed_ply === entry.ply ? "active" : ""
                        }
                        onClick={() =>
                          void operate("history", { ply: entry.ply })
                        }
                      >
                        <span className="move-num">
                          {String(entry.ply).padStart(2, "0")}
                        </span>
                        <span className={`move-side side-${entry.player}`} />
                        <span>{moveLabel(entry.action)}</span>
                        <ChevronRight size={14} />
                      </button>
                    ))}
                  </div>
                )}
                {preview && (
                  <button
                    className="button return-live"
                    disabled={busy || !connected}
                    onClick={() => void operate("live")}
                  >
                    返回当前棋局
                    <ArrowRight size={16} />
                  </button>
                )}
                <div className="saved-note">
                  <Check size={14} />
                  自动保存 · 随时回来继续
                </div>
              </div>
            ) : (
              <div className="rules-pane">
                <div className="pane-heading">
                  <h2>认识这张棋盘。</h2>
                  <span>{Object.keys(game.types).length} 种棋子</span>
                </div>
                <p className="rules-intro">
                  选择棋子，查看它的走法。可走位置由真实规则引擎计算。
                </p>
                <div className="piece-catalog">
                  {game.rules.piece_types.map(([id, name]) => (
                    <button
                      key={id}
                      className={inspected === id ? "active" : ""}
                      onClick={() => setInspected(id)}
                    >
                      <img src={texture(id, orientation)} alt="" />
                      <span>{translateName(name)}</span>
                      {game.types[id].anchor && <small>王</small>}
                    </button>
                  ))}
                </div>
                <section className="rule-summary">
                  <h3>对局规则</h3>
                  <p>持子允许打入的位置（格数）：{game.rules.drop_summary}</p>
                  <p>{terminalText(game.rules.terminal_summary)}</p>
                  {game.rules.promotion_relations.length > 0 && (
                    <p>升变关系：{game.rules.promotion_relations.join("；")}</p>
                  )}
                </section>
              </div>
            )}
            <section className="piece-inspector">
              <div className="inspector-heading">
                <CircleHelp size={16} />
                <span>棋子手册</span>
              </div>
              {inspectedInfo ? (
                <>
                  <div className="inspector-piece">
                    <img src={texture(inspectedInfo[0], orientation)} alt="" />
                    <div>
                      <h3>{translateName(inspectedInfo[1])}</h3>
                      <small>{inspectedInfo[0]}</small>
                    </div>
                  </div>
                  <ul>
                    {inspectedInfo[2].map((line, index) => (
                      <li key={index}>{ruleText(line)}</li>
                    ))}
                  </ul>
                  <p className="hint">点击棋子，查看当前局面的合法目标。</p>
                </>
              ) : (
                <p className="hint">
                  点击任意棋子，了解它的走法。
                  <br />
                  生成棋的每一枚棋子都可能不同。
                </p>
              )}
            </section>
          </aside>
        </main>
      )}
      <footer className="site-footer">
        <span>弈境 / GENERIC CHESS</span>
        <span>
          把时间留给下一步。
          <Leaf size={13} />
        </span>
      </footer>
      <input
        ref={file}
        type="file"
        accept=".json,application/json"
        hidden
        onChange={(e) => {
          void readFile(e.target.files);
          e.target.value = "";
        }}
      />
      {setup && (
        <div className="modal-backdrop" onClick={() => setSetup(false)}>
          <section
            className="modal setup-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="setup-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="modal-close icon-button"
              aria-label="关闭新对局"
              onClick={() => setSetup(false)}
            >
              <X size={20} />
            </button>
            <p className="eyebrow">A FRESH START</p>
            <h2 id="setup-title">开启新的棋局</h2>
            <p className="modal-subtitle">选择规则，剩下的交给你的下一步。</p>
            <div className="kind-tabs">
              {Object.entries(titles).map(([kind, title]) => (
                <button
                  key={kind}
                  className={config.kind === kind ? "active" : ""}
                  onClick={() =>
                    setConfig({ ...config, kind: kind as Config["kind"] })
                  }
                >
                  {title}
                </button>
              ))}
            </div>
            {["generated", "hybrid"].includes(config.kind) && (
              <div className="form-grid">
                <label>
                  随机种子
                  <div className="input-with-action">
                    <input
                      aria-label="随机种子"
                      type="number"
                      min="0"
                      max="2147483647"
                      value={config.seed}
                      onChange={(e) =>
                        setConfig({ ...config, seed: Number(e.target.value) })
                      }
                    />
                    <button
                      aria-label="随机生成种子"
                      onClick={() =>
                        setConfig({
                          ...config,
                          seed:
                            crypto.getRandomValues(new Uint32Array(1))[0] %
                            2147483648,
                        })
                      }
                    >
                      <Shuffle size={16} />
                    </button>
                  </div>
                </label>
                <label>
                  棋盘大小
                  <select
                    aria-label="棋盘大小"
                    value={config.board_size}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        board_size: Number(e.target.value),
                      })
                    }
                  >
                    {[4, 6, 8, 9, 10, 12].map((n) => (
                      <option value={n} key={n}>
                        {n} × {n}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="full-width">
                  初始布局
                  <select
                    aria-label="初始布局"
                    value={config.preset}
                    onChange={(e) =>
                      setConfig({ ...config, preset: e.target.value })
                    }
                  >
                    <option value="classic_like">经典布局</option>
                    <option value="bilateral_random">对称随机</option>
                    <option value="free_random">自由随机</option>
                  </select>
                </label>
              </div>
            )}
            <div className="form-grid">
              <label>
                对局方式
                <select
                  aria-label="对局方式"
                  value={config.mode}
                  onChange={(e) =>
                    setConfig({
                      ...config,
                      mode: e.target.value as Config["mode"],
                    })
                  }
                >
                  <option value="pve">与 AI 对弈</option>
                  <option value="pvp">同屏双人</option>
                </select>
              </label>
              {config.mode === "pve" && (
                <label>
                  我的位置
                  <select
                    aria-label="我的位置"
                    value={config.human}
                    onChange={(e) =>
                      setConfig({
                        ...config,
                        human: Number(e.target.value) as 0 | 1,
                      })
                    }
                  >
                    <option value="0">先手</option>
                    <option value="1">后手</option>
                  </select>
                </label>
              )}
              {config.mode === "pve" && (
                <label className="full-width">
                  AI 思考时间
                  <div className="segmented">
                    {[0.5, 1, 3].map((n) => (
                      <button
                        key={n}
                        className={config.think_seconds === n ? "active" : ""}
                        onClick={() =>
                          setConfig({ ...config, think_seconds: n })
                        }
                      >
                        {n} 秒
                      </button>
                    ))}
                  </div>
                </label>
              )}
            </div>
            <div className="setup-note">
              <Sparkles size={16} />
              使用完整 Python Core AI · 无对局倒计时
            </div>
            <button
              className="button primary full-width"
              disabled={busy}
              onClick={() => void start()}
            >
              {busy ? "正在准备棋局…" : "开始对局"}
              <ArrowRight size={17} />
            </button>
          </section>
        </div>
      )}
      {!!choices.length && (
        <div className="modal-backdrop">
          <section
            className="modal choice-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="choice-title"
          >
            <button
              className="modal-close icon-button"
              aria-label="取消行动选择"
              onClick={() => setChoices([])}
            >
              <X size={19} />
            </button>
            <p className="eyebrow">YOUR CHOICE</p>
            <h2 id="choice-title">选择这一步的变化</h2>
            <p className="modal-subtitle">此目标有多种合法行动，请选择。</p>
            {choices.map((offer) => (
              <button
                className="choice-option"
                key={offer.id}
                onClick={() => choose(offer)}
              >
                {offer.action.promotion_target_id ? (
                  <>
                    <img
                      src={texture(
                        offer.action.promotion_target_id,
                        game!.side_to_move,
                      )}
                      alt=""
                    />
                    <span>
                      升变为{" "}
                      {translateName(
                        game!.types[offer.action.promotion_target_id]?.name ??
                          offer.action.promotion_target_id,
                      )}
                    </span>
                  </>
                ) : (
                  <span>保持原样</span>
                )}
                {offer.action.pattern_id && (
                  <small>
                    {offer.action.pattern_id} / {offer.action.geometry_id}
                  </small>
                )}
                <ChevronRight size={16} />
              </button>
            ))}
          </section>
        </div>
      )}
    </div>
  );
}
