"""Full-history truth on a finite counterfactual A/B mechanism panel.

The source mu is unchanged. These complete three-ply continuations of an
already played prefix are diagnostics only, never experiential training starts.
Physical WIN lifts only with a strict rank, enough actual clock and no incoming
third-visit barrier; physical DRAW uses both players' draw safety invariant.
"""
from pathlib import Path
from copy import copy
from collections import Counter
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,BudgetEnd
from generic_chess.learning.mainline_search import search


def load_graph(path):
    g=json.loads(gzip.decompress(path.read_bytes()));c=L.compile_rule(L.ruleset_from_dict(g['rule']));ps=[decode_position(p,c.initial_position)for p in g['positions']]
    return g,c,{p:i for i,p in enumerate(ps)},{int(k):v for k,v in g['relative_values'].items()},{int(k):v for k,v in g['ranks'].items()}


def label(s,indices,values,ranks):
    # Explicit frozen source: plain capture/removal, bare seat1, H64/repeat4.
    if s.state.terminal_status.is_terminal:return 0 if s.result.winner is None else 1 if s.result.winner==0 else-1,'actual_terminal'
    i=indices.get(s.state.position)
    if i is None:return None,'outside_complete_domain'
    v=values[i]*(1 if s.state.position.side_to_move==0 else-1)
    if v==0:return 0,'complete_physical_draw_safety'
    if v!=1:raise ValueError('bare opposing King cannot score')
    if ranks[i]>64-s.state.ply_count:return None,'insufficient_actual_clock'
    if max(n for _,n in s.state.repetition_counts)>2:return None,'prehistory_barrier_needs_separate_proof'
    return 1,'strict_rank_with_clock_and_incoming_counts_le2'


def plan(graph,output):
    output.mkdir(parents=True,exist_ok=False);g,c,ix,vs,rs=load_graph(graph);root=restore(c,g['root_record']);pool=[]
    def visit(s,left):
        if s.state.terminal_status.is_terminal:return
        if not left:
            phi=FixedScaleSessionEnv(s,unit_type='A').features()
            if phi==(1,1,0,0)and s.state.position.side_to_move==0:pool.append(s)
            return
        for a in s.legal_actions():
            ch=copy(s);ch.submit(a);visit(ch,left-1)
    visit(root,3);pool.sort(key=lambda s:L.state_sha(s.state));chosen=pool[:16]
    # Freeze selection before inspecting per-root WDL labels.
    selected=[dict(record=L.record_value(s.to_record()),state_sha256=L.state_sha(s.state))for s in chosen]
    spec=dict(graph_sha256=L.sha(graph),rule=g['rule'],selected=selected,
        producer_sha256=L.sha(Path(__file__)),requested_depths=[4,12],B=[.5,1.,2.],nodes=1000000,query_seconds=20,whole_seconds=1200,
        question='At the same material composition and real full-history WDL, do relative prices or extra depth change actual choice quality?',
        selection='First16 full-history hashes among ALL legal three-ply continuations of the original contact game1 prefix7 retaining A+B and seat0 to move. No WDL filtering. Exposed counterfactual diagnostics, not natural occupation, new source mu, training starts or population strength.',
        rank_lift='Complete source Core domain/ranks; one strictly decreasing winning action at seat0 and every legal defender action decreases rank. Future Positions cannot repeat. Incoming counts<=2 and repeat4 leave room for each future key at most once. Rank<=actual remaining64 clock, actual terminal precedence. No generic Position/history quotient.',
        stop='One exclusive run/cumulative cap. All missing/incomplete UNKNOWN, no refill; requested/completed depth and actual cost separate.')
    write(output/'spec.json',spec)
    labels=[];examples={}
    for s in pool:
        v,b=label(s,ix,vs,rs);examples.setdefault(str(v),dict(record=L.record_value(s.to_record()),state_sha256=L.state_sha(s.state),value=v,basis=b,index=ix[s.state.position],rank=rs.get(ix[s.state.position])))
        labels.append(v)
    write(output/'pool-truth.json',dict(counts=dict(Counter(map(str,labels))),examples=examples,scope='Complete finite posthoc3ply pool, not original mu or independent samples. Featurematched value contrast, not a proof that deeper search cannot use geometry.'))


def run(graph,output):
    spec=json.loads((output/'spec.json').read_bytes());assert spec['graph_sha256']==L.sha(graph)and spec['producer_sha256']==L.sha(Path(__file__))
    with(output/'execution.json').open('x')as f:json.dump(dict(started=time.time()),f)
    g,c,ix,vs,rs=load_graph(graph);rows=[];began=time.perf_counter()
    slots=[dict(id=i,root=ri,depth=d,B=b)for i,(ri,d,b)in enumerate((ri,d,b)for d in(4,12)for ri in range(len(spec['selected']))for b in(.5,1.,2.))]
    for slot in slots:
        if time.perf_counter()-began>=1200 or role_stop_requested():break
        sr=spec['selected'][slot['root']];s=restore(c,sr['record']);assert L.state_sha(s.state)==sr['state_sha256'];value,basis=label(s,ix,vs,rs)
        labels=[]
        for a in s.legal_actions():
            ch=copy(s);ch.submit(a);v,b=label(ch,ix,vs,rs);labels.append(dict(action=L.record_value(a),value=v,basis=b))
        def cancel():
            if role_stop_requested()or time.perf_counter()-began>=1200:raise BudgetEnd('DIAGNOSTIC_CAP_UNKNOWN')
        model=Model((1,slot['B'],0,0));receipt=search(FixedScaleSessionEnv(s,unit_type='A'),model,depth=slot['depth'],nodes=1000000,seconds=min(20,1200-(time.perf_counter()-began)),pv_reserve_fraction=.1,cancel=cancel)
        chosen=None
        if receipt.complete and receipt.action is not None:
            ch=copy(s);ch.submit(receipt.action.action);chosen=label(ch,ix,vs,rs)[0]
        row=dict(slot=slot,state_sha256=sr['state_sha256'],root_value=value,root_basis=basis,actions=labels,receipt=L.record_value(receipt),chosen_value=chosen,suboptimal=None if chosen is None or value is None else chosen<value)
        write(output/f"query-{slot['id']:03d}.json",row);rows.append(row);write(output/'partial.json',dict(rows=rows,seconds=time.perf_counter()-began))
        print(slot,'depth',receipt.completed_depth,'value',value,'chosen',chosen,'seconds',receipt.seconds,flush=True)
    write(output/'result.json',dict(rows=rows,seconds=time.perf_counter()-began,unstarted=slots[len(rows):]))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--graph',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();globals()[a.mode](a.graph,a.output)
