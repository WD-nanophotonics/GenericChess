import json,hashlib,time
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task268';assert not (O/'audit.json').exists();D=json.loads((R/'results/dev_aux/task267/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task267/result.json').read_bytes());assert X['complete'];start=time.monotonic();go=plychecks=0;allterminal=[]
for z in X['calls']:
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert b.fen()==f['expected_fen'] and z['opening_history']==f['history'];assert len(z['actions'])==len(z['search_records'])==z['ply_count']<=48
 for ply,(text,rec) in enumerate(zip(z['actions'],z['search_records'])):
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves;meta=rec['record'];name='semantic' if b.turn==z['color'] else z['opponent'];assert rec['player']==name and rec['ply']==ply;assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack] and meta['nodes_limit']==z['node_limit'];assert meta['reported_nodes'] is not None and meta['reported_depth'] is not None
  for line in meta['uci_info']:
   if line.startswith('info ') and ' pv ' in line:
    bb=b.copy(stack=True)
    for move in line.split(' pv ',1)[1].split():mm=chess.Move.from_uci(move);assert mm in bb.legal_moves;bb.push(mm)
  b.push(m);plychecks+=1;go+=1
 assert b.fen()==z['final_fen'];out=b.outcome(claim_draw=False);assert (out is not None)==z['terminal'];kind='UNKNOWN_CUTOFF' if out is None else out.termination.name;sign=0 if out is None or out.winner is None else 1 if out.winner==z['color'] else -1;assert z['termination']==kind and z['finite_mate_goal']==(sign if kind=='CHECKMATE' else 0) and z['actual_terminal_result']==(None if out is None else sign);assert z['quantity_at_cap']==sum(len(b.pieces(t,z['color']))-len(b.pieces(t,not z['color'])) for t in range(1,6))
 for name in ('semantic',z['opponent']):
  w=D['profiles'][name];assert z['table_ack'][name]['alignment']==3 and z['table_ack'][name]['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')};assert len(z['leaf_probes'][name])==5
  for p in z['leaf_probes'][name]:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
 allterminal.append(dict(opponent=z['opponent'],node_limit=z['node_limit'],root=z['root'],color=z['color'],termination=kind,sign=z['finite_mate_goal'],unknown=out is None,plies=z['ply_count']))
def summary(rr):
 n=len(rr);wins=sum(z['finite_mate_goal']==1 for z in rr);losses=sum(z['finite_mate_goal']==-1 for z in rr);draws=sum(z['terminal'] and z['actual_terminal_result']==0 for z in rr);unknown=n-wins-losses-draws;net=Fraction(wins-losses,n);return dict(games=n,wins=wins,losses=losses,draws=draws,unknown=unknown,finite_mate_goal=str(net),quantity_mean=str(Fraction(sum(z['quantity_at_cap'] for z in rr),n)),fully_censored_final_net_result_bounds=[str(Fraction(wins-losses-unknown,n)),str(Fraction(wins-losses+unknown,n))],winning_plies=[z['ply_count'] for z in rr if z['finite_mate_goal']==1])
groups=[]
for limit in D['node_limits']:
 for op in D['opponents']:
  rr=[z for z in X['calls'] if z['node_limit']==limit and z['opponent']==op];assert len(rr)==8;groups.append(dict(node_limit=limit,opponent=op,**summary(rr),leave_one_root_out=[dict(omitted=i,**summary([z for z in rr if z['root']!=i])) for i in range(4)]))
aggregates=[dict(node_limit=n,**summary([z for z in X['calls'] if z['node_limit']==n])) for n in D['node_limits']];pairs=[]
for op in D['opponents']:
 for i in range(4):
  for color in (True,False):
   rr=[next(z for z in X['calls'] if z['opponent']==op and z['root']==i and z['color']==color and z['node_limit']==n) for n in D['node_limits']];pairs.append(dict(opponent=op,root=i,color=color,finite_goal_delta=rr[1]['finite_mate_goal']-rr[0]['finite_mate_goal'],same_actions=rr[0]['actions']==rr[1]['actions'],terminations=[z['termination'] for z in rr]))
out=dict(complete=True,actual_games=len(X['calls']),actual_mature_queries=go,legal_plies=plychecks,groups=groups,aggregates=aggregates,node_curve_pairs=pairs,seconds=time.monotonic()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task267/result.json').read_bytes()).hexdigest(),scope='Actual128pairedcolor/fixedbudget48ply games allhistory/moves/allreportedPV/readbacks/outcomes audited. Unknownnotdraw; censoredboundsnotconfidenceintervals. Fourfixedoldroots notpopulation/IID, terminalgoalnotfullChessstrength; nohumanpricelearning. Greaternodebudget canhaveadverseshortcap results.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','actual_games','actual_mature_queries','aggregates','seconds')},indent=2));print([(z['node_limit'],z['opponent'],z['wins'],z['losses'],z['draws'],z['unknown']) for z in groups])
