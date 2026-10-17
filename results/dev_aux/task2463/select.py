"""N-hand TRAIN selection with once-only measured baseline reuse."""
from pathlib import Path
from collections import Counter
import json,time,datetime,hashlib
OUT=Path('results/dev_aux/task2463')
def run():
 f=Path('results/dev_aux/task2461');assert(f/'completion.json').exists();done=json.loads((f/'completion.json').read_text());slots=json.loads((f/'slots.json').read_text());games={g['slot']:g for g in map(json.loads,(f/'games.jsonl').read_text().splitlines())};reuse=json.loads((f/'baseline-reuse.json').read_text());assert json.loads(Path('results/dev_aux/task2459/reuse-result.json').read_text())['reused_games']==8;rows=[]
 for value in(0.,.5,1.,2.):
  counts=Counter();blocks=[]
  for family in range(4):
   bounds=[]
   for role in(0,1):
    if value==1.:
     r,=[r for r in reuse if r['family']==family and r['role']==role];reward=r['reward'];outcome=r['outcome']
    else:
     ss,=[s for s in slots if s['root']==family and s['candidate_color']==role and s['N_hand']==value];g=games.get(ss['slot']);reward=None if g is None else g['reward'];outcome='U'if g is None else g['outcome']
    counts['U'if reward is None else outcome]+=1;bounds.append((-1,1)if reward is None else(reward,reward))
   blocks.append([sum(b[i]for b in bounds)/2 for i in(0,1)])
  rows.append(dict(N_hand=value,counts={k:counts[k]for k in'WLDU'},family_bounds=blocks,mean_bounds=[sum(b[i]for b in blocks)/4 for i in(0,1)]))
 baseline=next(r for r in rows if r['N_hand']==1.);eligible=[r for r in rows if r['mean_bounds'][0]>baseline['mean_bounds'][1]];selected=min(eligible,key=lambda r:(-r['mean_bounds'][0],r['N_hand']))if eligible else baseline
 result=dict(status='IMMUTABLE_NHAND_TRAIN_ONLY_SELECTION',selected_N_hand=selected['N_hand'],baseline_N_hand=1.,R_board_hand=[.75,.75],rows=rows,new_games=len(games),reuse_games=8,all_matrix_cells=len(games)+8,unreturned_new=len(slots)-len(games),completion_status=done['status'],utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_games_sha=hashlib.sha256((f/'games.jsonl').read_bytes()).hexdigest(),scope='TRAIN-onlyscalarNhand modelrestrictiondiagnostic afteroriginal2Dplateau; no changedprimary2Dselection. AnchorchosenlexmaxTRAINtie, noreservefitnessused. EightoriginalmeasuredanchorNhand1games reusedonce/config+callbackqualified, notnewreplication. U/missingworstbounds; noquantity/humanfit/stability/defaultclaim. New8initialorbits remainunqueried unlessstrictimprover; conditionalreservedbranchfalse isnotfakezero-gainvalidation.')
 with(OUT/'selection.json').open('x')as fp:json.dump(result,fp,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
