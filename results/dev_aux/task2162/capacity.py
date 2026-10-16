"""Frozen TRAIN completed-depth capacity; no games, fit or DEV selection."""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import json,time,hashlib,math
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from generic_chess.session.session import GameSession
from scripts.generic_win_proof import _ordered
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2117.capacity import regions
from results.dev_aux.task2155.sample import profile
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2162')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def partition(tree):
 lines={(0,0)}
 def collect(t):
  if 'coeff'in t:lines.add((t['coeff'][1],t['coeff'][0]))
  for _,child in t.get('edges',[]):collect(child)
 collect(tree);points,reps=regions(lines)
 return [str(p)for p in points],profile(tree,reps)
def run():
 if(OUT/'started.json').exists():raise RuntimeError('closed cap neverrestart')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text(encoding='utf-8'));assert digest(p['inputs'])==p['inputs_sha'];roots=json.loads(Path(p['inputs']).read_text(encoding='utf-8'))['roots'][:32];stop=EvidenceStopReader(Path.cwd());deadline=start+p['one_cap_seconds']
 (OUT/'started.json').write_text(json.dumps(dict(started_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),source_sha=digest(__file__),plan_sha=digest(OUT/'plan.json'))),encoding='utf-8')
 def check():
  stop()
  if time.perf_counter()>=deadline:raise TimeoutError('original300cap')
 load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2093','results/dev_aux/task2094','results/dev_aux/task2095');load=time.perf_counter()-load;rows=[];total=0;status='COMPLETE'
 with(OUT/'trees.jsonl').open('x',encoding='utf-8')as tf,(OUT/'queries.jsonl').open('x',encoding='utf-8')as qf:
  try:
   for r in roots:
    check();c=compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text(encoding='utf-8')));s=GameSession(c);assert c.ruleset_fingerprint==r['fingerprint'];assert teacher.label(s).quality=='EXACT_CANONICAL_FRESH_ROOT';rt=SearchPathRuntime.from_state(s.state,c);q={e['action']:-e['child_value']for e in teacher.rows[teacher.key(actor_state(s.state))]['actions']}
    for depth in p['depths']:
     visits=0
     def tree(left):
      nonlocal visits,total
      check();visits+=1;total+=1;t=rt.terminal_status
      if t.status is not TerminalStatus.ONGOING:return dict(terminal='DRAW'if t.winner is None else'WIN'if t.winner==0 else'LOSS')
      if not left:
       coeff=[0,0]
       for piece in rt.position.board:
        if piece is not None and piece.current_type_id!='K':coeff[piece.current_type_id=='N']+=1 if piece.owner==0 else-1
       return dict(coeff=coeff)
      edges=[]
      for a in _ordered(rt.legal_actions()):
       rt.push(a)
       try:child=tree(left-1)
       finally:rt.pop()
       edges.append((uci(a),child))
      assert edges;return dict(own=rt.position.side_to_move==0,edges=edges)
     began=time.perf_counter();tr=tree(depth);rt.assert_balanced();points,rs=partition(tr);best=max(q.values())
     for x in rs:
      regrets=[best-q[a]for a in x['top_actions']];x.update(any_top_position_optimal=min(regrets)==0,all_top_position_optimal=max(regrets)==0,first_position_value=q[x['first_action']],first_position_optimal=q[x['first_action']]==best)
     row=dict(family=r['family'],depth=depth,nodes=visits,seconds=time.perf_counter()-began,child_position_values=q,root_position_label=teacher.label(s).value,nonflat_child_WDL=len(set(q.values()))>1,breakpoints=points,regions=rs,fixed_cells=profile(tr,list(map(Fraction,p['ratios']))),no_price_any_top=not any(x['any_top_position_optimal']for x in rs),no_price_all_top=not any(x['all_top_position_optimal']for x in rs),no_price_first=not any(x['first_position_optimal']for x in rs),price_changes_first=len({x['first_action']for x in rs})>1)
     tf.write(json.dumps(dict(family=r['family'],depth=depth,tree=tr))+'\n');tf.flush();qf.write(json.dumps(row)+'\n');qf.flush();rows.append(row)
    print(json.dumps(dict(family=r['family'],queries=len(rows),seconds=time.perf_counter()-start)),flush=True)
  except TimeoutError:status='CAP_PARTIAL'
 groups={}
 for d in p['depths']:
  rr=[r for r in rows if r['depth']==d];groups[str(d)]=dict(cases=len(rr),nodes=sum(r['nodes']for r in rr),nonflat=sum(r['nonflat_child_WDL']for r in rr),**{k:sum(r[k]for r in rr)for k in('no_price_any_top','no_price_all_top','no_price_first','price_changes_first')},baseline1_first_position_optimal=sum(r['child_position_values'][next(x['first_action']for x in r['fixed_cells']if x['ratio']=='1')]==max(r['child_position_values'].values())for r in rr))
 out=dict(status=status,queries=len(rows),nodes=total,teacher_load_seconds=load,seconds=time.perf_counter()-start,groups=groups,new_game_or_fit_or_DEV=0,scope=p['teacher']);(OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
