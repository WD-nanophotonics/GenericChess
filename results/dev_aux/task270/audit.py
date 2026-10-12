import json,time,hashlib,importlib.util,math
from fractions import Fraction
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task270';D=json.loads((R/'results/dev_aux/task269/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task269/result.json').read_bytes());E=json.loads((R/'results/dev_aux/task269/endpoints.json').read_bytes());assert X['complete'];start=time.monotonic();queries=0;rows=[]
for z in X['calls']:
 f=D['train_roots' if z['phase']=='train' else 'development_roots'][z['root']];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert b.fen()==f['expected_fen'];assert len(z['actions'])==len(z['search_records'])<=48
 for ply,(text,rec) in enumerate(zip(z['actions'],z['search_records'])):
  assert rec['ply']==ply;actor='agent' if b.turn==z['color'] else 'unit';assert rec['player']==actor;meta=rec['record'];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack] and meta['nodes_limit']==1024;m=chess.Move.from_uci(text);assert m in b.legal_moves
  for line in meta['uci_info']:
   if line.startswith('info ') and ' pv ' in line:
    bb=b.copy(stack=True)
    for pm in line.split(' pv ',1)[1].split():mm=chess.Move.from_uci(pm);assert mm in bb.legal_moves;bb.push(mm)
  b.push(m);queries+=1
 out=b.outcome(claim_draw=False);sign=0 if out is None or out.winner is None else 1 if out.winner==z['color'] else -1;kind='UNKNOWN_CUTOFF' if out is None else out.termination.name;fitness=Fraction(sign)*(1+Fraction(48-len(z['actions']),4800)) if kind=='CHECKMATE' else Fraction(0);assert z['final_fen']==b.fen() and z['termination']==kind and z['fitness']==str(fitness) and z['finite_mate_goal']==(sign if kind=='CHECKMATE' else 0) and z['actual_terminal_result']==(None if out is None else sign);assert z['quantity_at_cap']==sum(len(b.pieces(t,z['color']))-len(b.pieces(t,not z['color'])) for t in range(1,6))
 for ack,w in [(z['table_ack'],z['weights']),(z['opponent_table_ack'],D['opponent_weights'])]:assert ack['alignment']==3 and ack['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')}
rowsTrain=[z for z in X['calls'] if z['phase']=='train'];assert len(rowsTrain)==144;means={name:sum(Fraction(z['fitness']) for z in rowsTrain if z['name']==name)/4 for name in D['profiles']};assert E['train_means']=={k:str(v) for k,v in means.items()};assert E['chosen']=={name:max(fam,key=lambda k:means[k]) for name,fam in D['families'].items()};assert E['weights']=={name:D['profiles'][key] for name,key in E['chosen'].items()};assert E['training_games']==144
# Everydevelopment logicalalias points to actualidenticalweights, notnewindependentgames.
held={**{f'initial-{n}':w for n,w in D['initials'].items()},**{f'selected-{n}':w for n,w in E['weights'].items()},'unit':D['opponent_weights']}
for name,w in held.items():physical=X['development_aliases'][name];rr=[z for z in X['calls'] if z['phase']=='development' and z['name']==physical];assert len(rr)==4 and all(z['weights']==w for z in rr)
def summarize(rr):return dict(games=len(rr),wins=sum(z['finite_mate_goal']==1 for z in rr),losses=sum(z['finite_mate_goal']==-1 for z in rr),draws=sum(z['terminal'] and z['actual_terminal_result']==0 for z in rr),unknown=sum(not z['terminal'] for z in rr),finite_goal=str(sum(Fraction(z['finite_mate_goal']) for z in rr)/len(rr)),fitness=str(sum(Fraction(z['fitness']) for z in rr)/len(rr)),quantity=str(Fraction(sum(z['quantity_at_cap'] for z in rr),len(rr))))
for name,selected in E['chosen'].items():
 base=[z for z in rowsTrain if z['name']==name];sel=[z for z in rowsTrain if z['name']==selected];bdev=[z for z in X['calls'] if z['phase']=='development' and z['name']==X['development_aliases']['initial-'+name]];sdev=[z for z in X['calls'] if z['phase']=='development' and z['name']==X['development_aliases']['selected-'+name]]
 def humanDistance(w):return sum(math.log((w[k]/w['P'])/target)**2 for k,target in zip('NBRQ',(3,3,5,9)))
 rows.append(dict(initial=name,selected=selected,initial_weights=D['initials'][name],selected_weights=E['weights'][name],train_initial=summarize(base),train_selected=summarize(sel),development_initial=summarize(bdev),development_selected=summarize(sdev),human_log_squared_distance_initial=humanDistance(D['initials'][name]),human_log_squared_distance_selected=humanDistance(E['weights'][name]),descriptive_human_distance_delta=humanDistance(E['weights'][name])-humanDistance(D['initials'][name]),warning='Humanreference AFTERfrozenendpoints/actualallresult; descriptiveonlynotselection/proof. Olddevelopmentexposed/correlated4games notconfidence.') )
out=dict(complete=True,actual_games=len(X['calls']),actual_mature_queries=queries,independent_train_selection_checks=36,endpoint_frozen_before_development_recorded=E['frozen_at'],rows=rows,seconds=time.monotonic()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task269/result.json').read_bytes()).hexdigest(),scope='172actualgames/144train+28physicaldevelopment,8logicaldevelopmentaliasduplicates notindependent. Allhistory/PVs/terminalfitness/selectionchecked; unknownnotdraw. Onepredeclaredgenerationnotrapidgeneralhumanlearning.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'},indent=2))
