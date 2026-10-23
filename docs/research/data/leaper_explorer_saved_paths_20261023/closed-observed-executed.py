from pathlib import Path
from collections import Counter,defaultdict,deque
from scripts.leaper_saved_child_bounds import current_truth,propagate
from scripts.leaper_saved_suffix_transfer import apply as suffix_apply
from scripts.leaper_observed_path_proofs import apply as observed_apply
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_cooperative_truth import admit
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested
from scripts.research_record import record_value
from generic_chess.core.actions import action_from_dict
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
import json,time

p=Path('artifacts/saved-child-bounds-d19a')
t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
u,_=propagate(t,load(p/'edges.json.gz'));v=suffix_apply(u,load(p/'shortened-proofs.json.gz'));w=observed_apply(v,load(p/'observed-proofs.json.gz'))
roots={r['id']:r for r in w['roots']};compiled={fp:compile_rule(ruleset_from_dict(raw))for fp,raw in w['rules'].items()}
for fp,c in compiled.items():
    admit(ruleset_from_dict(w['rules'][fp]),c)
    assert c.support.stalemate_result=='draw'and not c.declarations and not c.ir.triggers and not c.ir.aux_slots
start=time.perf_counter();last=0.;legal={};edges=defaultdict(dict);goals=set();vertices=set();positions={};stats=Counter()
for rid,record in w['records'].items():
    c=compiled[record['ruleset_fingerprint']]
    s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
    for action in record['actions']:
        now=time.perf_counter()
        if now-start>=180:raise RuntimeError('CLOSED_FEASIBILITY_CAP_UNKNOWN')
        if now-last>=.2:
            last=now
            if role_stop_requested():raise RuntimeError('USER_STOP')
        hid=state_sha(s.state);pos=s.state.position;r=roots[hid]
        expected={digest(a['action'])for a in r['action_bounds']}
        assert expected
        if pos in legal:assert legal[pos]==expected
        else:legal[pos]=expected
        positions[hid]=pos;vertices.add(pos)
        s.submit(action_from_dict(action));child=s.state.position;vertices.add(child)
        ah=digest(action)
        if ah in edges[pos]:assert edges[pos][ah]==child
        edges[pos][ah]=child
        if s.state.terminal_status.winner is not None:goals.add(child)
        elif s.state.terminal_status.status.value=='stalemate':
            if child in legal:assert not legal[child]
            legal[child]=set()
        stats['recorded_actions']+=1
    stats['records']+=1
parents=defaultdict(set)
for pos,cs in edges.items():
    if pos in legal:assert set(cs)<=legal[pos]
    for ch in cs.values():parents[ch].add(pos)
bad={p for p in vertices if p in goals or p not in legal or set(edges[p])!=legal[p]}
initial_open=len(bad);queue=deque(bad)
while queue:
    ch=queue.popleft()
    for parent in parents[ch]:
        if parent not in bad:bad.add(parent);queue.append(parent)
closed=vertices-bad
assert not closed&goals and all(set(edges[p])==legal[p]and all(ch in closed for ch in edges[p].values())for p in closed)
affected=[r['id']for r in w['roots']if positions[r['id']]in closed and r['cooperative_decisive']is None]
known=Counter(str(r['cooperative_decisive'])for r in w['roots']if positions[r['id']]in closed)
assert not known['True']
report=dict(input_digest=digest(w),counts=dict(stats),observed_positions=len(vertices),initial_open_or_mate_positions=initial_open,
    closed_candidate_positions=len(closed),source_histories_in_closed=dict(known),remaining_unknown_candidates=affected,
    seconds=time.perf_counter()-start,status='NEGATIVE_FEASIBILITY_NO_NEW_LABEL'if not affected else'PENDING_INDEPENDENT_COMPLETE_CORE_CERTIFICATE',
    scope='Candidate closure of existing recorded edges using complete legal action names already source-bound. No new successor expansion or adopted negative label. Unknown candidates would require independent Core verification;zero candidates closes this route without expansion.')
save(p/'closed-observed-feasibility.json',report);print(report)
