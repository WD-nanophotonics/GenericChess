"""Independent public GameSession/literal-actor tree and rational-region audit."""
from pathlib import Path
from fractions import Fraction
from collections import Counter,defaultdict
import json,time,math,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,uci
OUT=Path('results/dev_aux/task2119')
def run():
 start=time.perf_counter();deadline=start+600;cases=json.loads(Path('results/dev_aux/task2117/cases-frozen-before-labels.json').read_text())['cases'];queries=[json.loads(x)for x in Path('results/dev_aux/task2117/queries.jsonl').read_text().splitlines()];roots=json.loads(Path('results/dev_aux/task2105/inputs.json').read_text())['roots'];compiled={};actor=RoyalActor(4);nodes=edges=terminals=leaves=0;frontiers=0;groups=defaultdict(Counter);witness=[];all_lines=set();joint={};firstjoint={}
 def check(t,s,target,left,lines):
  nonlocal nodes,edges,terminals,leaves,frontiers
  if time.perf_counter()>=deadline:raise TimeoutError('original600cap')
  nodes+=1;raw=actor_state(s.state)
  if s.result.status is not SessionStatus.ONGOING:
   expected=0 if s.result.winner is None else math.inf if s.result.winner==target else-math.inf;assert t==dict(terminal=expected);terminals+=1;return
  if not left:
   expected=tuple(sum((1 if int(ch.islower())==target else-1)for ch in raw[:-1]if ch.upper()==tid)for tid in('N','B'));assert t==dict(coeff=list(expected));lines.add(expected);leaves+=1;return
  legal=sorted(s.legal_actions(),key=lambda a:json.dumps(action_to_dict(a),sort_keys=True));literal=dict(actor.moves(raw));assert set(literal)=={uci(a)for a in legal};frontiers+=1;assert t['max']==(s.state.position.side_to_move==target)and [x[0]for x in t['edges']]==[uci(a)for a in legal]
  for (name,childtree),a in zip(t['edges'],legal):
   child=GameSession.replay(s.compiled,s.to_record());child.submit(a);assert actor_state(child.state)==literal[name];edges+=1;check(childtree,child,target,left-1,lines)
 def score(t,r):
  if 'terminal'in t:return t['terminal']
  if 'coeff'in t:return t['coeff'][0]*r+t['coeff'][1]
  return (max if t['max']else min)(score(child,r)for _,child in t['edges'])
 for line,row in zip(Path('results/dev_aux/task2117/trees.jsonl').open(),queries):
  tr=json.loads(line);assert tr['case']==row['case']and tr['depth']==row['depth'];case=cases[row['case']];fam=case['family']
  if fam not in compiled:compiled[fam]=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[fam]['rules']).read_text(encoding='utf-8')))
  s=GameSession.replay(compiled[fam],deserialize_game_record(json.dumps(case['record'])));lines=set();before=nodes;check(tr['tree'],s,row['target'],row['depth'],lines);assert nodes-before==row['nodes'];all_lines.update(lines);points=set()
  for n,b in lines:
   for m,c in lines:
    if n!=m:
     x=Fraction(c-b,n-m)
     if x>0:points.add(x)
  assert sorted(points)==[Fraction(x)for x in row['breakpoints']]
  # Crossing-free open intervals preserve every pairwise affine ordering.
  last=Fraction(0);reps=[]
  for b in sorted(points):reps.extend([(last+b)/2,b]);last=b
  reps.append(last+1);assert reps==[Fraction(x['ratio'])for x in row['regions']]
  for rr,r in zip(row['regions'],reps):
   vv=[(name,score(t,r))for name,t in tr['tree']['edges']];best=max(v for _,v in vv);aa=[a for a,v in vv if v==best];assert aa==rr['top_actions']and aa[0]==rr['first_action'];regret=[max(row['child_values'].values())-row['child_values'][a]for a in aa];assert min(regret)==rr['optimistic_regret']and max(regret)==rr['pessimistic_regret']
  k=case['kind']+'_depth'+str(row['depth']);g=groups[k];g['states']+=1;g['nonflat']+=row['nonflat_child_position_WDL'];g['no_ratio_first_choice_optimal']+=not any(x['optimistic_regret']==0 and row['child_values'][x['first_action']]==max(row['child_values'].values())for x in row['regions']);g['some_ratio_changes_first_action']+=row['distinct_first_actions']>1
  if row['kind']=='INITIAL'and row['no_ratio_all_top_optimal']:witness.append(dict(case=row['case'],family=fam,depth=row['depth'],child_values=row['child_values'],all_region_top_sets=[x['top_actions']for x in row['regions']]))
  if row['case']%8==0:print(json.dumps(dict(query_case=row['case'],depth=row['depth'],nodes=nodes,seconds=time.perf_counter()-start)),flush=True)
 assert nodes==14180 and len(queries)==168
 result=dict(status='PASS_ALL_PUBLIC_SESSION_AND_LITERAL_FRONTIER_AFFINE_REGIONS',cases=len(cases),queries=len(queries),nodes=nodes,edges=edges,frontiers=frontiers,terminal_leaves=terminals,ongoing_material_leaves=leaves,groups={k:dict(v)for k,v in groups.items()},seconds=time.perf_counter()-start,scope='Exactfinite-depthtree; allpositivepricespartitionedbecauseonlyleafaffinecrossingscanchange min/max ordering. TerminalInfinitytokensarePythonJSONnonstandard in originaltrees; semanticallyverified, retainedoriginalbytes; publishedportablecopywilluseexplicitstrings. No training, no hidden DEV, no arbitraryhistoryWDLclaim.')
 (OUT/'witnesses.json').write_text(json.dumps(witness,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
