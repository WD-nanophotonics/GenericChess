"""Finite-clock verification and posthoc occupation of a new qualified closure."""
from pathlib import Path
from copy import copy
from collections import Counter
import gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.leaper_ab_learning_truth import tables,classify
from scripts.leaper_cooperative_certificate import encode_position


def clock_proof(graph,output):
    tick=time.perf_counter();g=json.loads(gzip.decompress(graph.read_bytes()));ts={int(k):v for k,v in g['terminals'].items()};rs={int(k):v for k,v in g['ranks'].items()};vs={int(k):v for k,v in g['relative_values'].items()};edges=g['edges'];sides=[p[0]for p in g['positions']]
    assert set(ts.values())<={None,0}
    values=[int(ts.get(i,-1)==0)for i in range(len(edges))];rows=[]
    for h in range(max(rs.values(),default=0)+1):
        assert values==[int(vs[i]!=0 and rs[i]<=h)for i in range(len(edges))]
        rows.append(dict(H=h,WIN=sum(values),digest=hashlib.sha256(bytes(values)).hexdigest()))
        future=[int(ts[i]==0)if i in ts else max(values[j]for j in ee)if sides[i]==0 else min(values[j]for j in ee)for i,ee in enumerate(edges)]
        if h==max(rs.values(),default=0):assert future==values
        values=future
    out=dict(verified=True,graph_sha256=L.sha(graph),vertices=len(edges),rows=rows,fixed_point_verified=True,seconds=time.perf_counter()-tick,
        scope='Complete finite-clock Bellman DP for the declared single-winning-seat physical graph. Adding draw-only repetition cannot create a win; positive actual histories still require strict-rank/incoming-key admission.')
    write(output,out);return out


def run(panel,graph,qualification,swapped_qualification,clock,output):
    if not all(p.is_file()for p in(qualification,swapped_qualification,clock)):
        raise ValueError('qualification incomplete; no truth labels emitted')
    tick=time.perf_counter();g=json.loads(gzip.decompress(graph.read_bytes()));cp=json.loads(clock.read_bytes());assert cp['verified']and cp['graph_sha256']==L.sha(graph)
    cfg=json.loads((panel/'plan.json').read_bytes());result=json.loads((panel/'result.json').read_bytes());world=cfg['worlds']['two-type'];c=L.compile_rule(L.ruleset_from_dict(world['rule']));assert g['rule']==world['rule']
    lookup,keys,proofs=tables('two-type',c,{3:g},[(3,False,graph,qualification),(3,True,graph,swapped_qualification)])
    old=set();previous=Path('docs/research/data/leaper_ab_learning_and_rank_20261024');translation=str.maketrans('0123456','0456123')
    for n in range(3):
        raw=json.loads(gzip.decompress((previous/f'domain-{n}.json.gz').read_bytes()))['positions'];old.update(tuple(p)for p in raw)
        if n==0:old.update((1-p[0],p[1].translate(translation))for p in raw)
    rows=[]
    for entry in result['rows']:
        slot=entry['slot']
        if slot['group']!='two-type':continue
        row=json.loads((panel/f"game-{slot['id']:03d}.json").read_bytes());s=restore(c,world['roots'][slot['root']]['record']);events={e['state_sha256']:e for e in row['events']if e['kind']=='candidate'};counts=Counter()
        for action in L.deserialize_game_record(json.dumps(row['final_record'])).actions:
            event=events.get(L.state_sha(s.state))
            if event is not None and tuple(encode_position(s.state.position,c.initial_position))not in old:
                value,basis=classify(s,c,lookup,keys);counts['new_root_'+basis]+=1
                if value is not None:
                    counts['newly_qualified_root_occurrences']+=1
                    counts['favorable_WIN']+=int(value*(1 if s.state.position.side_to_move==0 else-1)==1)
                    child_values=[];chosen=None
                    for a in s.legal_actions():
                        ch=copy(s);ch.submit(a);v,b=classify(ch,c,lookup,keys);child_values.append(v)
                        if a==action:chosen=v
                    if all(v is not None for v in child_values):
                        assert (max if s.state.position.side_to_move==0 else min)(child_values)==value
                        counts['complete_known_frontiers']+=1;counts['forks']+=int(len(set(child_values))>1);counts['suboptimal_choices']+=int(chosen!=value)
            s.submit(action)
        rows.append(dict(slot=slot,counts=dict(counts)))
    source_root=restore(c,g['root_record']);assert source_root.state.ply_count==63
    source_children=[]
    for a in source_root.legal_actions():
        ch=copy(source_root);ch.submit(a);assert ch.state.terminal_status.is_terminal and ch.result.winner is None
        source_children.append(dict(action=L.record_value(a),terminal=L.record_value(ch.result),state_sha256=L.state_sha(ch.state)))
    out=dict(verified=True,rows=rows,proofs=proofs,clock_proof_sha256=L.sha(clock),source_oneply=dict(state_sha256=L.state_sha(source_root.state),record=L.record_value(source_root.to_record()),all_actual_children_DRAW=source_children),seconds=time.perf_counter()-tick,
        scope='Additional old-UNKNOWN natural quiet occurrences only, using both owner qualifications. No union-by-counts or oracle TRAIN starts. Existing outside/low-rank barriers remainUNKNOWN; optimal-future WDL is distinct from actual Uniform payoff. This does not rewrite original old truth tables.')
    write(output,out);return out
