"""One bounded exact-mass Uniform response-tree feasibility check.

Caller: frozen Unit material, fresh cold q0 D4 Player/query, equal capture
ordering, actual complete GameSession/history/clock, IID legal Uniform foe.
Returned completed decisions are retained as a fixed response map. No warm TT,
Position-only Markov law, learning, price sweep or whole-policy exactness is
assumed. An incomplete response or unexplored prefix retains UNKNOWN mass.
"""
from pathlib import Path
from collections import deque,Counter
from fractions import Fraction
import argparse,gzip,heapq,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.leaper_cooperative_certificate import encode_position
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_microgames import role_stop_requested
from generic_chess.learning.incremental import Model,FixedScaleSessionEnv,BudgetEnd
from generic_chess.learning.mainline_search import search
from generic_chess.core.actions import action_to_dict

COST=Path('artifacts/leaper-four-actor-learner-cost-20261024')
GRAPH=Path('artifacts/leaper-four-actor-truth-20261024')
def ratio(x):return [x.numerator,x.denominator]
def plan(output):
    output.mkdir(parents=True,exist_ok=False);cfg=L.load(COST/'plan.json');qual=L.load(GRAPH/'qualification.json')
    assert qual['verified']and qual['sha256']==L.sha(GRAPH/'domain.json.gz')
    spec=dict(source=cfg['source'],producer_sha256=L.sha(Path(__file__)),world=cfg['world'],
        graph_sha256=qual['sha256'],qualification_sha256=L.sha(GRAPH/'qualification.json'),
        source_cost_sha256=L.sha(COST/'game-000.json'),root=0,role=0,weights=[1.,1.,0.,0.],
        question='Can exact IID-Uniform terminal-WIN0 expectation of one full-history cold material response policy be bounded economically, rather than assuming a Position-only law?',
        policy='Fresh library mainline q0 D4/max8192nodes/5seconds, equal capture ordering and fresh TT; require complete requestedD4/literal PV. Each first retained complete response binds that full-history state. Original matching actual receipts reused without another search. All other responses UNKNOWN until queried.',
        target='P(actual terminalWIN0) for this one frozen response map against IID legal Uniform under actualH64/repeat4; no whole-game observation wall cap. This target differs from original180s episode cap and from warm DEFAULT/served controller. Query decisions retain actual timing; no deterministic timed-policy theorem.',
        selection='First original root0, no WDL/outcome/gradient-selected starting state. One original-mu feasibility question, not a price/cell panel or new source sampler.',
        seconds=2100,queries_cap=20000,prefixes_cap=250000,precision=[1,1000],expected_seconds=1700,
        stop='Stop at first cap, exact unresolvedmass<=.001, userstop or complete tree. No refill/retry/extension; incomplete responses retain UNKNOWNmass. Exact Fraction mass conservation, not confidence intervals.',
        budget='Originalepisode~2.4s; one physicalclosure~600s plus qualification~600s, thisresponse-tree~1700s and analysis/readers~1200s: estimated4100s<120min aggregate. No artificial split of>=120min work. Actual paid calls/time/nodes and serialization reported.',
        scope='Cooperative shortest distance only prunes WIN0-impossible branches (no forcedDRAW claim). Full position/history/clock remain in every response. Bounds concern retained partial response map; not an exact Uniform expectation for the original seeded/timecapped episode or any arbitrary learned/warm policy.')
    write(output/'spec.json',spec);return spec

def run(output,resume=None):
    spec=L.load(output/'spec.json')
    if resume is None:
        assert spec['producer_sha256']==L.sha(Path(__file__))
    else:
        repair=L.load(resume)
        assert repair['original_producer_sha256']==spec['producer_sha256']
        assert repair['resumed_producer_sha256']==L.sha(Path(__file__))
        assert repair['original_execution_sha256']==L.sha(output/'execution.json')
        assert repair['original_queries_sha256']==L.sha(output/'queries.jsonl.gz')
        old_queries=[json.loads(x)for x in gzip.decompress((output/'queries.jsonl.gz').read_bytes()).decode().splitlines()]
        assert old_queries and all(q['reused']and q['origin']=='actual'for q in old_queries)
    assert spec['graph_sha256']==L.sha(GRAPH/'domain.json.gz')
    assert spec['qualification_sha256']==L.sha(GRAPH/'qualification.json')
    execution=output/('execution.json'if resume is None else'resumed-execution.json')
    with execution.open('x',encoding='utf8')as f:json.dump(dict(started=time.time(),resume=None if resume is None else str(resume)),f)
    # A serialization entry repair keeps the ORIGINAL absolute deadline.
    elapsed=0 if resume is None else time.time()-L.load(output/'execution.json')['started']
    tick=time.perf_counter()-elapsed;g=json.loads(gzip.decompress((GRAPH/'domain.json.gz').read_bytes()))
    world=spec['world'];c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    assert g['rule']==world['rule']
    index={(p[0],p[1]):i for i,p in enumerate(g['positions'])}
    decisive=[int(i)for i,w in g['terminals'].items()if w==0]
    distance,_=cooperative_distances(g['edges'],decisive)
    old=L.load(COST/'game-000.json')
    cached={e['state_sha256']:e['receipt']for e in old['events']if e['kind']=='candidate'and e['receipt']['complete']and e['receipt']['completed_depth']==4}
    start=world['roots'][spec['root']]['record'];nodes=[dict(parent=None,action=None,kind=None)]
    origin={k:'actual'for k in cached}
    heap=[(-Fraction(1),0)];mass=Counter();counts=Counter();unknown=Fraction(0);frontier_mass=Fraction(1);status='COMPLETE';queries=[]
    def session(i):
        aa=[]
        while nodes[i]['parent']is not None:aa.append(nodes[i]['action']);i=nodes[i]['parent']
        record=dict(start);record['actions']=start['actions']+list(reversed(aa))
        return restore(c,record)
    def guard():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-tick>=spec['seconds']:raise BudgetEnd('RESPONSE_TREE_CAP_UNKNOWN')
    def add(parent,a,p):
        j=len(nodes);nodes.append(dict(parent=parent,action=action_to_dict(a),kind=None));heapq.heappush(heap,(-p,j));return j
    query_path=output/('queries.jsonl.gz'if resume is None else'queries-resume.jsonl.gz')
    with gzip.open(query_path,'xt',encoding='utf8')as log:
        while heap:
            pending=frontier_mass+unknown
            if pending<=Fraction(*spec['precision']):status='PRECISION';break
            if role_stop_requested():status='USER_STOP';break
            if time.perf_counter()-tick>=spec['seconds']:status='TIME_CAP_UNKNOWN';break
            if counts['new_Player_queries']>=spec['queries_cap']:status='QUERY_CAP_UNKNOWN';break
            if len(nodes)+16>spec['prefixes_cap']:status='PREFIX_CAP_UNKNOWN';break
            neg,i=heapq.heappop(heap);p=-neg;frontier_mass-=p;s=session(i);n=nodes[i];n.update(state_sha256=L.state_sha(s.state),ply=s.state.ply_count,mass=ratio(p))
            counts['expanded_prefixes']+=1
            if s.state.terminal_status.is_terminal:
                bucket='actual_WIN0'if s.result.winner==0 else'actual_WIN1'if s.result.winner==1 else'actual_DRAW'
                n.update(kind=bucket);mass[bucket]+=p;counts[bucket]+=1;continue
            raw=encode_position(s.state.position,c.initial_position);ix=index[(raw[0],raw[1])]
            if distance.get(ix,10**9)>64-s.state.ply_count:
                n.update(kind='no_cooperative_WIN0');mass['no_cooperative_WIN0']+=p;counts['no_cooperative_WIN0']+=1;continue
            if s.state.position.side_to_move!=spec['role']:
                choices=sorted(FixedScaleSessionEnv(s,unit_type='A').actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True))
                n.update(kind='Uniform',children=[add(i,a.action,p/len(choices))for a in choices]);counts['Uniform_prefixes']+=1;frontier_mass+=p
            else:
                r=cached.get(n['state_sha256']);reuse=r is not None
                if not reuse:
                    receipt=search(FixedScaleSessionEnv(s,unit_type='A'),Model(spec['weights']),depth=4,nodes=8192,seconds=min(5.,max(.001,spec['seconds']-(time.perf_counter()-tick))),cancel=guard)
                    r=L.record_value(receipt);counts['new_Player_queries']+=1;counts['new_Player_nodes']+=r['nodes']
                else:counts['reused_'+origin[n['state_sha256']]+'_receipts']+=1
                q=dict(prefix=i,state_sha256=n['state_sha256'],reused=reuse,origin=origin.get(n['state_sha256'],'new'),receipt=r)
                log.write(json.dumps(q,separators=(',',':'))+'\n');log.flush()
                n.update(query=len(queries));queries.append(q)
                if not r['complete']or r['completed_depth']<4 or r['action']is None:
                    n.update(kind='UNKNOWN_response');unknown+=p;counts['UNKNOWN_responses']+=1;continue
                cached[n['state_sha256']]=r
                if not reuse:origin[n['state_sha256']]='tree'
                choice=L.match_action(s,r['action']['action'])
                n.update(kind='candidate',children=[add(i,choice,p)]);frontier_mass+=p
            if counts['expanded_prefixes']%500==0:
                lower=Fraction(mass['actual_WIN0']);pending=frontier_mass+unknown
                print(counts['expanded_prefixes'],len(heap),counts['new_Player_queries'],float(lower),float(lower+pending),round(time.perf_counter()-tick,2),flush=True)
    assert frontier_mass==-sum((a for a,_ in heap),Fraction(0))
    pending=frontier_mass+unknown
    if status=='COMPLETE'and unknown:status='UNKNOWN_RESPONSES'
    assert sum(mass.values(),Fraction(0))+pending==1
    raw=json.dumps(dict(nodes=nodes,frontier=[dict(prefix=i,mass=ratio(-a))for a,i in heap],unresolved_response_mass=ratio(unknown)),separators=(',',':')).encode()
    (output/'tree.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    lower=Fraction(mass['actual_WIN0'])
    result=dict(status=status,counts=dict(counts),prefixes=len(nodes),leaf_mass={k:ratio(v)for k,v in mass.items()},
        unresolved_mass=ratio(pending),WIN0_bounds=[ratio(lower),ratio(lower+pending)],WIN0_decimal=[float(lower),float(lower+pending)],
        exact_mass_conservation=True,seconds=time.perf_counter()-tick,
        tree_sha256=L.sha(output/'tree.json.gz'),queries_file=query_path.name,queries_sha256=L.sha(query_path),
        resumed=resume is not None,original_deadline_preserved=True)
    write(output/'result.json',result);print(result,flush=True);return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--resume',type=Path);a=ap.parse_args()
    if a.mode=='run':run(a.output,a.resume)
    else:plan(a.output)

