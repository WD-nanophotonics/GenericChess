from pathlib import Path
import json,hashlib,datetime
OUT=Path('results/dev_aux/task2355')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 OUT.mkdir(exist_ok=True);assert not(OUT/'plan.json').exists();read=lambda p:json.loads(Path(p).read_text());reuse=read('results/dev_aux/task2356/result.json');assert reuse['status'].startswith('PASS')and reuse['reuse_count']==65
 old=read('results/dev_aux/task2340/plan.json');roots=read(old['input']);grid=[.5,1.,1.5,2.,3.];used={tuple(e['key']):e for e in reuse['entries']};matrix=[];fresh=[]
 for root in sorted(r['index']for r in roots):
  for opponent in range(2):
   for color in(0,1):
    shift=(root+opponent+color)%5;prices=grid[shift:]+grid[:shift]
    for price in prices:
     key=(root,old['opponents'][opponent]['ratio'],color,price);row=dict(matrix_slot=len(matrix),root=root,opponent=opponent,candidate_color=color,ratio=price,arm='LOW_ONLY_INCREMENTAL')
     if key in used:row.update(source_task=used[key]['task'],source_slot=used[key]['slot'],kind='REUSED_ACTUAL_TERMINAL')
     else:
      row.update(source_task=2355,source_slot=len(fresh),kind='NEW_GAME');fresh.append(dict(slot=len(fresh),root=root,opponent=opponent,candidate_color=color,ratio=price,arm=row['arm'],matrix_slot=row['matrix_slot']))
     matrix.append(row)
 assert len(matrix)==160 and len(fresh)==95
 def save(n,v):
  with(OUT/n).open('x',encoding='utf-8')as f:json.dump(v,f,indent=2)
 save('inputs.json',roots);save('slots.json',fresh);save('matrix.json',matrix);save('reuse.json',reuse['entries'])
 p=dict(old);p.update(input=str(OUT/'inputs.json'),input_sha=sha(OUT/'inputs.json'),slots_sha=sha(OUT/'slots.json'),expected_games=95,one_cap_seconds=2400,estimated_seconds=1900)
 p['selection']='NEW82 complete positive material-order TRAIN conditions .5/1/1.5/2/3 (open cells and exact boundaries1,2) from prior79 structural partition,8fixedoldTRAIN/foes.5,2/bothroles; matrix160, reuse65closedcompatiblekeys and95new, no duplicate key. New finite-grid criterion actualmeanW-L strictgainoverbaseline1, tiesbaseline1 thenlowestimprovingprice. Original2340 remains49closed/1UNKNOWN/46unstarted; not resumed/completed.'
 p['scope']='NEW82 registered complete material-order TRAIN study, not budget extension or completion claim for old2340. Changedscientificpremise: old3pointgrid omitted lowerpositivecell/exact2boundary; cost premise:65source terminals validated reusable, ownfailure closure repaired. New95single2400wallcap forecast1900<2h, plus explicitprepaid65gamecost1217.52s; do not hide cumulativecost or call reused records fresh/independent. Ifanymatrixslotmissing/U no selection. Public reference fullyexposed, oldTRAINnotblind, currentwalllimitedpolicy equivalence not proved by leaforder partition. Reserve2341stays price-unqueried, no81DEVpricechoice/default/PRIMARYwrite/workers/oldcapreset.'
 names=['results/dev_aux/task2354/pilot.py','results/dev_aux/task2354/test_closure.py','results/dev_aux/task2355/freeze.py','results/dev_aux/task2355/matrix.json','results/dev_aux/task2355/reuse.json','results/dev_aux/task2356/qualify.py','results/dev_aux/task2356/result.json','results/dev_aux/task2357/select.py','results/dev_aux/task2357/selection-contract.json','results/dev_aux/task2341/inputs.json','results/dev_aux/task2341/exposure-correction.json','results/dev_aux/task2210/player.py','results/dev_aux/task2273/incremental_adapted.py','generic_chess/core/semantic_executor.py','generic_chess/session/session.py']
 p['pins']={n:sha(n)for n in names};save('plan.json',p);save('registration.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),matrix160=160,reused65=65,new95=95,original_new_cap_seconds=2400,expected_new_seconds=1900,paid_reuse_game_seconds=reuse['paid_game_seconds'],reserve_sha=sha('results/dev_aux/task2341/inputs.json'),selection_sha=sha('results/dev_aux/task2357/select.py'),exposure='AlloldTRAINand81transferresults alreadyknown; newmissingTRAINqueriesnotyetexecuted; no newreservedperformancequeries. Fiveconditions fromprior79, not chosenforDEVperformance.'))
 print(json.dumps(dict(matrix=160,reuse=65,new=95,cap=2400,forecast=1900,paid_reuse_seconds=reuse['paid_game_seconds'])))
if __name__=='__main__':run()
