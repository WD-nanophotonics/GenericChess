"""Feasibility probe: generation, compilation, profile build and one search."""
from pathlib import Path
import sys, json, time, random, hashlib
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.learning.material import LearnableMaterialCheckpoint
from tools.local_agent.common import write_json

D = ROOT / '.local_agent/asymmetric-static-20261018'
out = []
t0 = time.perf_counter()
for seed in (281001, 281002, 281003, 281004, 281005, 281006):
    st = time.perf_counter()
    row = {'seed': seed}
    try:
        game = generate_game(GeneratorConfig(seed=seed, board_size=5,
                                             setup_preset='free_random',
                                             movement_symmetry='none'))
        ruleset = game.ruleset
        d = ruleset_to_dict(ruleset)
        roundtrip = ruleset_from_dict(json.loads(json.dumps(d)))
        assert ruleset_to_dict(roundtrip) == d
        compiled = compile_legacy_ruleset_for_semantic_execution(ruleset)
        native = compile_native_semantic_rules(compiled)
        profile = build_ruleset_profile(compiled, EvaluationConfig())
        types = list(compiled.types_by_id)
        row.update(ok=True, gen_seconds=time.perf_counter() - st,
                   types=types,
                   opening_moves=game.generation_report.opening_legal_move_count,
                   board_values=dict(profile.board_value_by_type),
                   hand_values=dict(profile.hand_value_by_base_type),
                   drop_types=sorted(compiled.drop_allowed),
                   fingerprint=compiled.ruleset_fingerprint)
        # one 4-ply random prefix then a single D2 search per side
        s = GameSession(compiled)
        rng = random.Random(seed * 1000000)
        for _ in range(4):
            if s.result.status.value != 'ongoing':
                break
            aa = sorted(s.legal_actions(), key=repr)
            s.submit(aa[rng.randrange(len(aa))])
        row['prefix_terminal'] = s.result.status.value != 'ongoing'
        row['prefix_ply'] = s.state.ply_count
        if not row['prefix_terminal']:
            board = {t: 0. for t in types}
            hand = dict(board)
            for t in types:
                if t != 'K':
                    board[t] = profile.board_value_by_type.get(t, 0) / 1000
                    hand[t] = profile.hand_value_by_base_type.get(t, 0) / 1000
            cp = LearnableMaterialCheckpoint(ruleset_fingerprint=compiled.ruleset_fingerprint,
                                             evaluation_profile_version='probe',
                                             board_weights=board, hand_weights=hand,
                                             material_scale=256, value_scale=10.,
                                             reference_median=1.)
            eng = SemanticSearchEngine(compiled, native, checkpoint=cp, tt_megabytes=0)
            side = s.state.position.side_to_move
            r = eng.search(s, SearchLimits(max_depth=2, max_nodes=8192,
                                           max_time_seconds=2., quiescence_max_depth=0),
                           root_window_pruning=False)
            row['search'] = dict(completed_depth=r.completed_depth, nodes=r.nodes,
                                 action=None if r.action is None else repr(r.action),
                                 score=r.score, termination=r.termination_reason)
    except Exception as exc:
        row.update(ok=False, error=repr(exc))
    row['seconds'] = time.perf_counter() - st
    out.append(row)
    print(json.dumps(row, default=str)[:600], flush=True)
write_json(D / 'probe.json', dict(rows=out, seconds=time.perf_counter() - t0,
                                  scope='feasibility only; no outcomes stored'))
