from collections import Counter,defaultdict
from pathlib import Path
from scripts.leaper_saved_child_bounds import current_truth,propagate,meet
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_cooperative_truth import admit
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_design import state_sha
from scripts.research_record import record_value
from generic_chess.core.identity import search_state_identity,repetition_identity_key
from generic_chess.core.actions import action_from_dict
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
import json,time

p=Path('artifacts/saved-child-bounds-d19a');start=time.perf_counter()
t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
u,_=propagate(t,load(p/'edges.json.gz'));roots={r['id']:r for r in u['roots']}
compiled={fp:compile_rule(ruleset_from_dict(raw))for fp,raw in u['rules'].items()}
for fp,c in compiled.items():
    admit(ruleset_from_dict(u['rules'][fp]),c)
    assert not c.ir.triggers and not c.ir.aux_slots
groups={k:defaultdict(list)for k in ('mainline_search_identity','capture_pruned_candidate')}
ids={};stats=Counter();begin=time.perf_counter();last=0.
for rid,record in u['records'].items():
    c=compiled[record['ruleset_fingerprint']]
    s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
    actors_by_key={}
    for action in record['actions']:
        now=time.perf_counter()
        if now-begin>=180:raise RuntimeError('IDENTITY_SCAN_CAP_UNKNOWN')
        if now-last>=.2:
            last=now
            if role_stop_requested():raise RuntimeError('USER_STOP')
        st=s.state;hid=state_sha(st);n=sum(pc is not None for pc in st.position.board)
        key=repetition_identity_key(st.position,c)
        if key in actors_by_key:assert actors_by_key[key]==n
        actors_by_key[key]=n
        assert not st.position.aux_state and not any(h.total()for h in st.position.hands)
        assert Counter(h.position_key for h in st.history)==dict(st.repetition_counts)
        if hid not in ids:
            identity=search_state_identity(st,c)
            assert not identity.adjudication_context
            relevant=tuple((k,v)for k,v in st.repetition_counts if actors_by_key[k]<=n)
            k1=digest(record_value(identity))
            k2=digest(dict(position=record_value(st.position),ply_count=st.ply_count,repetition_counts=relevant,
                           terminal=record_value(st.terminal_status)))
            ids[hid]=dict(mainline_search_identity=k1,capture_pruned_candidate=k2)
            for name,k in ids[hid].items():groups[name][k].append(hid)
            stats['retained_count_entries']+=len(relevant)
            stats['original_count_entries']+=len(st.repetition_counts)
        s.submit(action_from_dict(action));stats['actions_replayed']+=1
    stats['records']+=1
assert set(ids)==set(roots)
reports={}
for name,gs in groups.items():
    summary=Counter();matched=[]
    for key,hs in gs.items():
        if len(hs)>1:summary['nontrivial_groups']+=1;summary['histories_in_nontrivial_groups']+=len(hs)
        bounds=[-1,1]
        for h in hs:bounds=meet(bounds,roots[h]['wdl_bounds'])
        candidates=[h for h in hs if roots[h]['wdl_bounds']!=bounds]
        if candidates:matched.append(dict(key=key,histories=hs,intersection=bounds,candidates=candidates))
        for prop in ('wdl_fork','cooperative_decisive','universal_draw'):
            known={roots[h][prop]for h in hs if roots[h][prop]is not None}
            assert len(known)<=1,(name,prop,hs)
            if known:summary['potential_'+prop+'_labels']+=sum(roots[h][prop]is None for h in hs)
    reports[name]=dict(groups=len(gs),counts=dict(summary),wdl_candidates=matched)
report=dict(input_digest=digest(u),reports=reports,counts=dict(stats),component_seconds=time.perf_counter()-begin,
            end_to_end_seconds=time.perf_counter()-start,
            scope='Existing full histories only. Mainline identity reused directly; capture-pruned key is a feasibility candidate, not an adopted generic history quotient or new labels. No rule generation, rollout, forecast or graph expansion.')
save(p/'identity-candidates.json.gz',dict(input_digest=digest(u),ids=ids))
save(p/'identity-feasibility.json',report)
print(report)
