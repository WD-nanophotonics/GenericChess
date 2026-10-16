"""Paired conditional horizon sensitivity; original prefix labels unchanged."""
from pathlib import Path
from collections import Counter
import json,hashlib,itertools
from results.dev_aux.task2006.physical_audit import audit,read,lines
from results.dev_aux.task1998.audit import ci
ROOT=Path('results/dev_aux/task2005');OUT=Path('results/dev_aux/task2006')
def run():
 p=read(ROOT/'run-plan.json');physical=audit(ROOT);rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');parents={x['slot']:x for x in lines(p['parent_games'])}
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 if not physical['full_study_complete']:
  partial=dict(status='PARTIAL_CONDITIONAL_H48_RETAINED',physical=physical,source_unchanged=True,scope='Original1200cap retained; no fullcohortcontrast frommissing/censoredcases.')
  with(OUT/'result.json').open('x')as f:json.dump(partial,f,indent=2)
  print(json.dumps(partial));return
 selected=read('results/dev_aux/task1997/FULL-lock-before-dev.json')['selected_R'];prices=sorted({720,selected})
 cells={(x['family'],x['candidate_side'],x['R'],x['opponent_R']):x for x in rows};assert len(cells)==len(rows) and set(cells)==set(itertools.product(range(32,48),(0,1),prices,(360,720,1440,2880)))
 oldcells={key:parents[g['parent_slot']]for key,g in cells.items()};transitions=Counter()
 for g in rows:
  old=parents[g['parent_slot']];transitions[old['outcome']+'->'+g['outcome']]+=1
  if old['outcome']!='UNKNOWN':assert old['record']==g['record'] and old['outcome']==g['outcome'] and g['moves']==0
  else:assert old['reason']=='H_UNKNOWN' and g['prefix_actions']==24
 ds=lambda table:[sum(table[f,s,selected,o]['finite_event_score']-table[f,s,720,o]['finite_event_score']for s in (0,1)for o in (360,720,1440,2880))/8 for f in range(32,48)]
 before,after=ds(oldcells),ds(cells);interaction=[a-b for a,b in zip(after,before)]
 unresolved=0 if selected==720 else sum((cells[f,s,selected,o]['outcome']=='UNKNOWN')+(cells[f,s,720,o]['outcome']=='UNKNOWN')for f in range(32,48)for s in (0,1)for o in (360,720,1440,2880))/128
 profile=None;cleared=False;intents=0
 for e in lines(ROOT/'run/transport.jsonl'):
  if e['event']=='PROFILE':
   profile=e['values'];r,n,b,pawn=profile;assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in e['ack'];cleared=False
  elif e['event']=='CLEAR':assert profile==e['values'];cleared=True
  elif e['event']=='INTENT':assert profile==e['R']and cleared;cleared=False;intents+=1
 assert intents==physical['actual_native']
 result=dict(status='PASS_PREDECLARED_CONDITIONAL_H48',physical=physical,selected_R=selected,ratio=selected/720,parent_cases=len(rows),continued_unknown_parents=sum(x['parent_outcome']=='UNKNOWN'for x in rows),inherited_terminal_cases=sum(x['inherited_terminal']for x in rows),new_continuation_moves=len(moves),new_Native_queries=physical['actual_native'],outcome_transitions=dict(transitions),H24_price_delta=dict(mean=sum(before)/16,bootstrap16family_interval=ci(before)),H48conditional_price_delta=dict(mean=sum(after)/16,bootstrap16family_interval=ci(after),family_deltas=after,UNKNOWN_WDL_bounds=[max(-2,sum(after)/16-unresolved),min(2,sum(after)/16+unresolved)]),horizon_interaction=dict(mean=sum(interaction)/16,bootstrap16family_interval=ci(interaction)),outcomes={r:dict(Counter(x['outcome']for x in rows if x['R']==r))for r in prices},recorded_case_seconds=sum(x['seconds']for x in rows),scope='Predeclared beforeparentDEV. Same16families/UNIT+TRAINonlyFULL, ALLcases accounted; terminalparents inheritedauthentically, UNKNOWNprefixes continuedunderdefinednewH48policy. ActualprefixNative/PNwork reusednotcountednew; freshcoldbanks/actualNativeclears, strictlylongerrecordkeys/noactiveproof. NOT independentlysampledvalidation or identicalfromrootH48counterfactual; finiteeventW-LnotunlimitedWDL/quantity labels. Parent3300cap/resultsunchanged; continuation1200cap unchanged.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in ('physical','scope')}))
if __name__=='__main__':run()
