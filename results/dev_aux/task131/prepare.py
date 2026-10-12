import json,random,hashlib,difflib,time
from pathlib import Path
import chess
R=Path.cwd();out=R/'results/dev_aux/task131';out.mkdir(exist_ok=True)
old=R/'results/dev_aux/task129';D=json.loads((old/'controller.json').read_bytes());status=json.loads((old/'status.json').read_bytes());assert not D['completed'] and len(D['calls'])==816 and status['error']=='ValueError: opening terminal; freeze failure, do not resample'
fixtures={}
for seed in list(range(87000,87192))+list(range(89000,89008)):
 b=chess.Board();rng=random.Random(seed);moves=[]
 for _ in range(24):
  if b.is_game_over(claim_draw=False):break
  m=rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()));b.push(m);moves.append(m.uci())
 terminal=b.is_game_over(claim_draw=False)
 fixtures[str(seed)]=dict(moves=moves,terminal=terminal,fen=b.fen(),termination=b.outcome(claim_draw=False).termination.name if terminal else None)
(out/'opening_contract.json').write_text(json.dumps(fixtures,indent=2),encoding='utf-8')
decl=dict(task_id='131',question='Can the full-domain coordinate control be completed with an explicit terminal-opening contract, avoiding repeated valid-prefix work?',old_task129='INTERRUPTED816actualtraininggames,0heldout; preserved and never relabeled completed',source_controller_sha256=hashlib.sha256((old/'controller.json').read_bytes()).hexdigest(),source_driver_sha256=hashlib.sha256((old/'run.py').read_bytes()).hexdigest(),new_premise='Fixed24randomopening may itself become terminal. Preflight all200declaredseedroots without resampling; terminal input is EXCLUDED_INPUT, no engine game/reward, zero-information slot contribution only. Same exclusions for all candidates and bothcolors, no userdecision needed.',terminal_inputs=[{'seed':seed,**f} for seed,f in fixtures.items() if f['terminal']],cached_actual_games=816,new_actual_games_maximum=2736,planned_trial_slots=3552,planned_train_slots=3456,planned_heldout_slots=96,selection='SameTask129schedule and reward; excludedinput contributes0 to fixedslot mean, equivalent to same positive common denominator rescaling across allarms; report eligible-only heldout means separately',human_prices_in_training=False,old_human_description='unchangedfixedreference; reusedstarts/exposedprefix, not independent validation',per_seed_order='freeze that seed final then heldout, nextseedtraining; no crossseed heldout feedback',total_original_plus_new_run_budget_seconds=900,old_actual_seconds=status['wall_seconds'],new_run_budget_seconds=900-status['wall_seconds'],scope='Changed input contract continuation with auditable oldprefix provenance, not fresh independent rerun or recovery of oldfrozencompletion status. No new seeds, longergames,extra workers or fees.',done='Exact3552trialslots classified; cached/new actual outputs independentlyreplayed; all3ends/eligibleheldout and inclusive old/newcost reported. Any otherfailure stops, no expansion.')
(out/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
s=(old/'run.py').read_text(encoding='utf-8').replace("OUT=ROOT/'results/dev_aux/task129'","OUT=ROOT/'results/dev_aux/task131'")
s=s.replace("journal=A.Journal(OUT/'events.jsonl');started=time.monotonic();deadline=started+900;calls=[];runs=[];e=None", "journal=A.Journal(OUT/'events.jsonl');started=time.monotonic();deadline=started+DECL['new_run_budget_seconds'];calls=[];runs=[];e=None;new_physical=0;excluded=0;cached_used=0")
s=s.replace("STEPS=[(E.HIGH-E.LOW)/2**(i+1) for i in range(6)]", "STEPS=[(E.HIGH-E.LOW)/2**(i+1) for i in range(6)]\nDECL=json.loads((OUT/'declaration.json').read_bytes());FIXTURES=json.loads((OUT/'opening_contract.json').read_bytes());CACHE=json.loads((ROOT/'results/dev_aux/task129/controller.json').read_bytes())['calls']")
start=s.index(' def block(');end=s.index(' try:\n  for seed in (103,104,105):',start)
block=''' def block(w,seed,sweep,coordinate,arm,phase):
  nonlocal e,new_physical,excluded,cached_used
  A.guard(deadline,stop);rewards=[]
  if hashlib.sha256(binary.read_bytes()).hexdigest()!=digest:raise RuntimeError('Binary changed')
  try:
   for oi in range(8):
    for color in (True,False):
     opening_seed=87000+(sweep*4+coordinate)*8+oi if phase=='train' else 89000+oi
     random_seed=97000+(sweep*4+coordinate)*8+oi if phase=='train' else 99000+oi
     x=dict(opening_seed=opening_seed,random_seed=random_seed,agent_color=color,phase=phase,name=f's{seed}-{phase}-sweep{sweep}-k{coordinate}-a{arm}-o{oi}-c{int(color)}')
     fixture=FIXTURES[str(opening_seed)]
     if fixture['terminal']:
      excluded+=1;calls.append(dict(context=x,weights=dict(w),result=None,status='EXCLUDED_INPUT',selection_contribution=0,opening=fixture['moves'],root_termination=fixture['termination']))
      journal.record('excluded_terminal_opening',context=x,weights=w,fixture=fixture);rewards.append(0)
     elif cached_used<len(CACHE):
      c=CACHE[cached_used];assert c['context']==x and c['weights']==w and c['result']['opening']==fixture['moves']
      calls.append(dict(copy.deepcopy(c),provenance='CACHED_ACTUAL_TASK129',source_call_index=cached_used));rewards.append(c['result']['reward'])
      journal.record('cached_actual_callback',context=x,source_call_index=cached_used,source_controller_sha256=DECL['source_controller_sha256']);cached_used+=1
     else:
      if e is None:e=A.UCI(binary,ROOT,deadline,stop);e.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
      r=A.play_game(e,w,x,deadline,OUT/'variant.ini',journal,lambda seed:FIXTURES[str(seed)]['moves'],G.score,stop,cap=16);A.guard(deadline,stop)
      new_physical+=1;calls.append(dict(context=x,weights=dict(w),result=r,provenance='NEW_ACTUAL_TASK131'));rewards.append(r['reward'])
     if len(calls)%48==0:
      A.atomic_json(OUT/'progress.json',dict(trial_slots=len(calls),cached_used=cached_used,new_physical=new_physical,excluded=excluded,wall_seconds=time.monotonic()-started,current=x['name']))
      print(json.dumps(dict(trial_slots=len(calls),cached_used=cached_used,new_physical=new_physical,excluded=excluded,wall_seconds=round(time.monotonic()-started,3))),flush=True)
  finally:
   if e:e.close();e=None
  return rewards
'''
s=s[:start]+block+s[end:]
s=s.replace("scope='Actual full-domain coordinate schedule, not extension of old frozen experiments'", "scope='Changed terminal-input contract; includes provenance-bound old actual prefix, old failure preserved'")
s=s.replace("hard_seconds=900,cap=16,steps=STEPS", "hard_seconds=DECL['new_run_budget_seconds'],old_run_seconds=DECL['old_actual_seconds'],inclusive_old_new_run_seconds=DECL['old_actual_seconds']+time.monotonic()-started,cached_actual=cached_used,new_actual=new_physical,excluded_input_slots=excluded,unique_actual_games=cached_used+new_physical,cap=16,steps=STEPS")
(out/'run.py').write_text(s,encoding='utf-8');(out/'change.patch').write_text(''.join(difflib.unified_diff((old/'run.py').read_text().splitlines(True),s.splitlines(True),fromfile='Task129/run.py',tofile='Task131/run.py')),encoding='utf-8')
print(json.dumps(dict(terminal_roots=[seed for seed,f in fixtures.items() if f['terminal']],cached816=True,remaining_budget=decl['new_run_budget_seconds'],contract_changed=True)))