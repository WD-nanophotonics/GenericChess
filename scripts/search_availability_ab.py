"""One existing readonly availability flag; current exact-map code in both arms."""
from pathlib import Path
import argparse
import json
import time
import hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import gate, stamp
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def run(directory):
    plan = json.loads((directory / 'plan.json').read_text())
    registration = json.loads((directory / 'availability-plan.json').read_text())
    cases = json.loads((directory / 'inputs.json').read_text())['cases']
    output = directory / 'availability.jsonl'
    if output.exists():
        raise ValueError('fresh experiment only; retain old results')
    started = stamp()
    tick = time.perf_counter()
    cpu = time.process_time()
    queries = 0
    for key in registration['cases']:
        case = next(x for x in cases if x['key'] == key)
        compiled = L.compile_rule(L.ruleset_from_dict(case['rule']))
        session = replay(compiled, case['record'])
        players = {enabled: AlphaBetaPlayer(compiled, use_disk_cache=False, use_native_semantic_availability=enabled) for enabled in (False, True)}
        assert all(p.native_legality_provider is not None for p in players.values())
        for rep in range(4):
            for mode in ('nodes', 'wall'):
                pair = []
                order = (False, True) if rep in (0, 3) else (True, False)
                for enabled in order:
                    gate(plan)
                    if stopped():
                        raise RuntimeError('PRIMARY user stop persists')
                    player = players[enabled]
                    player.reset()
                    provider = player.native_legality_provider
                    before_metrics = provider.availability_metrics
                    limits = SearchLimits(max_depth=64, max_nodes=65536 if mode == 'nodes' else None, max_time_seconds=60 if mode == 'nodes' else 8)
                    before = L.record_value(session.to_record())
                    start = stamp()
                    t = time.perf_counter()
                    cp = time.process_time()
                    decision = player.choose_action(session, limits)
                    wall = time.perf_counter() - t
                    cost = time.process_time() - cp
                    after_metrics = provider.availability_metrics
                    delta = {name: value - before_metrics.get(name, 0) for name, value in after_metrics.items()}
                    row = dict(case=key, input_sha256=case['input_sha256'], rep=rep, mode=mode, availability_enabled=enabled, order=list(order), started_at=start, ended_at=stamp(), wall_seconds=wall, cpu_seconds=cost, limits=L.record_value(limits), availability_delta=delta, decision=L.record_value(decision))
                    assert before == L.record_value(session.to_record())
                    assert decision.action in session.legal_actions()
                    if enabled:
                        assert delta.get('queries', 0) > 0
                    else:
                        assert delta == {}
                    pair.append(row)
                    with output.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(row) + '\n')
                    queries += 1
                    print(key, rep, mode, enabled, decision.completed_depth, decision.nodes + decision.qnodes, round(wall, 3), delta.get('queries', 0), flush=True)
                a, b = [x['decision'] for x in pair]
                if mode == 'nodes' and all(x['termination_reason'] != 'time_limit' for x in (a, b)):
                    fields = ('score', 'completed_depth', 'nodes', 'qnodes', 'principal_variation', 'tt_hits', 'tt_cutoffs', 'runtime_pushes', 'runtime_pops')
                    assert tuple(a[x] for x in fields) == tuple(b[x] for x in fields), 'availability changed actual tree/value'
    write_json(directory / 'availability-receipt.json', dict(started_at=started, ended_at=stamp(), wall_seconds=time.perf_counter() - tick, cpu_seconds=time.process_time() - cpu, queries=queries, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    run(args.directory)
