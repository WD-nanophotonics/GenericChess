from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
BASE=Path(__file__).resolve().parent
RUN=BASE/"staged-capture-order-run-20261021"
PLAN=json.loads((BASE/"staged-capture-order-plan.json").read_text(encoding="utf-8"))
PREFLIGHT=json.loads((BASE/"staged-capture-order-preflight.json").read_text(encoding="utf-8"))
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.position import GameState
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

def digest(value):
    packed=json.dumps(record_value(value),sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(packed).hexdigest()

games=[json.loads(line) for line in (RUN/"capture-order-games.jsonl").read_text(encoding="utf-8").splitlines() if line]
roots={r["root_id"]:r for r in json.loads((RUN/"roots.json").read_text(encoding="utf-8"))}
assert len(games)==64 and len(roots)==16
assert len({g["game_id"] for g in games})==64
regenerated={}
setup_schedule=PLAN["rules"]["setup_schedule"]
symmetry_schedule=PLAN["rules"]["symmetry_schedule"]
for index,seed in enumerate(PLAN["rules"]["seeds"]):
    generated=generate_game(GeneratorConfig(
        seed=seed, board_size=PLAN["rules"]["board_size"],
        setup_preset=setup_schedule[index%len(setup_schedule)],
        movement_symmetry=symmetry_schedule[index%len(symmetry_schedule)],
        allow_hybrid=PLAN["rules"]["allow_hybrid"],
        require_promotable_type=PLAN["rules"]["require_promotable_type"],
        require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],
        max_generation_attempts=PLAN["rules"]["max_generation_attempts"],
        require_no_opening_win_in_one=False))
    compiled=compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
    saved=json.loads((RUN/f"rule-{seed}.json").read_text(encoding="utf-8"))
    assert ruleset_to_dict(generated.ruleset)==saved, f"RULE_REGEN:{seed}"
    profile=build_ruleset_profile(compiled,EvaluationConfig())
    saved_profile=json.loads((RUN/f"profile-{seed}.json").read_text(encoding="utf-8"))
    assert saved_profile["fingerprint"]==compiled.ruleset_fingerprint
    assert saved_profile["board"]=={str(k):v for k,v in profile.board_value_by_type.items()}
    assert saved_profile["hand"]=={str(k):v for k,v in profile.hand_value_by_base_type.items()}
    regenerated[seed]=compiled
assert len(regenerated)==8
replayed=0
for g in games:
    seed=int(g["root_id"].split("-")[0])
    record=deserialize_game_record(json.dumps(g["full_record"],sort_keys=True))
    session=GameSession.replay(regenerated[seed],record)
    assert digest(session.state)==g["final_state_sha256"], f"FINAL_STATE:{g['game_id']}"
    assert session.result.status.value==g["terminal_status"], f"STATUS:{g['game_id']}"
    assert session.result.winner==g["winner"], f"WINNER:{g['game_id']}"
    assert tuple(item.action for item in session.history)==record.actions, f"HISTORY:{g['game_id']}"
    assert len(record.actions)==len(g["opening_actions"])+g["move_count"]
    root=roots[g["root_id"]]
    assert root["seed"]==seed
    assert g["root_state_sha256"]==root["root_sha256"], f"ROOT_DIGEST:{g['game_id']}"
    if g["reward"] is None:
        assert g["terminal_reason"]!="ACTUAL_TERMINAL" or g["terminal_status"]=="no_contest"
    else:
        assert g["terminal_reason"]=="ACTUAL_TERMINAL"
        expected=0 if session.result.winner is None else (1 if session.result.winner==g["candidate_owner"] else -1)
        assert g["reward"]==expected
    replayed+=1
assert all(g["action_invalid_count"]==0 and g["full_history_replay_equal"] for g in games)
assert PREFLIGHT["outcomes_collected"]==0 and len(PREFLIGHT["roots"])==16
print(json.dumps({
  "independent_status":"PASS","regenerated_rules":len(regenerated),
  "profile_matches":len(regenerated),"replayed_full_histories":replayed,
  "distinct_roots":len(roots),"games":len(games),"invalid_actions":sum(g["action_invalid_count"] for g in games),
  "producer_replay_mismatch_flags":sum(not g["full_history_replay_equal"] for g in games),
  "game_jsonl_sha256":hashlib.sha256((RUN/"capture-order-games.jsonl").read_bytes()).hexdigest()
},sort_keys=True))
