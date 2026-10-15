"""Complete fixed-depth material reference for exposed unit-action differences.

This is not WDL or an oracle for Native qsearch/extensions. One positive unit
suffices: finite material scores scale, infinities/zero terminal values do not
change order. Exact root action ties and complete-depth costs are reported.
"""
from pathlib import Path
from collections import defaultdict
import json,hashlib,time,math,sys
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from scripts.generic_win_proof import _ordered,_Budget,_Interrupted,_same_state
from scripts.generic_proof_rnb_bridge import uci
from scripts.generic_session_native_material import _load_transport
OUT=Path('results/dev_aux/task1873')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def freeze():
 from generic_chess.session.serialization import serialize_game_record
 law=json.loads(Path('results/dev_aux/task1872/feasibility.json').read_text());assert law['status']=='FULL_32_INPUTS';c=compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task1872/rules.json').read_text()));states=[];cases=[]
 for item in law['roots'][:16]:
  assert item['phase']=='TRAIN';session=GameSession(c,item['setup']);states.append(dict(index=len(states),family=item['family'],record=json.loads(serialize_game_record(session.to_record())),state_sha=hashlib.sha256(repr(session.state).encode()).hexdigest()))
  for ratio in (.5,1.,2.):cases.append(dict(case=len(cases),state=item['family'],ratio=ratio,kind='NEW_CONTACT_TRAIN_ONLY',native=[]))
 write('inputs.json',dict(rules='results/dev_aux/task1872/rules.json',states=states))
 plan=dict(status='FROZEN_BEFORE_CONTACT_REFERENCE',cases=cases,expected=48,depth=5,base_N=720,node_cap_each=250000,seconds_each=10.,seconds_cap=120,expected_seconds=20,source_sha={p:sha(p) for p in [str(Path(__file__).relative_to(Path.cwd())),'generic_chess/core/search_runtime.py','scripts/generic_win_proof.py','results/dev_aux/task1872/rules.json','results/dev_aux/task1872/feasibility.json','results/dev_aux/task1873/inputs.json']},question='Does symmetric input-only R/N legalcapture filter increase finite-material choice conflicts on its TRAIN inputs before any W-L pilot?',scope='Onlyfirst16newTRAIN roots x3fixedratios. No DEVfiniteproxy/WDL, Native, games, pricefit or rootselection by result. All32previouslygeneratedinputs retained unchanged. Compare old16TRAINfreshroot finiteobjective references already paid. This isnot proof of denser actualW-L or cheapmate; new W-L experiment still mustbe separately frozen.',cost_decision='Full oldcommon panel has only3/64finiteobjective conflicts; pureinput contact filter produced32newdistinctroots in1368draws/.05s.48smallTRAIN references test this one mechanism before anygamecost. Expected20s hard120s, no extension or filterrelaxation.')
 write('reference_plan.json',plan);print(json.dumps(dict(cases=48,hard_seconds=120)))

def run():
 plan=json.loads((OUT/'reference_plan.json').read_text());assert all(sha(p)==v for p,v in plan['source_sha'].items());base=json.loads(Path('results/dev_aux/task1873/inputs.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(base['rules']).read_text()));t=_load_transport();beg=time.perf_counter();deadline=beg+plan['seconds_cap'];rows=[];status='COMPLETE'
 with (OUT/'roots.jsonl').open('x',encoding='utf-8') as f:
  for spec in plan['cases']:
   if time.perf_counter()>=deadline:status='GLOBAL_CAP';break
   t.stop_check(Path.cwd());state=base['states'][spec['state']];s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])));root=s.state;rt=SearchPathRuntime.from_state(root,c);rootkey=rt.search_key();root_history=repr(rt.history);target=root.position.side_to_move;price=int(720*spec['ratio']);b=_Budget(plan['node_cap_each'],min(plan['seconds_each'],deadline-time.perf_counter()),None,time.perf_counter);scores=[];complete=True;cause='depth_complete'
   def ab(depth,alpha,beta):
    b.visit();terminal=rt.terminal_status
    if terminal.status is not TerminalStatus.ONGOING:return 0 if terminal.winner is None else (math.inf if terminal.winner==target else -math.inf)
    if depth==0:return sum((1 if p.owner==target else -1)*({'R':price,'N':720}.get(p.current_type_id,0)) for p in rt.position.board if p is not None)
    maximizing=rt.position.side_to_move==target;value=-math.inf if maximizing else math.inf
    for a in _ordered(rt.legal_actions(checkpoint=b.poll)):
     rt.push(a,checkpoint=b.poll)
     try:score=ab(depth-1,alpha,beta)
     finally:rt.pop()
     if maximizing:value=max(value,score);alpha=max(alpha,score)
     else:value=min(value,score);beta=min(beta,score)
     if alpha>=beta:break
    return value
   try:
    for action in _ordered(rt.legal_actions(checkpoint=b.poll)):
     rt.push(action,checkpoint=b.poll)
     try:value=ab(plan['depth']-1,-math.inf,math.inf)
     finally:rt.pop()
     scores.append(dict(move=uci(action),value='WIN_INFINITY' if value==math.inf else 'LOSS_INFINITY' if value==-math.inf else value))
   except _Interrupted:complete=False;cause=b.reason
   rt.assert_balanced()
   assert rt.search_key()==rootkey and repr(rt.history)==root_history and _same_state(rt.position,root.position) and rt.ply_count==root.ply_count and _same_state(s.state,root)
   row=dict(**spec,complete=complete,cause=cause,nodes=b.nodes,seconds=b.elapsed(),action_scores=scores,state_sha=hashlib.sha256(repr(root).encode()).hexdigest())
   rows.append(row);f.write(json.dumps(row)+'\n');f.flush();print(json.dumps(dict(done=len(rows),complete=complete,nodes=b.nodes,seconds=round(b.elapsed(),3),wall=round(time.perf_counter()-beg,3))),flush=True)
 write('completion.json',dict(status=status,completed=len(rows),expected=len(plan['cases']),complete_roots=sum(r['complete'] for r in rows),seconds=time.perf_counter()-beg,source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
