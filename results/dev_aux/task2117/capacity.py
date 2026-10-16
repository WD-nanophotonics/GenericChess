"""Exhaustive finite-depth positive-price capacity, not fitting or game strength."""
from pathlib import Path
from fractions import Fraction
from collections import Counter,defaultdict
import json,time,hashlib,math
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,uci
from scripts.generic_win_proof import _ordered
from scripts.generic_session_native_material import _load_transport
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2117')
def coefficients(pos,target):
 return tuple(sum((1 if p.owner==target else-1)for p in pos.board if p is not None and p.current_type_id==tid)for tid in('N','B'))
def regions(lines):
 points=set()
 for n,b in lines:
  for m,c in lines:
   if n!=m:
    r=Fraction(c-b,n-m)
    if r>0:points.add(r)
 points=sorted(points);out=[];last=Fraction(0)
 for p in points:out.extend([(last+p)/2,p]);last=p
 out.append(last+1)
 return points,out

def value(tree,ratio):
 if 'terminal'in tree:return tree['terminal']
 if 'coeff'in tree:return tree['coeff'][0]*ratio+tree['coeff'][1]
 vv=[value(t,ratio)for _,t in tree['edges']]
 return (max if tree['max']else min)(vv)

def run():
 if (OUT/'started.json').exists():raise RuntimeError('frozen cap, never restart')
 start=time.perf_counter();plan=json.loads((OUT/'plan.json').read_text());deadline=start+plan['one_cap_seconds'];(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');stop=_load_transport().stop_check
 def check():
  stop(Path.cwd())
  if time.perf_counter()>=deadline:raise TimeoutError('original1200cap')
 roots=json.loads(Path('results/dev_aux/task2105/inputs.json').read_text())['roots'][:32];compiled={r['family']:compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')))for r in roots};cases=[]
 for r in roots:
  s=GameSession(compiled[r['family']]);cases.append(dict(kind='INITIAL',family=r['family'],record=json.loads(serialize_game_record(s.to_record()))))
 games=[json.loads(x)for x in Path('results/dev_aux/task2105/games.jsonl').read_text().splitlines()];steps=defaultdict(list)
 for line in Path('results/dev_aux/task2105/moves.jsonl').read_text().splitlines():
  x=json.loads(line);steps[x['physical_id']].append(x)
 found=set()
 for g in games:
  if g['phase']!='TRAIN'or g['reused_from']is not None or g['family']in found:continue
  s=GameSession(compiled[g['family']]);record=deserialize_game_record(json.dumps(g['record']))
  for m,a in zip(steps[g['physical_id']],record.actions):
   check();pieces=[p.current_type_id for p in s.state.position.board if p is not None]
   if len(pieces)<=4 and 'B'in pieces and 'N'in pieces and s.state.position.side_to_move==g['candidate_side']and m['source']in('MATERIAL_SEARCH','LEGAL_FALLBACK'):
    cases.append(dict(kind='POSTTRIGGER_B_AND_N',family=g['family'],physical_id=g['physical_id'],source_ply=m['ply'],record=json.loads(serialize_game_record(s.to_record()))));found.add(g['family']);break
   s.submit(a)
 (OUT/'cases-frozen-before-labels.json').write_text(json.dumps(dict(cases=cases,missing_posttrigger_families=sorted(set(range(32))-found)),indent=2),encoding='utf-8');load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-load;receipts=[];nodecount=0;status='COMPLETE'
 with (OUT/'trees.jsonl').open('x',encoding='utf-8')as tf,(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf:
  try:
   for index,case in enumerate(cases):
    c=compiled[case['family']];s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));target=s.state.position.side_to_move;rt=SearchPathRuntime.from_state(s.state,c);legal=_ordered(rt.legal_actions());assert {uci(a)for a in legal}=={uci(a)for a in s.legal_actions()};position=teacher.rows[teacher.key(actor_state(s.state))];q={e['action']:-e['child_value']for e in position['actions']};assert set(q)=={uci(a)for a in legal}
    # For a child that actually ends in DRAW/WIN now, use the actual result.
    actualchild={}
    for a in legal:
     child=GameSession.replay(c,s.to_record());child.submit(a);actualchild[uci(a)]=q[uci(a)]if child.result.status is SessionStatus.ONGOING else 0 if child.result.winner is None else 1 if child.result.winner==target else-1
    for depth in plan['depths']:
     check();lines=set();visits=0
     def tree(left):
      nonlocal nodecount,visits
      check();nodecount+=1;visits+=1;t=rt.terminal_status
      if t.status is not TerminalStatus.ONGOING:return dict(terminal=0 if t.winner is None else math.inf if t.winner==target else-math.inf)
      if not left:
       coeff=coefficients(rt.position,target);lines.add(coeff);return dict(coeff=coeff)
      edges=[]
      for a in _ordered(rt.legal_actions()):
       rt.push(a)
       try:child=tree(left-1)
       finally:rt.pop()
       edges.append((uci(a),child))
      assert edges
      return dict(max=rt.position.side_to_move==target,edges=edges)
     began=time.perf_counter();tr=tree(depth);rt.assert_balanced();points,reps=regions(lines);regionsout=[];allsets=[]
     for r in reps:
      vals=[value(t,r)for _,t in tr['edges']];v=max(vals);best=[a for(a,_),x in zip(tr['edges'],vals)if x==v];allsets.append(tuple(best));regrets=[max(actualchild.values())-actualchild[a]for a in best];regionsout.append(dict(ratio=str(r),top_actions=best,first_action=best[0],any_top_position_optimal=min(regrets)==0,all_top_position_optimal=max(regrets)==0,optimistic_regret=min(regrets),pessimistic_regret=max(regrets)))
     row=dict(case=index,kind=case['kind'],family=case['family'],depth=depth,nodes=visits,seconds=time.perf_counter()-began,pieces=sum(p is not None for p in s.state.position.board),target=target,positional_label=position['label'],nonflat_child_position_WDL=len(set(actualchild.values()))>1,child_values=actualchild,breakpoints=[str(r)for r in points],regions=regionsout,distinct_top_sets=len(set(allsets)),distinct_first_actions=len({v[0]for v in allsets}),no_ratio_any_top_optimal=not any(x['any_top_position_optimal']for x in regionsout),no_ratio_all_top_optimal=not any(x['all_top_position_optimal']for x in regionsout));tf.write(json.dumps(dict(case=index,depth=depth,tree=tr))+'\n');tf.flush();qf.write(json.dumps(row)+'\n');qf.flush();receipts.append(row)
    print(json.dumps(dict(case=index,kind=case['kind'],done_queries=len(receipts),seconds=time.perf_counter()-start)),flush=True)
  except TimeoutError:status='CAP_PARTIAL'
 groups={}
 for kind in('INITIAL','POSTTRIGGER_B_AND_N'):
  for depth in plan['depths']:
   rs=[r for r in receipts if r['kind']==kind and r['depth']==depth];groups[kind+'_depth'+str(depth)]=dict(cases=len(rs),nonflat=sum(r['nonflat_child_position_WDL']for r in rs),price_changes_top_sets=sum(r['distinct_top_sets']>1 for r in rs),price_changes_first_action=sum(r['distinct_first_actions']>1 for r in rs),no_price_any_optimal=sum(r['no_ratio_any_top_optimal']for r in rs),no_price_all_optimal=sum(r['no_ratio_all_top_optimal']for r in rs))
 result=dict(status=status,cases=len(cases),queries=len(receipts),nodes=nodecount,teacher_load_seconds=load,seconds=time.perf_counter()-start,groups=groups,scope=plan['history_scope'],no_training=True,no_DEV_reads=True)
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
