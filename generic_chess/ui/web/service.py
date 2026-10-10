"""Serialized UI sessions and a single cooperative AI worker for local play."""
from __future__ import annotations
import asyncio
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import time
import uuid

from ...ai.budget import ThinkingConfig, ThinkingStrategy
from ...ai.cancellation import CancellationToken
from ...clock import TimeControl, TimeControlMode
from ...core.actions import action_to_dict
from ...rules.serialization import deserialize_ruleset, serialize_ruleset
from ...visual.textures import generate_piece_texture
from ..ai_backend import create_ui_player
from ..controller import UIController
from ..match import MatchConfig, ParticipantKind
from ..stores import DictSettingsStore
from .models import GameConfig, Operation

class GameError(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message, self.status = message, status


def make_controller(config: GameConfig) -> UIController:
    ctrl = UIController(settings=DictSettingsStore())
    if config.kind in ("generated", "hybrid"):
        ok = ctrl.new_game(seed=config.seed, board_size=config.board_size,
                           preset=config.preset, hybrid=config.kind == "hybrid")
    else:
        ok = ctrl.new_game_from_builtin(config.kind)
    if not ok:
        raise GameError("无法创建此规则棋局，请尝试其他种子或配置。")
    configure_match(ctrl, config)
    return ctrl


def configure_match(ctrl: UIController, config: GameConfig):
    players = tuple(ParticipantKind.HUMAN if config.mode == "pvp" or i == config.human
                    else ParticipantKind.AI for i in range(2))
    ctrl.start_match(MatchConfig(participants=players,
        time_control=TimeControl(mode=TimeControlMode.NONE),
        ai_config=ThinkingConfig(strategy=ThinkingStrategy.FIXED_TIME,
                                 move_time_seconds=config.think_seconds)))


class WebGame:
    def __init__(self, service, config, controller, game_id=None):
        self.service, self.config, self.controller = service, config, controller
        self.id = game_id or uuid.uuid4().hex
        self.revision = 0
        self.active = True
        self.paused = False
        self.ai_error = None
        self.storage_error = None
        self.task = None
        self.token = None
        self.player = None
        self.lock = asyncio.Lock()
        self.listeners = set()
        self.requests = OrderedDict()
        self.updated = time.time()
        self.seed = controller.game_info().seed if controller.session else None
        self._legal_key = None
        self._legal = ()
        self._rules = None
        self._state = None

    def legal(self):
        ctrl = self.controller
        key = (id(ctrl.session), ctrl.session.state.ply_count, ctrl.session.result.status.value)
        if key != self._legal_key:
            self._legal = tuple(ctrl.session.legal_actions()) if ctrl.session.result.status.value == "ongoing" else ()
            self._legal_key = key
        return self._legal

    def can_undo(self):
        ctrl = self.controller
        if ctrl.interaction.displayed_ply is not None or not ctrl.can_undo:
            return False
        if self.config.mode == "pvp":
            return True
        return any(entry.player == self.config.human for entry in ctrl.history_entries())

    def snapshot(self):
        if self._state is not None:
            return self._state
        ctrl = self.controller
        board = ctrl.board_view_model()
        info = ctrl.game_info()
        if self._rules is None:
            self._rules = asdict(ctrl.rules_info())
        human_turn = self.config.mode == "pvp" or board.side_to_move == self.config.human
        live = not board.is_history_preview
        actions = [dict(id=f"{self.revision}:{i}", action=action_to_dict(action), label=str(action))
                   for i, action in enumerate(self.legal())] if live and human_turn and not ctrl.ai_thinking and self.active else []
        types = {p.type_id: {"id": p.type_id, "name": p.name, "anchor": p.is_anchor}
                 for p in ctrl.compiled.piece_types}
        squares = []
        for square in board.squares:
            piece = square.piece
            squares.append({"file": square.square.file, "rank": square.square.rank,
                "piece": None if piece is None else {"owner": piece.owner,
                    "type": piece.current_type_id, "base_type": piece.base_type_id,
                    "promoted": piece.promoted, "name": types[piece.current_type_id]["name"]},
                "last_from": square.is_last_move_from, "last_to": square.is_last_move_to,
                "check": square.is_check_anchor})
        # History view hands must match the displayed position, not the live game.
        pos = ctrl.displayed_position()
        hands = [[{"type_id": tid, "count": count} for tid, count in pos.hands[owner].counts]
                 for owner in (0, 1)]
        self._state = {"id": self.id, "revision": self.revision, "config": self.config.model_dump(),
            "board_size": board.board_size, "side_to_move": board.side_to_move,
            "squares": squares, "hands": hands, "types": types, "rules": self._rules,
            "fingerprint": info.fingerprint, "seed": self.seed,
            "ply": info.ply_count, "displayed_ply": ctrl.interaction.displayed_ply,
            "result": {"status": info.result.status.value, "winner": info.result.winner},
            "history": [{"ply": e.ply, "player": e.player, "label": e.label,
                         "action": action_to_dict(e.action)} for e in ctrl.history_entries()],
            "actions": actions, "can_undo": self.can_undo(), "active": self.active,
            "ai": {"thinking": ctrl.ai_thinking, "queued": bool(self.task) and not ctrl.ai_thinking,
                   "paused": self.paused, "error": self.ai_error}, "storage_error": self.storage_error}
        return self._state

    def touch(self, persist=False):
        self.revision += 1
        self.updated = time.time()
        self._state = None
        if persist:
            self.save()
        for queue in tuple(self.listeners):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(True)

    def bundle(self):
        return {"schema": "generic-chess-web-v1", "config": self.config.model_dump(),
                "rules": json.loads(serialize_ruleset(self.controller.ruleset)),
                "record": json.loads(self.controller.record_text()), "paused": self.paused, "seed": self.seed}

    def save(self):
        path = self.service.state_dir / f"{self.id}.json"
        temp = path.with_suffix(".tmp")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {"id": self.id, "revision": self.revision, "updated": self.updated,
                    "bundle": self.bundle()}
            temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            temp.replace(path)
            self.storage_error = None
        except OSError:
            self.storage_error = "自动保存失败，请立即导出续局包。"

    def kick(self):
        if (self.task is not None or not self.active or self.paused
                or not self.controller.ai_move_needed() or self.service.closing):
            return
        self.task = asyncio.create_task(self.run_ai())
        self.touch()

    async def run_ai(self):
        snapshot = None
        token = None
        try:
            async with self.service.worker_lock:
                if not self.active or self.paused or not self.controller.ai_move_needed():
                    return
                token = CancellationToken()
                self.token = token
                snapshot = self.controller.capture_ai_search(token)
                if snapshot is None:
                    return
                if self.player is None:
                    self.player = create_ui_player(self.controller.compiled, use_disk_cache=False)
                player = self.player
                self.touch()
                decision = await asyncio.get_running_loop().run_in_executor(
                    self.service.executor,
                    lambda: player.choose_action(snapshot.session, snapshot.limits, cancel_token=token))
                async with self.lock:
                    # The original token remains authoritative even after undo/restart resets controller fields.
                    if not token.is_cancelled():
                        committed = self.controller.finish_ai_move(decision, snapshot)
                        if not committed and self.active and not self.paused:
                            self.ai_error = "AI 未能提交合法行动，可重试或重开棋局。"
                            self.paused = True
                    self.touch(persist=True)
        except Exception:
            async with self.lock:
                if token is None or not token.is_cancelled():
                    if snapshot is not None:
                        self.controller.finish_ai_move(None, snapshot)
                    self.ai_error = "AI 思考失败，棋局已保留；请点击继续 AI 重试。"
                    self.paused = True
                    self.touch(persist=True)
        finally:
            self.task = None
            self.token = None
            self.touch()
            self.kick()

    def cancel_search(self):
        if self.token is not None:
            self.token.cancel()
        self.controller.cancel_ai()

    async def suspend(self):
        async with self.lock:
            self.active = False
            self.cancel_search()
            self.touch(persist=True)

    def imported(self, fmt, content):
        try:
            payload = json.loads(content) if isinstance(content, str) else content
            config = self.config
            ctrl = UIController(settings=DictSettingsStore())
            if fmt == "bundle":
                if not isinstance(payload, dict) or payload.get("schema") != "generic-chess-web-v1":
                    raise ValueError("invalid bundle")
                config = GameConfig.model_validate(payload["config"])
                rules = payload["rules"]
                record = payload["record"]
                paused = bool(payload.get("paused", False))
            elif fmt == "rules":
                rules, record, paused = payload, None, self.paused
            elif fmt == "record":
                rules = json.loads(serialize_ruleset(self.controller.ruleset))
                record, paused = payload, self.paused
            else:
                raise ValueError("invalid format")
            if not ctrl.new_game_from_ruleset(deserialize_ruleset(json.dumps(rules))):
                raise ValueError("invalid rules")
            if record is not None and not ctrl.load_record_text(json.dumps(record)):
                raise ValueError("invalid record")
            configure_match(ctrl, config)
            return ctrl, config, paused
        except (ValueError, KeyError, TypeError):
            raise GameError("文件无效或棋谱与规则不匹配，当前棋局未改变。") from None

    async def operate(self, op: Operation):
        async with self.lock:
            payload = op.model_dump(exclude={"expected_revision"})
            if op.request_id in self.requests:
                if self.requests[op.request_id] != payload:
                    raise GameError("请求标识已使用，请刷新后重试。", 409)
                return self.snapshot()
            if op.expected_revision != self.revision:
                raise GameError("棋局已更新，请根据当前局面重试。", 409)
            ctrl = self.controller
            kind = op.kind
            if kind == "action":
                offered = {entry["id"]: i for i, entry in enumerate(self.snapshot()["actions"])}
                if op.action_id not in offered:
                    raise GameError("此行动已失效或不是当前合法行动。")
                action = self.legal()[offered[op.action_id]]
                if not ctrl.submit_action(action):
                    raise GameError("无法执行此行动，棋局未改变。")
            elif kind == "undo":
                if not self.can_undo():
                    raise GameError("当前没有可以撤回的玩家行动。")
                entries = ctrl.history_entries()
                count = 1 if self.config.mode == "pvp" else len(entries) - max(i for i,e in enumerate(entries) if e.player == self.config.human)
                self.cancel_search()
                for _ in range(count):
                    if not ctrl.undo():
                        raise GameError("无法悔棋。")
                self.paused = False
                ctrl.clear_stop_request()
            elif kind == "restart":
                self.cancel_search()
                ctrl.restart()
                ctrl.clear_stop_request()
                self.player = None
                self.paused = False
                self.ai_error = None
            elif kind == "resign":
                if ctrl.interaction.displayed_ply is not None or ctrl.session.result.status.value != "ongoing":
                    raise GameError("当前无法认输。")
                if self.config.mode == "pve" and ctrl.session.state.position.side_to_move != self.config.human:
                    raise GameError("请在轮到你时认输。")
                self.cancel_search()
                if not ctrl.resign():
                    raise GameError("当前无法认输。")
            elif kind == "history":
                if op.ply is None or op.ply > ctrl.session.state.ply_count:
                    raise GameError("棋谱位置无效。")
                self.cancel_search()
                if not ctrl.display_ply(op.ply):
                    raise GameError("无法查看此棋谱位置。")
            elif kind == "live":
                ctrl.return_to_current()
                if not self.paused:
                    ctrl.clear_stop_request()
            elif kind in ("pause_ai", "suspend"):
                self.cancel_search()
                if kind == "suspend":
                    self.active = False
                else:
                    self.paused = True
            elif kind in ("resume", "resume_ai"):
                self.active = True
                self.paused = False
                self.ai_error = None
                ctrl.clear_stop_request()
            elif kind == "import":
                # Validate/replay on a separate controller before cancelling or swapping the live one.
                new_ctrl, config, paused = self.imported(op.format, op.content)
                self.cancel_search()
                old_fingerprint = self.controller.compiled.ruleset_fingerprint
                if op.format == "bundle":
                    payload = json.loads(op.content) if isinstance(op.content, str) else op.content
                    self.seed = payload.get("seed")
                elif op.format == "rules" or new_ctrl.compiled.ruleset_fingerprint != old_fingerprint:
                    self.seed = None
                self.controller, self.config, self.paused = new_ctrl, config, paused
                self.player = None
                self.ai_error = None
                self._rules = None
                self._legal_key = None
            self._state = None
            self.requests[op.request_id] = payload
            while len(self.requests) > 128:
                self.requests.popitem(last=False)
            self.touch(persist=True)
            self.kick()
            return self.snapshot()


class GameService:
    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.games = {}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="web-ai")
        self.worker_lock = asyncio.Lock()
        self.closing = False

    def get(self, game_id):
        if game_id not in self.games:
            try:
                if len(game_id) != 32 or any(c not in "0123456789abcdef" for c in game_id):
                    raise ValueError("bad id")
                saved = json.loads((self.state_dir / f"{game_id}.json").read_text(encoding="utf-8"))
                config = GameConfig.model_validate(saved["bundle"]["config"])
                ctrl = UIController(settings=DictSettingsStore())
                game = WebGame(self, config, ctrl, game_id)
                game.controller, game.config, game.paused = game.imported("bundle", saved["bundle"])
                game.revision = int(saved["revision"]) + 1
                game.updated = saved["updated"]
                game.seed = saved["bundle"].get("seed")
                game.active = False
                self.games[game_id] = game
            except (OSError, ValueError, KeyError, TypeError, GameError):
                raise GameError("未找到可恢复的棋局，请新建或导入续局包。", 404) from None
        return self.games[game_id]

    def listing(self):
        result = []
        errors = 0
        for path in self.state_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                config = GameConfig.model_validate(data["bundle"]["config"])
                result.append({"id": path.stem, "config": config.model_dump(), "updated": data["updated"],
                               "ply": len(data["bundle"]["record"]["actions"])})
            except (OSError, ValueError, KeyError, TypeError):
                errors += 1
        return {"games": sorted(result, key=lambda item: item["updated"], reverse=True),
                "warning": f"有 {errors} 个存档无法读取，请使用已导出的续局包。" if errors else None}

    def create(self, config):
        game = WebGame(self, config, make_controller(config))
        self.games[game.id] = game
        game.touch(persist=True)
        game.kick()
        return game

    async def close(self):
        self.closing = True
        for game in self.games.values():
            await game.suspend()
        tasks = [game.task for game in self.games.values() if game.task]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.executor.shutdown(wait=True, cancel_futures=True)
