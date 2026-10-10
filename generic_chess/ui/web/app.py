"""Loopback-only HTTP and WebSocket presentation adapter."""
from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from ...rules.serialization import serialize_ruleset
from ...visual.textures import generate_piece_texture
from .models import CreateGame, Operation
from .service import GameService, GameError

ROOT = Path(__file__).resolve().parents[3]


def allowed_origin(origin, host):
    if not origin:
        return True
    parsed = urlsplit(origin)
    return parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost") and (
        parsed.netloc == host or parsed.port == 5173)


def create_app(state_dir=None, dist_dir=None):
    service = GameService(Path(state_dir) if state_dir is not None else ROOT / ".web_state")
    textures = {}

    @asynccontextmanager
    async def lifespan(app):
        yield
        await service.close()

    app = FastAPI(title="GenericChess Web", lifespan=lifespan)
    app.state.service = service
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if not allowed_origin(request.headers.get("origin"), request.headers.get("host")):
            return JSONResponse({"error": "仅允许本机游戏页面访问。"}, status_code=403)
        if int(request.headers.get("content-length", "0")) > 5_000_000:
            return JSONResponse({"error": "文件过大，请使用小于 5 MB 的棋谱或续局包。"}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(GameError)
    async def game_error(request, exc):
        body = {"error": exc.message}
        game_id = request.path_params.get("game_id")
        if game_id in service.games:
            body["state"] = service.games[game_id].snapshot()
        return JSONResponse(body, status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse({"error": "输入格式或配置无效，请检查后重试。"}, status_code=422)

    @app.get("/api/health")
    async def health():
        return {"ok": True, "mode": "local", "backend": "python-core"}

    @app.get("/api/games")
    async def games():
        return service.listing()

    @app.post("/api/games")
    async def create(body: CreateGame):
        # Create/validate before changing the previous game.
        game = service.create(body.config)
        if body.previous_id and body.previous_id in service.games:
            await service.games[body.previous_id].suspend()
        return game.snapshot()

    @app.get("/api/games/{game_id}")
    async def state(game_id: str):
        return service.get(game_id).snapshot()

    @app.post("/api/games/{game_id}/operations")
    async def operation(game_id: str, body: Operation):
        return await service.get(game_id).operate(body)

    @app.get("/api/games/{game_id}/export/{fmt}")
    async def export(game_id: str, fmt: str):
        game = service.get(game_id)
        if fmt == "record":
            content = game.controller.record_text()
        elif fmt == "rules":
            content = serialize_ruleset(game.controller.ruleset)
        elif fmt == "bundle":
            content = json.dumps(game.bundle(), ensure_ascii=False, indent=2)
        else:
            raise GameError("导出格式无效。")
        return Response(content, media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="generic-chess-{fmt}.json"'})

    @app.get("/api/games/{game_id}/textures/{type_id}/{owner}.svg")
    async def texture(game_id: str, type_id: str, owner: int):
        game = service.get(game_id)
        if owner not in (0, 1) or type_id not in game.controller.compiled.types_by_id:
            raise GameError("棋子纹理不存在。", 404)
        key = (game.controller.compiled.ruleset_fingerprint, type_id, owner)
        if key not in textures:
            textures[key] = generate_piece_texture(game.controller.compiled.types_by_id[type_id], owner=owner, size=160).svg
            if len(textures) > 512:
                textures.pop(next(iter(textures)))
        return Response(textures[key], media_type="image/svg+xml")

    @app.websocket("/api/games/{game_id}/events")
    async def events(websocket: WebSocket, game_id: str):
        if not allowed_origin(websocket.headers.get("origin"), websocket.headers.get("host")):
            await websocket.close(code=1008)
            return
        try:
            game = service.get(game_id)
        except GameError:
            await websocket.close(code=1008)
            return
        await websocket.accept()
        queue = asyncio.Queue(maxsize=1)
        game.listeners.add(queue)
        async def push():
            await websocket.send_json(game.snapshot())
            while True:
                await queue.get()
                await websocket.send_json(game.snapshot())
        async def receive():
            while True:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_json({"type": "pong"})
        tasks = [asyncio.create_task(push()), asyncio.create_task(receive())]
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            game.listeners.discard(queue)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    dist = Path(dist_dir) if dist_dir is not None else ROOT / "web/dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
