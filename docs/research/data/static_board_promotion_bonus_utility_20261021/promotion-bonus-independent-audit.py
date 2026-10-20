from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
BASE=Path(__file__).resolve().parent
RUN=BASE/"promotion-bonus-run"
PLAN=json.loads((BASE/"promotion-bonus-plan.json").read_text(encoding="utf-8"))
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.serialization import ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value

def digest(value):
    packed=json.dumps(record_value(value),sort_keys=True,separators=(",",":"))
    return hashlib.sha256(packed.encode()).hexdigest().upper()

games=[json.loads(x) for x in (RUN/"games.jsonl").read_text(encoding="utf-8").splitlines() if x]
roots={r["root_id"]:r for r in json.loads((RUN/"roots.json").read_text(encoding="utf-8"))}
result=json.loads((RUN/"result.json").read_text(encoding="utf-8"))
assert result["status"]=="COMPLETE" and len(games)==PLAN["physical_games"]==64
assert result["invalid_actions"]==result["replay_mismatches"]==result["unstarted_slots"]==0
assert len({g["game_id"] for g in games})==64 and len(roots)==16
compiled_by_seed={}
setup=PLAN["rules"]["setup_schedule"]
symmetry=PLAN["rules"]["symmetry_schedule"]
for index,seed in enumerate(PLAN["rules"]["seeds"]):
    generated=generate_game(GeneratorConfig(
        seed=seed,board_size=PLAN["rules"]["board_size"],
        setup_preset=setup[index%len(setup)],
        movement_symmetry=symmetry[index%len(symmetry)],
        allow_hybrid=PLAN["rules"]["allow_hybrid"],
        require_promotable_type=PLAN["rules"]["require_promotable_type"],
        require_nonpromotable_type=PLAN["rules"]["require_nonpromotable_type"],
        max_generation_attempts=PLAN["rules"]["max_generation_attempts"],
        require_no_opening_win_in_one=PLAN["rules"]["require_no_opening_win_in_one"]))
    compiled=compile_legacy_ruleset_for_semantic_execution(generated.ruleset)
    assert ruleset_to_dict(generated.ruleset)==json.loads((RUN/f"rule-{seed}.json").read_text(encoding="utf-8")),f"RULE:{seed}"
    saved=json.loads((RUN/f"profile-{seed}.json").read_text(encoding="utf-8"))
    profile=build_ruleset_profile(compiled,EvaluationConfig())
    unit_hand={pt.type_id:(0 if pt.is_anchor else 900) for pt in compiled.piece_types}
    assert saved["candidate_board_values"]=={str(k):v for k,v in profile.board_value_by_type.items()},f"BOARD:{seed}"
    assert saved["unit_hand_values"]==unit_hand,f"HAND:{seed}"
    assert saved["promotion_gain_by_type"]=={str(k):v for k,v in profile.promotion_gain_by_type.items()},f"GAIN:{seed}"
    assert saved["weights_off"]["promotion_potential_weight"]==0 and saved["weights_on"]["promotion_potential_weight"]==3,f"WEIGHTS:{seed}"
    compiled_by_seed[seed]=compiled
assert len(compiled_by_seed)==8
for row in games:
    seed=int(row["root_id"].split("-")[0])
    record=deserialize_game_record(json.dumps(row["full_record"],sort_keys=True))
    session=GameSession.replay(compiled_by_seed[seed],record)
    final=digest({"state":session.state,"history":session.history,
                  "witnesses":session._search_witnesses,"result":session.result})
    assert final==row["final_state_sha256"],f"FINAL:{row['game_id']}"
    assert record.ruleset_fingerprint==compiled_by_seed[seed].ruleset_fingerprint
    assert session.result.status.value==row["terminal_status"]
    assert session.result.winner==row["winner"]
    assert tuple(item.action for item in session.history)==record.actions
    root=roots[row["root_id"]]
    assert root["seed"]==seed and row["root_state_sha256"]==root["root_state_sha256"]
    assert row["action_invalid_count"]==0 and row["full_history_replay_equal"]
    if row["reward"] is None:
        assert "UNKNOWN" in row["terminal_reason"] or row["terminal_status"]=="no_contest"
    else:
        assert row["terminal_reason"]=="ACTUAL_TERMINAL"
        expected=0 if session.result.winner is None else (1 if session.result.winner==row["candidate_owner"] else -1)
        assert row["reward"]==expected
assert len({(g["root_id"],g["candidate_owner"],g["variant"]) for g in games})==64
print(json.dumps({
 "independent_status":"PASS","regenerated_rules":len(compiled_by_seed),
 "profile_matches":len(compiled_by_seed),"full_histories_replayed":len(games),
 "distinct_roots":len(roots),"games":len(games),
 "invalid_actions":sum(g["action_invalid_count"] for g in games),
 "replay_mismatch_flags":sum(not g["full_history_replay_equal"] for g in games),
 "games_sha256":hashlib.sha256((RUN/"games.jsonl").read_bytes()).hexdigest().upper()
},sort_keys=True))