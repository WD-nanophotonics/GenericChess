"""Literal complete-history reader for the finite two-type forward experiment."""
from __future__ import annotations
from pathlib import Path
from collections import Counter
import json,time,argparse
from scripts import leaper_design as L
from tools.local_agent.common import write_json

def qualify_game(world,row,reg):
 assert row['status']=='CLOSED';slot=row['slot'];root=world['roots'][slot['root']];c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(root['record'])))
 assert L.record_value(s.to_record())==row['initial_record'];assert row['nodes_limit']==reg['nodes'];counts=Counter();depths=Counter();stops=Counter();captures=[];query_seconds=0
 for q in row['queries']:
  assert not s.state.terminal_status.is_terminal and q['actor']==s.state.position.side_to_move and q['root_ply']==s.state.ply_count and q['state_sha256']==L.state_sha(s.state)
  legal=s.legal_actions();assert len(legal)==q['legal_count'];d=q['decision'];assert d['action']==q['action'];a=L.match_action(s,q['action']);assert d['qnodes']==0 and d['nodes']+d['qnodes']<=reg['nodes'];assert d['runtime_depth_balanced'] and d['runtime_pushes']==d['runtime_pops'];assert d['native_legality_operational_failures']==0
  if d['termination_reason']=='root_immediate_win':
   assert d['completed_depth']==0 and d['result_ordinary_qdepth']is None
   z=L.GameSession.replay(c,s.to_record());z.submit(a);assert z.result.winner==q['actor'] and z.state.terminal_status.is_terminal
  else:assert d['result_ordinary_qdepth']==0
  pv=L.GameSession.replay(c,s.to_record())
  for raw in d['principal_variation']:pv.submit(L.match_action(pv,raw));counts['PV_plies']+=1
  before=[(p.owner,p.current_type_id)for p in s.state.position.board if p is not None];s.submit(a);after=[(p.owner,p.current_type_id)for p in s.state.position.board if p is not None]
  if len(after)<len(before):captures.append(dict(ply=s.state.ply_count,removed=list((Counter(before)-Counter(after)).elements())))
  counts['Player_queries']+=1
  for k in ('nodes','qnodes','native_legality_calls','native_legality_fallbacks','runtime_pushes','runtime_pops'):counts[k]+=d[k]
  depths[str(d['completed_depth'])]+=1;stops[d['termination_reason']]+=1;query_seconds+=q['seconds']
 assert L.record_value(s.to_record())==row['final_record'] and L.record_value(s.state)==row['final_state'] and L.record_value(s.result)==row['terminal'];assert row['value']==L.outcome_value(s.result,0,row['censor']);assert row['seconds']>=query_seconds
 return dict(counts=dict(counts),depths=dict(depths),stops=dict(stops),captures=captures,plies=s.state.ply_count,value=row['value'],terminal=row['terminal']['status'],seconds=row['seconds'],final_record_sha256=L.state_sha(row['final_record']))
def analyze(world,reg,results,read_row):
 from scripts.leaper_two_type_forward import profiles,RATIOS
 c=L.compile_rule(L.ruleset_from_dict(world['rule']))
 assert world['profiles']=={label:list(profiles(c,b)[1:])for label,b in RATIOS.items()},'declared complete profiles differ from the executed constructor'
 assert len(results['slots'])==len(reg['slots']);counts=Counter();rows=[]
 for i,(expected,actual)in enumerate(zip(reg['slots'],results['slots'])):
  assert all(actual[k]==v for k,v in expected.items())
  if actual['status']!='finished':continue
  row=read_row(i);assert row['slot']==expected;summary=qualify_game(world,row,reg);assert actual['value']==summary['value'];counts.update(summary['counts']);rows.append(dict(slot=expected,**summary))
 assert results['missing']==[i for i,x in enumerate(results['slots'])if x['status']!='finished'or x['value']is None]
 paired=[]
 for root in range(len(world['roots'])):
  entries={r['slot']['policy']:r for r in rows if r['slot']['root']==root};base=entries.get('B1000')
  if base:
   for p,r in entries.items():
    paired.append(dict(root=root,policy=p,value=r['value'],baseline_value=base['value'],difference=None if r['value']is None or base['value']is None else r['value']-base['value'],identical_final_record=r['final_record_sha256']==base['final_record_sha256']))
 return dict(status='PASS',games=len(rows),missing=results['missing'],counts=dict(counts),rows=rows,paired=paired,scope='One fixed rule/four prospective layouts, seven declared relative leaf prices, deterministic matched defender; no iid game CI, oracle labels, learner, or generic strength claim. Source/data reader reuses Core, not independent engine.')
def qualify(inputs,regfile,d,out):
 tick=time.perf_counter();w=L.load(inputs);reg=L.load(regfile);assert L.sha(inputs)==reg['input_sha256'];r=analyze(w,reg,L.load(d/'results.json'),lambda i:L.load(d/f'game-{i:03d}.json'));r['seconds']=time.perf_counter()-tick;write_json(out,r);print('QUALIFIED',r['games'],r['missing'],r['counts'],r['seconds'],flush=True);return r
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--registration',type=Path,required=True);ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();qualify(a.input,a.registration,a.directory,a.output)
