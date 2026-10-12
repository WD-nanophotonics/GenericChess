import json,time,hashlib
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task275';D=json.loads((R/'results/dev_aux/task274/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task274/result.json').read_bytes());base=json.loads((R/'results/dev_aux/task267/result.json').read_bytes());assert X['complete'] and base['complete'];start=time.monotonic();go=0
for z in X['calls']:
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert b.fen()==f['expected_fen'];assert len(z['actions'])==len(z['search_records'])<=48
 for ply,(text,rec) in enumerate(zip(z['actions'],z['search_records'])):
  side='semantic' if b.turn==z['color'] else 'unit';assert rec['player']==side and rec['ply']==ply and rec['record']['full_history']==[m.uci() for m in b.move_stack] and rec['record']['root_fen']==f['initial_fen'];assert rec['record']['nodes_limit']==z['node_limit'];m=chess.Move.from_uci(text);assert m in b.legal_moves
  for line in rec['record']['uci_info']:
   if line.startswith('info ') and ' pv ' in line:
    bb=b.copy(stack=True)
    for pm in line.split(' pv ',1)[1].split():mm=chess.Move.from_uci(pm);assert mm in bb.legal_moves;bb.push(mm)
  b.push(m);go+=1
 oo=b.outcome(claim_draw=False);sign=0 if oo is None or oo.winner is None else 1 if oo.winner==z['color'] else -1;term='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;assert b.fen()==z['final_fen'] and term==z['termination'] and (sign if term=='CHECKMATE' else 0)==z['finite_mate_goal'] and z['actual_terminal_result']==(None if oo is None else sign)
 for side in ('semantic','unit'):
  w=D['profiles'][side+'-c'+z['scale']]['weights'];assert z['weights'][side]==w and z['table_ack'][side]['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')};assert len(z['leaf_probes'][side])==5
  for p in z['leaf_probes'][side]:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
calls=[dict(z,scale='1over1',reused_from='267') for z in base['calls'] if z['opponent']=='unit']+X['calls'];assert len(calls)==48
def summarize(rr):return dict(games=len(rr),wins=sum(z['finite_mate_goal']==1 for z in rr),losses=sum(z['finite_mate_goal']==-1 for z in rr),draws=sum(z['terminal'] and z['actual_terminal_result']==0 for z in rr),unknown=sum(not z['terminal'] for z in rr),finite_net=str(Fraction(sum(z['finite_mate_goal'] for z in rr),len(rr))))
groups=[dict(scale=c,node_limit=n,**summarize([z for z in calls if z['scale']==c and z['node_limit']==n])) for c in ('1over2','1over1','2over1') for n in (1024,16384)];pairs=[]
for n in (1024,16384):
 for root in range(4):
  for color in (True,False):
   rr=[next(z for z in calls if z['scale']==c and z['node_limit']==n and z['root']==root and z['color']==color) for c in ('1over2','1over1','2over1')];pairs.append(dict(node_limit=n,root=root,color=color,goals=[z['finite_mate_goal'] for z in rr],terminations=[z['termination'] for z in rr],plies=[len(z['actions']) for z in rr],changed_trajectory=len({tuple(z['actions']) for z in rr})>1))
out=dict(complete=True,new_games=len(X['calls']),new_mature_queries=go,reused_actual_baseline_games=16,groups=groups,pairs=pairs,changed_trajectory_groups=sum(z['changed_trajectory'] for z in pairs),seconds=time.monotonic()-start,scope='Every32newactualhistory/PV/readback/goalchecked;16baselinegames explicitlyreused notfreshsample. Ratiosheld withhalfroundingkept. Scalechanges meansemanticgoal, butsmall4roots notgeneralcausalpricevalueconclusion. No bestcselection/automaticrepeats.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='pairs'},indent=2))
