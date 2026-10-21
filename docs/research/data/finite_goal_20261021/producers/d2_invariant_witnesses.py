"""Prespecified D2 witness search on ALL unique D1-invariant saved histories.

A corner witness disproves invariance; failure to find one does NOT prove D2
invariance because min/max trees are piecewise affine. No WDL, labels or training.
"""
from pathlib import Path
from itertools import product
from dataclasses import replace
import argparse,json,time
import numpy as np
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts.material_choice_sensitivity import vector
from scripts.price_regions import CONFIG,Budget,TreeLimit,build_tree
from scripts.research_record import record_value,write_record


def run(sensitivity_path,source_path,output):
    if output.exists():raise FileExistsError(output)
    sens=json.loads(sensitivity_path.read_text());source=json.loads(source_path.read_text())
    chosen=[x for x in sens['rows'] if x.get('status')=='ongoing' and x['certificates']['full']['invariant']]
    unique={};duplicates=[]
    for row in chosen:
        key=(row['seed'],json.dumps(row['record'],sort_keys=True))
        if key in unique:duplicates.append(dict(seed=row['seed'],policy=row['policy'],ply=row['ply'],same_as_policy=unique[key]['policy']))
        else:unique[key]=row
    result=dict(scope=__doc__,declaration=dict(input_slots=len(chosen),unique_histories=len(unique),depth=2,
        board_box=[125,4000],hand_box=[0,4000],anchor=0,queries='baseline + all2**d corners + all2**d one-step-interior corners for each full typed dimension d',
        global_nodes=150000,global_seconds=90,public_nodes=100000,public_seconds=5,q=0,tt=False,ordering=False),duplicates=duplicates,rows=[])
    write_record(output,result);budget=Budget(90,150000);start=time.perf_counter()
    for raw in source['rules']:
        rows=[x for x in unique.values() if x['seed']==raw['seed']]
        if not rows:continue
        c=compile_ruleset_for_execution(ruleset_from_dict(raw['definition']));profile,_=build_semantic_opportunity_profile(c,CONFIG)
        for row in rows:
            s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));features=tuple(map(tuple,row['features']));n=len(features)//2
            assert not c.ir.declarations
            assert 1<=len(features)<=12, 'Explicit corner memory scope; keep unsupported rather than drop types'
            lo=np.array([125]*n+[0]*n);hi=np.array([4000]*(2*n));baseline=np.array([1000]*n+[900]*n)
            corners=np.array([np.where(bits,hi,lo) for bits in product((0,1),repeat=2*n)])
            interiors=np.minimum(hi-1,np.maximum(lo+1,corners));weights=np.vstack([baseline,corners,interiors])
            dest=dict(seed=row['seed'],policy=row['policy'],ply=row['ply'],record=row['record'],features=features,public=[])
            result['rows'].append(dest)
            def f(state,owner):return tuple(map(int,vector(state,owner,features)))
            before=budget.edges;t=time.perf_counter()
            try:tree=build_tree(s.state,c,2,s.state.position.side_to_move,budget,set(),leaf_features=f)
            except TreeLimit as exc:
                dest['incomplete']=str(exc);write_record(output,result);break
            def values(node):
                if node[0]=='leaf':
                    v=node[1]
                    if len(v)==2:return np.full(len(weights),v[1],dtype=np.int64)
                    return weights@np.array(v,dtype=np.int64)
                values_=np.array([values(child) for _,child in node[1]])
                return (np.max if node[0]=='max' else np.min)(values_,axis=0)
            names=[a for a,_ in tree[1]];scores=np.array([values(child) for _,child in tree[1]])
            selected=np.argmax(scores,axis=0);opts=scores==np.max(scores,axis=0)[None,:]
            corner_end=1+len(corners)
            changed_choice=np.flatnonzero(selected!=selected[0]);changed_sets=np.flatnonzero(np.any(opts!=opts[:,[0]],axis=0))
            dest.update(tree_nodes=budget.edges-before,tree_seconds=time.perf_counter()-t,baseline_selected=names[selected[0]],
                baseline_optimal=[a for a,v in zip(names,opts[:,0]) if v],dimensions=len(features),corners=len(corners),corner_first_changes=int(sum(selected[1:corner_end]!=selected[0])),
                interior_first_changes=int(sum(selected[corner_end:]!=selected[0])),optimal_set_changes=len(changed_sets),witness=None)
            if len(changed_choice):witness=int(changed_choice[0])
            elif len(changed_sets):witness=int(changed_sets[0])
            else:witness=None
            if witness is not None:
                dest['witness']=dict(index=witness,weights=weights[witness].tolist(),selected=names[selected[witness]],
                    optimal=[a for a,v in zip(names,opts[:,witness]) if v],interior=witness>=corner_end)
            for index in ([0,witness] if witness is not None else [0]):
                board={t:0 for t in c.support.type_metadata};hand=board.copy()
                for (kind,t),w in zip(features,weights[index]):(board if kind=='board' else hand)[t]=int(w)
                p=replace(profile,board_value_by_type=board,hand_value_by_base_type=hand,promotion_gain_by_type={t:0 for t in board})
                ev=Evaluator(c,p,CONFIG);pl=AlphaBetaPlayer(c,evaluator_override=ev,use_disk_cache=False,use_tt=False,use_ordering=False,
                    use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False))
                before_state=s.state;d=pl.choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=5,
                    quiescence_max_depth=0,quiescence_hard_max_depth=0))
                optimal=[a for a,v in zip(names,opts[:,index]) if v]
                assert d.completed_depth==2 and d.score==int(np.max(scores[:,index])) and str(d.action) in optimal and s.state==before_state
                dest['public'].append(dict(weights=weights[index].tolist(),decision=record_value(d),action=str(d.action),optimal=optimal))
            write_record(output,result)
        if result['rows'] and result['rows'][-1].get('incomplete'):break
    result.update(tree_nodes=budget.edges,wall_seconds=time.perf_counter()-start,observed_unique=len(result['rows']))
    write_record(output,result)
    print('slots',len(chosen),'unique',len(unique),'done',len(result['rows']),'nodes',budget.edges,'seconds',result['wall_seconds'])
    print([(r['seed'],r['policy'],r['ply'],r.get('corner_first_changes'),r.get('interior_first_changes'),r.get('optimal_set_changes'),r.get('incomplete')) for r in result['rows']])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('sensitivity',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();run(a.sensitivity,a.source,a.output)
