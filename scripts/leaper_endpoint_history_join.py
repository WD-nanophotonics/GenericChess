"""Zero-query cross-study complete-history join; never executes source capsules."""
from __future__ import annotations
import argparse,gzip,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path

def load(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)
def digest(v):
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run():
 base=Path('docs/research/data')
 ip=base/'leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz'
 sources={'inputs':ip,'resource':base/'leaper_root_order_quality_20261026/population-games/games.json.gz','pvs':base/'leaper_pvs_quality_pilot_20261026/pilot/games.json.gz'}
 roots={r['id']:r for r in load(ip)['rows'] if r['prefix_length']==2}
 common=defaultdict(list);families=defaultdict(lambda:dict(cases=[],games=[],query_reasons=Counter(),depth64=0,initial_choices={}))
 for case,root in roots.items():
  families[root['family']]['cases'].append(case)
 for study in ('resource','pvs'):
  for g in load(sources[study]):
   root=roots[g['case_id']];f=families[root['family']]
   assert root['record']==g['initial_record']
   assert root['fingerprint']==g['fingerprint']
   actions=g['final_record']['actions'];prefix=len(g['initial_record']['actions'])
   assert actions[:prefix]==g['initial_record']['actions']
   assert len(actions)==prefix+len(g['queries'])
   for i,q in enumerate(g['queries']):
    r=dict(g['initial_record'],actions=actions[:prefix+i])
    after=dict(r,actions=actions[:prefix+i+1])
    assert digest(r)==q['record_before_sha256'],(study,g['game_id'],i,'before')
    assert digest(after)==q['record_after_sha256'],(study,g['game_id'],i,'after')
    d=q['decision'];a=d['action'];wire=actions[prefix+i]
    assert a['actor_type_id']==wire['actor_type_id'] and a['pattern_id']==wire['pattern_id'] and a['geometry_id']==wire['geometry_id']
    assert [a['from_square']['file'],a['from_square']['rank']]==wire['from']
    assert [a['to_square']['file'],a['to_square']['rank']]==wire['to']
    assert a['promotion_target_id']==wire['promotion_target_id']
    policy=q['policy'] if study=='resource' else ('pvs_on' if q['on'] else 'pvs_off')
    common[(digest(root['RuleSet']),digest(r))].append(dict(study=study,game=g['game_id'],case=g['case_id'],family=root['family'],policy=policy,action=wire,depth=d['completed_depth'],score=d['score'],termination=d['termination_reason'],nodes=d['nodes']+d['qnodes'],wall=q.get('choose_wall_seconds',q.get('outer_seconds')),timing_eligible=q['timing_eligible']))
    f['query_reasons'][study+':'+d['termination_reason']]+=1
    f['depth64']+=d['completed_depth']==64
    if i==0:f['initial_choices'].setdefault(g['case_id'],[]).append(dict(study=study,policy=policy,action=wire,depth=d['completed_depth'],score=d['score'],termination=d['termination_reason']))
   result=g['Core_terminal'];winner=result['winner'];seat=g.get('long_seat',g.get('on_seat'))
   f['games'].append(dict(study=study,id=g['game_id'],case=g['case_id'],terminal=result,policy_seat=seat,net=0 if winner is None else (1 if winner==seat else -1),timing_eligible=g['timing_eligible'],queries=len(g['queries'])))
 paired_paths=[]
 for study in ("resource","pvs"):
  gs=load(sources[study])
  for cid in roots:
   pair=[g for g in gs if g["case_id"]==cid];assert len(pair)==2
   a,b=pair;x=a["final_record"]["actions"];y=b["final_record"]["actions"];k=0
   while k<min(len(x),len(y)) and x[k]==y[k]:k+=1
   initial=len(a["initial_record"]["actions"])
   paired_paths.append(dict(study=study,case=cid,family=roots[cid]["family"],first_divergent_absolute_ply=k if k<min(len(x),len(y)) else None,root_actions_differ=x[initial]!=y[initial],terminals=[a["Core_terminal"],b["Core_terminal"]],same_full_prefix_record_sha256=digest(dict(a["initial_record"],actions=x[:k])),limitation="Budget/PVSpolicy trajectories;not isolated-action counterfactual proof;warmTT contextdiffers."))
 rows=[]
 for (rule,history),obs in common.items():
  if len({o['study'] for o in obs})>1:
   rows.append(dict(rule_sha256=rule,record_sha256=history,observations=obs,distinct_actions=len({digest(o['action']) for o in obs})))
 for family,f in families.items():
  f['query_reasons']=dict(f['query_reasons'])
  f['resource_net']=sum(g['net'] for g in f['games'] if g['study']=='resource')
  f['resource_decisive']=sum(g['terminal']['winner'] is not None for g in f['games'] if g['study']=='resource')
  f['pvs_decisive']=sum(g['terminal']['winner'] is not None for g in f['games'] if g['study']=='pvs')
  f['root_action_diversity']={c:len({digest(q['action']) for q in qs}) for c,qs in f['initial_choices'].items()}
 out=dict(schema=1,new_Player=0,new_Core=0,new_games=0,new_solver=0,source_files={k:dict(path=p.as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for k,p in sources.items()},families=dict(families),cross_study_full_history_rows=rows,paired_path_divergences=paired_paths,summary=dict(families=len(families),roots=len(roots),shared_complete_histories=len(rows),shared_histories_action_changed=sum(r['distinct_actions']>1 for r in rows),resource_decisive_families=sum(f['resource_decisive']>0 for f in families.values()),root_action_diverse_families=sum(any(n>1 for n in f['root_action_diversity'].values()) for f in families.values()),all_original_queries=sum(sum(f['query_reasons'].values()) for f in families.values())),limitations='Data-only schema/action/history/hash join; does not rerun Core/PVs/search or prove individual-action WDL. Controllers/builds/time policies differ by study; within-game warm TT contexts not equivalent merely from identical records. Existing exposed families are not heldout.')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run()
 from scripts.research_record import write_record
 write_record(a.output,r);print(json.dumps(r['summary'],sort_keys=True))
