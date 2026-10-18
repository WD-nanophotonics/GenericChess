"""Bounded served-candidate comparison: rule-only static vs uniform material on
newly generated free_random / asymmetric-movement rules.

No fit, no learner, no AUX checkpoint or AUX-side state. All rules, roots and
weight vectors are written and hashed before any game outcome is produced.
"""
from pathlib import Path
import sys, json, time, random, hashlib, traceback, subprocess

ROOT = Path.cwd()
D = ROOT / '.local_agent/asymmetric-static-20261018'
START = time.monotonic()
sys.path.insert(0, str(ROOT))
from tools.local_agent.common import write_json
from scripts.research_record import record_value
from generic_chess.generation.generator import generate_game
from generic_chess.generation.config import GeneratorConfig, GenerationError
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record, deserialize_game_record
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.learning.material import LearnableMaterialCheckpoint

PLAN = json.loads((D / 'plan.json').read_bytes())
assert not (D / 'producer-source.json').exists(), 'rules/weights must be frozen only once'
assert not (D / 'games.jsonl').exists(), 'refuse to overwrite closed outcomes'
assert not (D / 'rules.json').exists(), 'rules were already frozen'


def digest(value):
    return hashlib.sha256(json.dumps(record_value(value), sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def poll():
    if time.monotonic() - START >= PLAN['limits']['global_cap_seconds']:
        raise TimeoutError('FROZEN_GLOBAL_CAP')
    for name in ('rollout', 'advisor', 'slack'):
        f = json.loads((ROOT / '.local_agent' / (name + '.json')).read_bytes())
        if f.get('stopped') or f.get('user_paused'):
            raise InterruptedError('EXPLICIT_STOP')


def assess(session, owner):
    if session.result.status.value == 'ongoing':
        return None
    return 0 if session.result.winner is None else (1 if session.result.winner == owner else -1)


# ---- freeze rules -----------------------------------------------------------
compiled, native, rule_dicts, generated = {}, {}, {}, []
used, failures = [], []
seeds = PLAN['rules']['seeds'] + PLAN['rules']['fallback_seeds']
for seed in seeds:
    if len(used) == len(PLAN['rules']['seeds']):
        break
    cfg = GeneratorConfig(seed=seed, **PLAN['rules']['config'])
    try:
        game = generate_game(cfg)
    except GenerationError as exc:
        failures.append(dict(seed=seed, error=repr(exc)))
        continue
    rule = game.ruleset
    d = ruleset_to_dict(rule)
    assert ruleset_to_dict(ruleset_from_dict(json.loads(json.dumps(d)))) == d
    c = compile_legacy_ruleset_for_semantic_execution(rule)
    compiled[seed] = c
    native[seed] = compile_native_semantic_rules(c)
    rule_dicts[seed] = d
    used.append(seed)
    generated.append(dict(seed=seed,
                          opening_legal_moves=game.generation_report.opening_legal_move_count,
                          types=list(c.types_by_id),
                          fingerprint=c.ruleset_fingerprint))
(D / 'rules.json').write_text(json.dumps(dict(
    rules={str(k): v for k, v in rule_dicts.items()},
    sha256={str(k): hashlib.sha256(json.dumps(v, sort_keys=True,
                                             separators=(',', ':')).encode()).hexdigest()
            for k, v in rule_dicts.items()},
    generated=generated, failures=failures,
    config=PLAN['rules']['config'], used_seeds=used,
    scope='Frozen before any game outcome; generation deterministic from seed+config.'),
    sort_keys=True, indent=1))
RULES = [g['seed'] for g in generated]


# ---- freeze weights ---------------------------------------------------------
def build_weights(c, values, label):
    board = {t: 0. for t in c.types_by_id}
    hand = dict(board)
    for kind, t, w in values:
        (board if kind == 'board' else hand)[t] = w
    return LearnableMaterialCheckpoint(
        ruleset_fingerprint=c.ruleset_fingerprint,
        evaluation_profile_version=label,
        board_weights=board, hand_weights=hand,
        material_scale=256, value_scale=10., reference_median=1.)


models, channels_by_rule = {}, {}
for gs in RULES:
    c = compiled[gs]
    ordinary = sorted(t for t in c.types_by_id if t != 'K')
    channels = [('board', t) for t in ordinary] + [('hand', t) for t in ordinary]
    channels_by_rule[gs] = channels
    profile = build_ruleset_profile(c, EvaluationConfig())
    static_vals = [(k, t, (profile.board_value_by_type if k == 'board'
                           else profile.hand_value_by_base_type)[t] / 1000)
                   for k, t in channels]
    unit_vals = [(k, t, 1.0) for k, t in channels]
    rng = random.Random(99031)
    fixed_vals = [(channels[0][0], channels[0][1], 1.0)]
    fixed_vals += [(k, t, rng.uniform(0.5, 1.5)) for k, t in channels[1:]]
    models[gs, 'unit'] = build_weights(c, unit_vals, 'unfitted-uniform-control')
    models[gs, 'rule_static_v2'] = build_weights(c, static_vals, 'existing-rule-only-generic-v2-material-control')
    models[gs, 'foe_uniform'] = build_weights(c, unit_vals, 'fixed-uniform-foe')
    models[gs, 'foe_fixed_random'] = build_weights(c, fixed_vals, 'frozen-deterministic-random-foe')
write_json(D / 'models.json', dict(rows=[
    dict(rule=gs, label=label, checkpoint_id=cp.checkpoint_id, checkpoint=cp.to_dict())
    for (gs, label), cp in models.items()],
    channels={str(k): [list(x) for x in v] for k, v in channels_by_rule.items()},
    scope='unit/static/fixed foe vectors frozen before outcomes; 256 scale, no fit/default change.'))


# ---- deterministic fitness-blind prefixes -----------------------------------
roots, attempts = {}, []
for gs in RULES:
    c = compiled[gs]
    kept = 0
    for index in range(PLAN['families']['attempts_per_rule']):
        if kept >= PLAN['families']['selected_per_rule']:
            break
        poll()
        s = GameSession(c)
        rng = random.Random(gs * 1000000 + index)
        for _ in range(PLAN['families']['prefix_plies']):
            if s.result.status.value != 'ongoing':
                break
            aa = sorted(s.legal_actions(), key=repr)
            assert aa
            s.submit(aa[rng.randrange(len(aa))])
        terminal = s.result.status.value != 'ongoing'
        attempts.append(dict(rule=gs, prefix_index=index, kept=not terminal,
                             prefix_completed=s.state.ply_count, terminal=terminal,
                             legal_root_actions=(0 if terminal else len(s.legal_actions()))))
        if terminal:
            continue
        roots[gs, index] = dict(rule=gs, family=index,
                                record=json.loads(serialize_game_record(s.to_record())),
                                state_sha256=digest(s.state),
                                witnesses_sha256=digest(s._search_witnesses),
                                prefix_completed=s.state.ply_count,
                                legal_root_actions=len(s.legal_actions()))
        kept += 1
write_json(D / 'roots.json', dict(rows=list(roots.values()), attempts=attempts,
                                  families_per_rule={str(gs): sum(1 for (g, _) in roots if g == gs)
                                                     for gs in RULES},
                                  scope='Fitness-blind prefix selection, first 32 non-terminal of 64 deterministic seeds.'))
FAMILIES = {gs: sorted(f for (g, f) in roots if g == gs) for gs in RULES}


# ---- slots ------------------------------------------------------------------
slots = []
for gs in RULES:
    for family in FAMILIES[gs]:
        for label in PLAN['profiles']:
            for foe in PLAN['foes']:
                owners = (0,) if (label == 'unit' and foe == 'uniform') else (0, 1)
                for owner in owners:
                    slots.append((gs, family, label, owner, foe))
random.Random(20261018).shuffle(slots)
write_json(D / 'slots.json', dict(slots=slots, physical=len(slots)))

write_json(D / 'producer-source.json', dict(
    producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    plan_sha256=hashlib.sha256((D / 'plan.json').read_bytes()).hexdigest(),
    rules_sha256=hashlib.sha256((D / 'rules.json').read_bytes()).hexdigest(),
    models_sha256=hashlib.sha256((D / 'models.json').read_bytes()).hexdigest(),
    roots_sha256=hashlib.sha256((D / 'roots.json').read_bytes()).hexdigest(),
    git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
    scope='New generated asymmetric/free rules; no fit, learner, AUX checkpoint, AUX state or default change.'))

# ---- games ------------------------------------------------------------------
STATUS, REASON, CURRENT = 'COMPLETE', None, None
queries = nodes = 0
games = []
try:
    with (D / 'queries.jsonl').open('x', encoding='utf8') as qlog, \
         (D / 'games.jsonl').open('x', encoding='utf8') as glog:
        for slot, (gs, family, label, owner, foe) in enumerate(slots):
            poll()
            c, n = compiled[gs], native[gs]
            root = roots[gs, family]
            s = GameSession.replay(c, deserialize_game_record(json.dumps(root['record'])))
            assert digest(s.state) == root['state_sha256']
            assert digest(s._search_witnesses) == root['witnesses_sha256']
            candidate = models[gs, label]
            unit = models[gs, 'foe_uniform' if foe == 'uniform' else 'foe_fixed_random']
            engines = {owner: SemanticSearchEngine(c, n, checkpoint=candidate, tt_megabytes=0),
                       1 - owner: SemanticSearchEngine(c, n, checkpoint=unit, tt_megabytes=0)}
            ending = 'HORIZON_UNKNOWN'
            localnodes = localqueries = 0
            CURRENT = dict(slot=slot, rule=gs, family=family, label=label,
                           candidate_owner=owner, foe=foe,
                           checkpoint_id=candidate.checkpoint_id,
                           root_state_sha256=root['state_sha256'])
            try:
                for relative_ply in range(PLAN['horizon_after_prefix']):
                    poll()
                    if s.result.status.value != 'ongoing':
                        ending = 'ACTUAL_TERMINAL'
                        break
                    remaining = PLAN['limits']['global_cap_seconds'] - (time.monotonic() - START)
                    if remaining < 2.:
                        raise TimeoutError('FROZEN_GLOBAL_CAP_BEFORE_FULL_QUERY')
                    before = (s.state, s.to_record(), s.history, s._search_witnesses)
                    beforehash = digest(s.state)
                    side = s.state.position.side_to_move
                    stamp = time.perf_counter()
                    r = engines[side].search(
                        s, SearchLimits(max_depth=PLAN['search']['depth'],
                                        max_nodes=PLAN['search']['nodes_per_query'],
                                        max_time_seconds=PLAN['search']['seconds_per_query'],
                                        quiescence_max_depth=0),
                        root_window_pruning=False)
                    elapsed = time.perf_counter() - stamp
                    assert before == (s.state, s.to_record(), s.history, s._search_witnesses)
                    localqueries += 1
                    localnodes += r.nodes
                    queries += 1
                    nodes += r.nodes
                    if r.completed_depth < PLAN['search']['depth']:
                        ending = 'SEARCH_LIMIT_UNKNOWN'
                    elif r.declaration_id is not None:
                        s.declare(r.declaration_id)
                    elif r.action is None:
                        ending = 'NO_ACTION_UNKNOWN'
                    else:
                        assert r.action in s.legal_actions()
                        s.submit(r.action)
                    qlog.write(json.dumps(dict(
                        slot=slot, relative_ply=relative_ply, actor=side,
                        checkpoint_id=(candidate if side == owner else unit).checkpoint_id,
                        before_sha256=beforehash, after_sha256=digest(s.state),
                        returned_action=record_value(r.action), declaration_id=r.declaration_id,
                        requested_depth=PLAN['search']['depth'],
                        requested_nodes=PLAN['search']['nodes_per_query'],
                        requested_seconds=PLAN['search']['seconds_per_query'],
                        completed_depth=r.completed_depth, selective_depth=r.selective_depth,
                        nodes=r.nodes, qnodes=r.qnodes, used_fallback=r.used_fallback,
                        cause=r.termination_reason, score=r.score,
                        kernel_seconds=r.elapsed_seconds, caller_seconds=elapsed),
                        separators=(',', ':')) + '\n')
                    qlog.flush()
                    if ending in ('SEARCH_LIMIT_UNKNOWN', 'NO_ACTION_UNKNOWN'):
                        break
                if s.result.status.value != 'ongoing':
                    ending = 'ACTUAL_TERMINAL'
            except (TimeoutError, InterruptedError) as exc:
                ending = 'INTERRUPTED_UNKNOWN'
                REASON = repr(exc)
                STATUS = 'INTERRUPTED'
            fresh = GameSession.replay(c, s.to_record())
            assert (fresh.state, fresh.history, fresh._search_witnesses, fresh.result) == \
                   (s.state, s.history, s._search_witnesses, s.result)
            CURRENT.update(ending=ending, result=record_value(s.result),
                           reward=assess(s, owner),
                           record=json.loads(serialize_game_record(s.to_record())),
                           final_state_sha256=digest(s.state),
                           final_witnesses_sha256=digest(s._search_witnesses),
                           nodes=localnodes, queries=localqueries,
                           relative_plies=s.state.ply_count - root['prefix_completed'],
                           full_replay_equal=True)
            games.append(CURRENT)
            glog.write(json.dumps(CURRENT, separators=(',', ':')) + '\n')
            glog.flush()
            CURRENT = None
            if len(games) % 64 == 0:
                print('CLOSED_GAMES', len(games), 'queries', queries,
                      'seconds', round(time.monotonic() - START, 3), flush=True)
            if qlog.tell() + glog.tell() > PLAN['limits']['max_output_bytes']:
                STATUS, REASON = 'INTERRUPTED', 'FROZEN_OUTPUT_CAP'
                break
            if STATUS != 'COMPLETE':
                break
except Exception as exc:
    STATUS, REASON = 'ERROR', repr(exc)
    traceback.print_exc()

result = dict(status=STATUS, reason=REASON, planned_physical=len(slots),
              returned_physical=len(games), unstarted_physical=len(slots) - len(games),
              queries=queries, nodes=nodes, seconds=time.monotonic() - START,
              current_unclosed_slot=CURRENT,
              terminal=sum(g['ending'] == 'ACTUAL_TERMINAL' for g in games),
              unknown=sum(g['reward'] is None for g in games),
              rules=RULES, families={str(k): v for k, v in FAMILIES.items()},
              generation_failures=failures,
              scope='Six new free_random/asymmetric rules; served-candidate diagnostic, '
                    'no fit/learner/AUX inputs/defaults; UNKNOWN retained, caps not extended.')
write_json(D / 'result.json', result)
print('CLOSED', json.dumps(result), flush=True)
