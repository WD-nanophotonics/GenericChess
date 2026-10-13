import json,time,math,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task571';start=time.perf_counter();axes=[2,3,4,5,6,7,9,10,11,12,13,14];MAP={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8};rows=[]
def occupancy(sfen):
 board,turn,hand,num=sfen.split();counts=[0]*16;prom=False
 for x in board:
  if x=='+':prom=True;continue
  if x=='/' or x.isdigit():continue
  counts[MAP[x.upper()]+(8 if prom else 0)]+=1;prom=False
 num=''
 for x in hand:
  if x=='-':continue
  if x.isdigit():num+=x;continue
  counts[MAP[x.upper()]]+=int(num or '1');num=''
 assert sum(counts)==40 and counts[8]==2;return counts
for task,route,opp in [(554,'pure24','unit'),(555,'pure24','random'),(565,'mixed12','unit'),(566,'mixed12','random')]:
 families={a:set() for a in axes};active={a:0 for a in axes};changed={a:0 for a in axes};states=0;games=0;initialroots={}
 for line in (R/f'results/dev_aux/task{task}/games.jsonl').open():
  g=json.loads(line);f=g['root'];seed=f['seed'];old=occupancy(f['expected_sfen']);initialroots[seed]=old;states+=1;games+=1
  for a in axes:
   if old[a]:families[a].add(seed);active[a]+=1
  for action in g['actions']:
   v=occupancy(action['after_sfen']);states+=1
   for a in axes:
    if v[a]:families[a].add(seed);active[a]+=1
    if old[a]!=v[a]:changed[a]+=1
   old=v
 rows.append(dict(route=route,opponent=opp,actual_games=games,played_state_records=states,independent_families=len(initialroots),initial_root_presence={str(a):sum(v[a]>0 for v in initialroots.values()) for a in axes},family_axis_presence={str(a):sorted(families[a]) for a in axes},state_axis_presence=active,count_changed_actions=changed,scope='Actualboard+hand typeoccupancy, signedfeatures/rank/feedbackidentifiability NOTclaimed; repeateddirection/price states areNOTindependentsamples. NoPV/frontier coverage claims.'))
out=dict(status='PASS_FINITE_OCCUPANCY',rows=rows,seconds=time.perf_counter()-start,new_go=0,question='Can poorpriceagreement be dismissedonlyas missingpromoted types? ALLbasicandpromoted actualplayedfamilycoverage, notnewfit orsourceparameter tuning.',scope='Post-execution coverage diagnosis beforechoosingnexttask; all4closedfits/typeaxes retained, no active-root selection/universal identifiability.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}));print([{k:r[k] for k in ['route','opponent','played_state_records','initial_root_presence','state_axis_presence','count_changed_actions']} for r in rows])
