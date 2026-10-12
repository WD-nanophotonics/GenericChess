"""Fixed endpoint contrasts across mature development, completeD3 and random coupling."""
import json,time,random,math,collections,hashlib
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task329';O.mkdir(exist_ok=False);start=time.monotonic();D0=json.loads((R/'results/dev_aux/task322/declaration.json').read_bytes());E=json.loads((R/'results/dev_aux/task322/endpoints.json').read_bytes());train=json.loads((R/'results/dev_aux/task320/result.json').read_bytes())['calls']+[json.loads(l) for l in (R/'results/dev_aux/task322/games.jsonl').read_bytes().splitlines()];datasets={};checks=0;extra_queries=0
for task in (327,328):
 D=json.loads((R/f'results/dev_aux/task{task}/declaration.json').read_bytes());X=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());assert X['complete'];rows=X['calls']
 for z in rows:
  f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
  for u in f['history']:b.push_uci(u)
  ss={r['ply']:r['record'] for r in z['search_records']};rs={r['ply']:r for r in z['random_choices']};rng=random.Random(z['seed']);turn=0
  for ply,u in enumerate(z['actions']):
   assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(u);assert m in b.legal_moves
   if b.turn==z['color']:
    meta=ss[ply];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack];lines=[line.split() for line in meta['uci_info'] if ' pv ' in line];pv=lines[-1][lines[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
    for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
    assert meta['nodes_limit']==1024 and meta['reported_nodes']>=0;extra_queries+=1
   else:
    if task==328:rng=random.Random(str(z['seed'])+':'+str(turn));turn+=1
    legal=sorted(b.legal_moves,key=lambda m:m.uci());ix=rng.randrange(len(legal));assert rs[ply]==dict(ply=ply,index=ix,legal_count=len(legal),move=legal[ix].uci()) and legal[ix]==m
   b.push(m)
  oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;goal=F(49-len(z['actions']),48) if kind=='CHECKMATE' and sign==1 else F(-1) if kind=='CHECKMATE' and sign==-1 else F(0);assert b.fen()==z['final_fen'] and kind==z['termination'] and str(goal)==z['fitness'];assert z['table_ack']['prices']=={str(i+1):[z['weights'][k]]*2 for i,k in enumerate('PNBRQ')}
  for pr in z['leaf_probes']:assert abs(pr['measured_white_pawns']-z['weights'][pr['type']]/208)<.011
  checks+=1
 datasets['mature_development' if task==327 else 'mature_ordinal_coupling']=rows
native=json.loads((R/'results/dev_aux/task325/result.json').read_bytes());assert native['complete'];datasets['Native_train']=[z for z in native['rows'] if z['phase']=='train_deployment'];datasets['Native_development']=[z for z in native['rows'] if z['phase']=='exposed_development'];needed={tuple(w[k] for k in 'PNBRQK') for w in D0['initials'].values()}|{tuple(v['weights'][k] for k in 'PNBRQK') for v in E['endpoints'].values()};datasets['mature_training']=[z for z in train if tuple(z['weights'][k] for k in 'PNBRQK') in needed];datasets['mature_train_first4seeds']=[z for z in datasets['mature_training'] if z['seed'] in D0['random_seeds'][:4]]
def key(w):return tuple(w[k] for k in 'PNBRQK')
def mean(zz):return sum(F(z['fitness']) for z in zz)/len(zz)
contrasts=[];summary=[]
for dataset,rows in datasets.items():
 for kk in sorted(needed):
  zz=[z for z in rows if key(z['weights'])==kk];assert len(zz) in (16,64);summary.append(dict(dataset=dataset,weights=dict(zip('PNBRQK',kk)),games=len(zz),fitness=str(mean(zz)),wins=sum(z['finite_mate_sign']==1 for z in zz),losses=sum(z['finite_mate_sign']==-1 for z in zz),unknown=sum(z['termination']=='UNKNOWN_CUTOFF' for z in zz)))
 for family,initial in D0['initials'].items():
  aa=[z for z in rows if key(z['weights'])==key(initial)];bb=[z for z in rows if key(z['weights'])==key(E['endpoints'][family]['weights'])];am={(z['root'],z['color'],z['seed']):z for z in aa};bm={(z['root'],z['color'],z['seed']):z for z in bb};assert set(am)==set(bm);delta={k:F(bm[k]['fitness'])-F(am[k]['fitness']) for k in am};roots=sorted(set(z['root'] for z in aa));contrasts.append(dict(dataset=dataset,family=family,cells=len(aa),speed_delta=str(mean(bb)-mean(aa)),net_sign_delta=str(F(sum(z['finite_mate_sign'] for z in bb)-sum(z['finite_mate_sign'] for z in aa),len(aa))),positive_cells=sum(v>0 for v in delta.values()),negative_cells=sum(v<0 for v in delta.values()),root_deltas={str(ri):str(sum(v for k,v in delta.items() if k[0]==ri)/sum(k[0]==ri for k in delta)) for ri in roots},color_deltas={str(color):str(sum(v for k,v in delta.items() if k[1]==color)/sum(k[1]==color for k in delta)) for color in (True,False)}))
out=dict(complete=True,new_mature_games_replayed=checks,new_mature_queries_checked=extra_queries,summary=summary,contrasts=contrasts,Native_completegames_producer=400,Native_exactvalue_audit='326separatereceipt, verifycompletebeforeclaimallvalues;329onlyusesalreadyfrozenactualterminalgamefields.',seconds=time.monotonic()-start,scope='Allendpointcontrasts fixed, nobestcase/model/horizon selection, nofitafternewseeds. Olddevelopmentroots exposed. Originalstream andordinalstream differcoupling only underuniformlegalPRNGpolicy model; finite realizations notIIDconfidence. NativecompleteD3 andmature1024areoverallbackend/resource references, notpurepruningcausality/equalwork oruniversalstrength. Humanratios descriptivepostfit324, nevercandidatefit.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(complete=True,games=checks,queries=extra_queries,seconds=out['seconds'],contrasts=contrasts),indent=2))