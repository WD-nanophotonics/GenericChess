"""Typed browser contracts; all actions still come from the real controller."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

class GameConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["generated", "hybrid", "western_chess", "standard_shogi"] = "generated"
    seed: int = Field(default=42, ge=0, le=2147483647)
    board_size: int = Field(default=8, ge=4, le=12)
    preset: Literal["classic_like", "bilateral_random", "free_random"] = "classic_like"
    mode: Literal["pve", "pvp"] = "pve"
    human: Literal[0, 1] = 0
    think_seconds: Literal[0.5, 1.0, 3.0] = 1.0

class CreateGame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: GameConfig = Field(default_factory=GameConfig)
    previous_id: str | None = None

class Operation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    request_id: str = Field(min_length=1, max_length=80)
    kind: Literal["action", "undo", "restart", "resign", "history", "live", "pause_ai", "resume_ai", "resume", "suspend", "import"]
    action_id: str | None = None
    ply: int | None = Field(default=None, ge=0)
    format: Literal["record", "rules", "bundle"] | None = None
    content: Any = None
