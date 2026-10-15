"""Separate physical-tail diagnostic; never relabel any frozen H16 game."""
import ast,json,time
from pathlib import Path
from scripts.generic_proof_native_study import mod
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state,uci
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_win_proof import prove_win,StrategyCursor,PROVEN_WIN
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
p=Path('results/dev_aux/task1770');p.mkdir(exist_ok=False);cases=[]
for task in (1763,1765):
 rows=[json.loads(x) for x in Path(f'results/dev_aux/task{task}/run/games.jsonl').read_text().splitlines()]
 for i,row in enumerate(rows):
  if row['payoff'] is None and any(z['decision']['source']=='PROOF' for z in row['trajectory']):cases.append(dict(source_task=task,row=i))
(p/'plan.json').write_text(json.dumps(dict(cases=cases,purpose='New policy: finish already-proved strategy tails after oldH16 cutoff. Original H16 labels remain UNKNOWN; no training/validation score replacement.',seconds_cap=120,max_new_native_go_per_source=20),indent=2))
D=mod('TAIL_DRIVER54','results/dev_aux/task1720/driver.py')
source=ast.parse(Path('scripts/generic_proof_native_study.py').read_text(encoding='utf-8-sig'));run=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='run');cls=next(n for n in run.body if isinstance(n,ast.ClassDef) and n.name=='TimedDriver');env=dict(D=D,time=time);exec(compile(ast.Module(body=[cls],type_ignores=[]),'frozen_timed_driver_class','exec'),env);Driver=env['TimedDriver']
results=[];c=compile_rnb();start=time.perf_counter()
for task in (1763,1765):
 plan=json.loads(Path(f'results/dev_aux/task{task}/plan.json').read_text());rows=[json.loads(x) for x in Path(f'results/dev_aux/task{task}/run/games.jsonl').read_text().splitlines()];plan.update(seconds_cap=120,max_go=20)
 d=Driver(plan,p/f'run{task}')
 try:
  d.start_engine()
  for case in [x for x in cases if x['source_task']==task]:
   row=rows[case['row']];f=next(f for f in plan['families'] if f['family']==row['family']);s=from_actor(c,f['roots'][row['color']]);cursor=None;reconstruction=None
   for step in row['trajectory']:
    if cursor is None and step['decision']['source']=='PROOF':
     cap=plan['candidate_nodes'] if s.position.side_to_move==row['color'] else next(o['nodes'] for o in plan['opponents'] if o['id']==row['opponent'])
     r=prove_win(c,s,max_nodes=cap//4,seconds=plan['step_seconds']/4,max_depth=64)
     assert r.status==PROVEN_WIN
     cursor=StrategyCursor(c,r.certificate,max_nodes=cap//4,seconds=plan['step_seconds']/4);reconstruction=dict(nodes=r.nodes,seconds=r.seconds,verification=cursor.receipt)
    a=next(a for a in legal_actions(s,c) if uci(a)==step['decision']['action'])
    if cursor is not None:cursor.advance(s,a)
    s=apply_action(s,a,c)
   assert cursor is not None and actor_state(s)==tuple(row['end']) and not s.terminal_status.is_terminal
   owner=cursor.certificate.target;rank=cursor.node.rank;extra=[];before=d.queries
   def normal(state,nodes,seconds,cancel):
    pp=row['price'] if state.position.side_to_move==row['color'] else plan['prices'][plan.get('baseline_index',0)]
    move,used=d.choose_timed(actor_state(state),pp,nodes,seconds);a=next(a for a in legal_actions(state,c) if uci(a)==move);return a,used
   opponent=ProofMaterialPlayer(c,None,proof_enabled=True,normal_search=normal)
   for ply in range(rank):
    if s.terminal_status.is_terminal:break
    if s.position.side_to_move==owner:a=cursor.choose(s);kind='EXISTING_PROOF_TAIL'
    else:
     op=next(o for o in plan['opponents'] if o['id']==row['opponent']);cap=plan['candidate_nodes'] if s.position.side_to_move==row['color'] else op['nodes']
     z=opponent.choose(s,max_nodes=cap,seconds=plan['step_seconds']);a=z.action;kind=z.source
    assert a is not None;oldrank=cursor.node.rank;extra.append(dict(state=actor_state(s),move=uci(a),source=kind,rank=oldrank));cursor.advance(s,a);s=apply_action(s,a,c);assert cursor.node.rank<oldrank
   assert s.terminal_status.is_terminal and s.terminal_status.winner==owner
   results.append(dict(**case,old_label='UNKNOWN_H16',recovered_remaining_rank=rank,extra_moves=extra,actual_new_native_go=d.queries-before,terminal=s.terminal_status.status.value,winner=owner,reconstruction_only=reconstruction))
 finally:d.close()
out=dict(status='PASS_PHYSICAL_TAIL_CONVERSION',cases=len(results),actual_new_native_go=sum(r['actual_new_native_go'] for r in results),seconds=time.perf_counter()-start,results=results,scope='Separate continuation diagnostic. OriginalH16 outcomes and all training/DEV scores unchanged.')
(p/'result.json').write_text(json.dumps(out,indent=2));print({k:v for k,v in out.items() if k!='results'})
