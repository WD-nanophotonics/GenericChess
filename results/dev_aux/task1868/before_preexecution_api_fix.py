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
OUT=Path('results/dev_aux/task1868')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(n,d):
 with (OUT/n).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2)
def freeze():
 rows=[json.loads(x) for x in Path('results/dev_aux/task1866/queries.jsonl').read_text().splitlines() if json.loads(x)['control']=='depth5'];groups=defaultdict(list)
 for row in rows:groups[row['state'],row['profile']['ratio']].append(row)
 changed=sorted(k for k,xs in groups.items() if len({x['move'] for x in xs})>1);unchanged=sorted(k for k,xs in groups.items() if len({x['move'] for x in xs})==1)[:len(changed)];cases=[]
 for kind,keys in [('CHANGED_UNITS',changed),('UNCHANGED_ORDINAL_CONTROL',unchanged)]:
  for key in keys:cases.append(dict(case=len(cases),state=key[0],ratio=key[1],kind=kind,native=[{k:r[k] for k in ('profile','move','completed_depth','score_kind','score_value')} for r in groups[key]]))
 plan=dict(status='FROZEN_BEFORE_REFERENCE',cases=cases,expected=len(cases),depth=5,base_N=720,node_cap_each=2000000,seconds_each=60.,seconds_cap=1800,expected_seconds=300,source_sha={p:sha(p) for p in [__file__,'generic_chess/core/search_runtime.py','scripts/generic_win_proof.py','results/dev_aux/task1866/plan.json','results/dev_aux/task1866/queries.jsonl']},question='Are unit-dependent Native depth5 choices tied under an independent complete depth5 material reference, or do they attain different values under that scoped objective?',scope='All14exposed changed depth5 quartets + first14ordinal unchanged controls, not an unexposed sample. Same fullrules/history, exactdepth5 withoutNativequiescence/extensions; terminalwins infinite/draw0, finiteleaf materialN720 Rratio. Complete allroot action scores or explicit UNKNOWNpartial, no result-driven extension. No mate/WDLlabel, heuristic-causes/strength claim, new games, pricefit or bestunitselection.',cost_decision='2304Nativequeries show14/192depth5quartets change actions atsame reporteddepth. Independent finiteobjective tie classification changes whether these are merely tie-breaking vs changing scopedmaterialdecision quality.28cases at60s/2M each within30min hard cap, expected5min; allchanged plus equalordinal controls, no massunaffected cohort. Preserve incompleteactions/roots.')
 write('plan.json',plan);print(json.dumps(dict(cases=len(cases),hard_seconds=1800)))
def run():
 plan=json.loads((OUT/'plan.json').read_text());assert all(sha(p)==v for p,v in plan['source_sha'].items());base=json.loads(Path('results/dev_aux/task1866/plan.json').read_text());c=compile_ruleset_for_execution(deserialize_ruleset(Path(base['rules']).read_text()));t=_load_transport();beg=time.perf_counter();deadline=beg+plan['seconds_cap'];rows=[];status='COMPLETE'
 with (OUT/'roots.jsonl').open('x',encoding='utf-8') as f:
  for spec in plan['cases']:
   if time.perf_counter()>=deadline:status='GLOBAL_CAP';break
   t.stop_check(Path.cwd());state=base['states'][spec['state']];s=GameSession.replay(c,deserialize_game_record(json.dumps(state['record'])));root=s.state;rt=SearchPathRuntime.from_state(root,c);target=root.position.side_to_move;price=int(720*spec['ratio']);b=_Budget(plan['node_cap_each'],min(plan['seconds_each'],deadline-time.perf_counter()),None,time.perf_counter);scores=[];complete=True;cause='depth_complete'
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
   assert _same_state(rt.to_state(),root) and _same_state(s.state,root)
   row=dict(**spec,complete=complete,cause=cause,nodes=b.nodes,seconds=b.elapsed(),action_scores=scores,state_sha=hashlib.sha256(repr(root).encode()).hexdigest())
   rows.append(row);f.write(json.dumps(row)+'\n');f.flush();print(json.dumps(dict(done=len(rows),complete=complete,nodes=b.nodes,seconds=round(b.elapsed(),3),wall=round(time.perf_counter()-beg,3))),flush=True)
 write('completion.json',dict(status=status,completed=len(rows),expected=len(plan['cases']),complete_roots=sum(r['complete'] for r in rows),seconds=time.perf_counter()-beg,source_unchanged=all(sha(p)==v for p,v in plan['source_sha'].items())))
if __name__=='__main__':{'freeze':freeze,'run':run}[sys.argv[1]]()
