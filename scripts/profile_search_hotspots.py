"""Instrument current Q4 hotspots separately; no timing/strength comparison claim."""
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import argparse
import cProfile
import pstats
import time
import json
import hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import gate, stamp
from scripts.search_snapshot_ab import legacy_items
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.core.search_runtime import RuntimeCountsSnapshot
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.audit_instrumentation import TimingAuditRecorder
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped

def run(directory):
    plan = json.loads((directory / 'plan.json').read_text())
    cases = json.loads((directory / 'inputs.json').read_text())['cases']
    cases += json.loads((directory / 'transfer-inputs.json').read_text())['cases']
    rows = []
    started = stamp()
    tick = time.perf_counter()
    cpu = time.process_time()
    current = RuntimeCountsSnapshot.items
    for key in ('promo6_0', 'classic6_ply16', 'classic8_ply24'):
        case = next(x for x in cases if x['key'] == key)
        compiler = compile_ruleset if case.get('execution_api') == 'compile_ruleset' else L.compile_rule
        compiled = compiler(L.ruleset_from_dict(case['rule']))
        session = replay(compiled, case['record'])
        for arm in ('old', 'new'):
            gate(plan)
            if stopped():
                raise RuntimeError('PRIMARY stop persists')
            player = AlphaBetaPlayer(compiled, use_disk_cache=False)
            recorder = TimingAuditRecorder()
            profiler = cProfile.Profile()
            limits = SearchLimits(max_depth=64, max_nodes=8192, max_time_seconds=60)
            with patch.object(RuntimeCountsSnapshot, 'items', legacy_items if arm == 'old' else current):
                profiler.enable()
                decision = player.choose_action(session, limits, recorder=recorder)
                profiler.disable()
            stats = pstats.Stats(profiler)
            # Keep exact private paths; publication will have an explicit sanitized copy.
            top = sorted(((f[0], f[1], f[2], v[0], v[1], v[2], v[3]) for f, v in stats.stats.items()), key=lambda x: x[-1], reverse=True)[:50]
            rows.append(dict(case=key, arm=arm, input_sha256=case['input_sha256'], decision=L.record_value(decision), timing=recorder.snapshot(), top_cumulative=top))
            write_json(directory / 'q4-hotspots.json', dict(rows=rows, status='PARTIAL', note='cProfile+recorder overhead; do not compare these seconds to uninstrumented speed.'))
            print(key, arm, decision.completed_depth, decision.nodes, decision.qnodes, decision.elapsed_seconds, flush=True)
    write_json(directory / 'q4-hotspots.json', dict(rows=rows, status='PASS', note='Separate instrumented samples, nested cumulative times not additive; no strength or speed estimate from instrumented durations.'))
    write_json(directory / 'q4-hotspots-receipt.json', dict(started_at=started, ended_at=stamp(), wall_seconds=time.perf_counter() - tick, cpu_seconds=time.process_time() - cpu, queries=len(rows), source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    run(args.directory)
