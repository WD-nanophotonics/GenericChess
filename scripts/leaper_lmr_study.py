"""Frozen bounded LMR feasibility: published reference, pilot, then paired games."""
import argparse
import hashlib
import json
import time
import traceback
from pathlib import Path
from contextlib import nullcontext
from collections import Counter
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from scripts.leaper_lmr_feasibility import LateQuietReduction
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.benchmark.runner import play_game, RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from datetime import datetime, timezone

def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

class BatchStop(RuntimeError): pass

def run(d):
    plan = L.load(d/'plan.json'); data = L.load(d/'inputs.json')
    assert not (d/'queries.jsonl').exists() and not (d/'receipt.json').exists()
    assert sha(d/'inputs.json') == plan['inputs_sha256']
    for p, expected in plan['source_sha256'].items(): assert sha(p) == expected, p
    tick = time.perf_counter(); start = stamp(); count = 0; games_done = 0
    cases = {x['key']: x for x in data['cases']}
    class Cancel:
        last = 0.; flag = False
        def is_cancelled(self):
            t = time.perf_counter()
            if t-self.last >= .25:
                self.last = t; self.flag = stopped() or t-tick >= plan['batch_seconds']
            return self.flag
    cancel = Cancel()
    def guard():
        if cancel.is_cancelled(): raise BatchStop('role/batch stop; remaining slots UNKNOWN, no refill')
    class Arm:
        def __init__(self, c, case, enabled, label):
            self.c = c; self.case = case; self.enabled = enabled; self.label = label
            self.player = AlphaBetaPlayer(c, use_disk_cache=False, tuning=SearchTuning(use_pvs=True))
            self.last_session = None
        def choose_action(self, s, limits):
            nonlocal count
            guard(); self.last_session = s
            before = L.record_value(s.to_record()); setup = time.perf_counter()
            policy = LateQuietReduction() if self.enabled else None
            begin = stamp(); qt = time.perf_counter(); cp = time.process_time()
            with policy if policy else nullcontext():
                decision = self.player.choose_action(s, limits, cancel_token=cancel)
            end = stamp()
            row = dict(id=count, label=self.label, case=self.case['key'], enabled=self.enabled,
                started_at=begin, ended_at=end, seconds=time.perf_counter()-qt,
                cpu_seconds=time.process_time()-cp, caller_seconds=time.perf_counter()-setup,
                before_record=before, limits=L.record_value(limits), decision=L.record_value(decision),
                tuning=L.record_value(SearchTuning(use_pvs=True)), profile=L.record_value(self.player.evaluation_profile),
                policy_counts=dict(policy.counts) if policy else {})
            append(d/'queries.jsonl', row); count += 1
            assert before == L.record_value(s.to_record()), 'complete session mutated'
            check = replay(self.c, before)
            for a in decision.principal_variation:
                assert a in check.legal_actions(); check.submit(a)
            assert decision.action in s.legal_actions() or decision.choice_kind == 'DECLARATION'
            if count % 32 == 0: print('LMR-QUERIES', count, self.label, flush=True)
            return decision
    status = 'FAILED'; phase = 'reference'; current_game = None; arms = []
    try:
        # Only known WIN strategy is independently qualified; other WDL labels
        # remain explicitly attributed to the published complete graph.
        w = data['reference']; c = L.compile_rule(L.ruleset_from_dict(w['rules']))
        root = L.GameSession(c)
        def verify(paths, s):
            if s.result.status.value != 'ongoing':
                assert all(not p for p in paths) and s.result.winner == w['winner']
                return 1
            assert all(p for p in paths)
            groups = {}
            # The published paths use GameRecord action serialization.
            for p in paths:
                groups.setdefault(json.dumps(p[0],sort_keys=True), []).append(p[1:])
            parsed = {}
            for raw, tails in groups.items():
                rs = json.loads(raw)
                match = [a for a in s.legal_actions()
                    if a.from_square.file==rs['from'][0] and a.from_square.rank==rs['from'][1]
                    and a.to_square.file==rs['to'][0] and a.to_square.rank==rs['to'][1]
                    and a.promotion_target_id==rs['promotion_target_id']]
                assert len(match)==1; parsed[match[0]]=tails
            if s.state.position.side_to_move != w['winner']:
                assert set(parsed)==set(s.legal_actions()), 'missing defense'
            else:
                assert len(parsed)==1, 'not one fixed winning strategy'
            total = 1
            for a,tails in parsed.items():
                child = replay(c, L.record_value(s.to_record())); child.submit(a)
                total += verify(tails, child)
            return total
        proof_nodes = verify(w['proof_paths'], root)
        write_json(d/'reference-proof.json', dict(nodes=proof_nodes, winner=w['winner'],
            rule_fingerprint=root.state.position.ruleset_fingerprint, full_record=L.record_value(root.to_record()),
            scope='Actual-Core full-history all-defense WIN strategy only; DRAW labels remain source-attributed.'))
        case = dict(key='published-horizontal-root137')
        for depth in plan['reference_depths']:
            for enabled in (False, True):
                Arm(c,case,enabled,'reference-D'+str(depth)).choose_action(root,
                    SearchLimits(max_depth=depth,max_nodes=30000,max_time_seconds=3))
        phase = 'pilot'; reductions = 0
        for key in plan['pilot_cases']:
            case = cases[key]; c = L.compile_rule(L.ruleset_from_dict(case['rule'])); s=replay(c,case['record'])
            for enabled in (False, True):
                before_count=count
                arm=Arm(c,case,enabled,'pilot'); arm.choose_action(s,SearchLimits(max_depth=6,max_nodes=100000,max_time_seconds=5))
                row=json.loads((d/'queries.jsonl').read_text(encoding='utf-8').splitlines()[-1])
                reductions += row['policy_counts'].get('reduced_calls',0)
        write_json(d/'pilot-gate.json',dict(reductions=reductions,passed=reductions>0,
            decision='run fixed paired games' if reductions else 'stop: policy inactive; no cost/game claim'))
        if not reductions:
            status='CLOSED_INACTIVE'; return
        phase='games'
        for i,key in enumerate(plan['game_cases']):
            case=cases[key]; c=L.compile_rule(L.ruleset_from_dict(case['rule'])); initial=replay(c,case['record'])
            for color in ((0,1) if i%2==0 else (1,0)):
                guard(); current_game=f'{key}-lmr{color}'
                candidate=Arm(c,case,True,current_game);control=Arm(c,case,False,current_game);arms=[candidate,control]
                game_start=stamp();gt=time.perf_counter()
                outcome,events=play_game(c,initial.to_record().actions,key,current_game,color,candidate,control,
                    RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=plan['game_seconds'],nodes=None,max_plies=96))
                final=candidate.last_session or control.last_session or initial
                append(d/'games.jsonl',dict(game=current_game,case=key,candidate_color=color,
                    started_at=game_start,ended_at=stamp(),seconds=time.perf_counter()-gt,
                    outcome=L.record_value(outcome),eligible=outcome.eligible,events=L.record_value(events),
                    initial_record=L.record_value(initial.to_record()),final_record=L.record_value(final.to_record()),
                    final_result=L.record_value(final.result)))
                games_done+=1;print('LMR-GAME',games_done,current_game,outcome.result,outcome.plies,outcome.eligible,flush=True)
                current_game=None
        status='CLOSED'
    except BatchStop:
        status='STOPPED_UNKNOWN'
        if current_game:
            final=next((a.last_session for a in arms if a.last_session is not None),None)
            write_json(d/'partial-game.json',dict(game=current_game,at=stamp(),
                final_record=L.record_value(final.to_record()) if final else None,reason='batch/role cap; not a draw'))
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),phase=phase,queries=count,traceback=traceback.format_exc()))
        raise
    finally:
        write_json(d/'receipt.json',dict(status=status,phase=phase,started_at=start,ended_at=stamp(),
            seconds=time.perf_counter()-tick,queries=count,games=games_done,plan_sha256=sha(d/'plan.json')))

if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);run(p.parse_args().directory)
