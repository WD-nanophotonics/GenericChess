"""Replay retained later-H6 decisions and their complete source histories.

No new Player calls or training. Exact action labels use the independently
retained closed H6 graph and its admitted full visited-set semantics.
"""
from collections import Counter
from fractions import Fraction as F
from pathlib import Path
from copy import copy
import argparse,gzip,json,time
from generic_chess.core.actions import action_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from scripts.leaper_design import match_action,state_sha
from scripts.leaper_h6_later_records import ContextBinder
from scripts.leaper_h6_initial_truth import history_solver


def verify(result,directory,*,old=None):
    tick=time.perf_counter();binder=ContextBinder(Path(directory));contexts=result['bound_contexts'];plan=result['plan'];counts=Counter();solvers={};summaries=[]
    if len(contexts)!=len(plan['contexts'])or len(result['rows'])!=plan['planned_retained']:raise ValueError('complete retained support differs')
    oldby={}if old is None else{(r['state_sha'],r['B'],r['depth']):r for r in old['rows']}
    seen=set();bound=[]
    for candidate,saved in zip(plan['contexts'],contexts,strict=True):
        s,b=binder.bind(candidate)
        if b!=saved:raise ValueError('actual originalmu history binding differs')
        bound.append(s)
    for row in result['rows']:
        context=row['context'];B=row['B'];dep=row['depth'];key=context,B,dep
        if key in seen:raise ValueError('duplicate retained query')
        seen.add(key)
        if(B,dep)not in map(tuple,plan['profiles']):raise ValueError('unplanned query profile')
        candidate=contexts[context];family=candidate['family'];s=copy(bound[context]);env=FixedScaleSessionEnv(s,unit_type='A');model=Model([B if name==('board','B')else 1. for name in env.names]);receipt=row['receipt']
        if not receipt['complete']or receipt['completed_depth']!=dep or row['state_sha']!=state_sha(s.state):raise ValueError('query depth/source incomplete')
        if row['reused']:
            prev=oldby.get((row['state_sha'],B,dep))
            if prev is None or prev['receipt']!=receipt:raise ValueError('old receipt bytes differ')
            counts['reused']+=1
        else:counts['new_queries']+=1;counts['new_nodes']+=receipt['nodes']
        if not receipt['pv_choices']or receipt['pv_choices'][0]!=receipt['action']:raise ValueError('root action/PV differs')
        for index,choice in enumerate(receipt['pv_choices']):
            if choice['kind']!='ACTION':raise ValueError('unexpected declaration')
            a=match_action(s,choice['action'])
            if index==0 and action_to_dict(a)!=row['action']:raise ValueError('chosen action differs')
            s.submit(a);counts['PV_Core_edges']+=1
        leaf=FixedScaleSessionEnv(s,unit_type='A');term=leaf.terminal();phi=None if term is not None else list(leaf.features())
        if receipt['pv_terminal']!=(term is not None)or receipt['pv_phi']!=phi:raise ValueError('literal PV gradient leaf differs')
        value=MATE*term if term is not None else model.raw(phi)
        if receipt['value']!=value:raise ValueError('literal PV value differs')
        _,c,d,positions,_=binder.family(family)
        if family not in solvers:
            solvers[family]=history_solver(d['edges'],{int(i):w for i,w in d['terminals'].items()},[p.side_to_move for p in positions],lambda *a:None,max_calls=1000000)[0]
        i=candidate['vertex'];k=d['actions'][i].index(row['action']);child=d['edges'][i][k];prior=tuple(sorted((*candidate['prior_vertices'],i)));wdl=solvers[family](child,candidate['h']-1,prior)[0]
        if row['exact_WDL']!=wdl:raise ValueError('full history action WDL differs')
        counts['retained_queries']+=1
    for family in sorted({c['family']for c in contexts}):
        for B,dep in plan['profiles']:
            rr=[r for r in result['rows']if r['family']==family and r['B']==B and r['depth']==dep];bad=[r for r in rr if r['exact_WDL']<0]
            weighted=sum((F(contexts[r['context']]['probability'])for r in bad),F(0))
            summaries.append(dict(family=family,B=B,depth=dep,contexts=len(rr),inferior=len(bad),fixed_incoming_bad_action_mass=str(weighted),retained_nodes=sum(r['nodes']for r in rr)))
    if any(counts[k]!=v for k,v in result['counts'].items()):raise ValueError('new/reused cost accounting differs')
    return dict(verified=True,counts=dict(counts),summaries=summaries,seconds=time.perf_counter()-tick,
        scope='All752actualoriginalmu historiesand2256retainedqueryPVsreplayed. Exactadmittedrepeat2historylabels;0newPlayer. Mechanism-selectedfinitecontexts,fixedUNIFORMincoming,not learneronpolicyutility/heldout/gainorwholetrace learning.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--old',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=json.loads(a.result.read_bytes());old=json.loads(a.old.read_bytes());receipt=verify(result,a.directory,old=old);a.output.write_text(json.dumps(receipt,indent=2));print(receipt)
