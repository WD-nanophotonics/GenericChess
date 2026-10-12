import json,time,hashlib
from fractions import Fraction
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task273';D=json.loads((R/'results/dev_aux/task272/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task272/result.json').read_bytes());assert X['complete'];start=time.monotonic();refs=[];terminal_visits=0
for f in D['roots']:
 b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert b.fen()==f['fen'];actor=b.turn;actions=[]
 def leaf(ply):
  global terminal_visits
  oo=b.outcome(claim_draw=False)
  if oo:terminal_visits+=1;return dict(terminal=0 if oo.winner is None else (100000000-ply if oo.winner==actor else -100000000+ply))
  return dict(vector=[len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6)])
 for m in sorted(b.legal_moves,key=lambda z:z.uci()):
  b.push(m);ll=[]
  if b.is_game_over(claim_draw=False):ll.append(leaf(1))
  else:
   for reply in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(reply);ll.append(leaf(2));b.pop()
  b.pop();actions.append(dict(move=m.uci(),leaves=ll))
 controls={}
 for pr,pp in D['profiles'].items():
  w=pp['weights'];exact={k:Fraction(v)*Fraction(pp['numerator'],pp['denominator']) for k,v in pp['unscaled'].items()}
  def solve(weights):
   ss=[min(ld['terminal'] if 'terminal' in ld else sum(weights[k]*v for k,v in zip('PNBRQ',ld['vector'])) for ld in a['leaves']) for a in actions];best=max(ss);return dict(value=str(best),argmax=[a['move'] for a,v in zip(actions,ss) if v==best],max_abs_leaf=str(max(abs(ld['terminal'] if 'terminal' in ld else sum(weights[k]*v for k,v in zip('PNBRQ',ld['vector']))) for a in actions for ld in a['leaves'])))
  controls[pr]=dict(rounded=solve(w),exact_rational=solve(exact))
 for name in ('semantic','unit'):
  baseline=controls[name+'-c1over1']['exact_rational']['argmax'];assert all(controls[name+s]['exact_rational']['argmax']==baseline for s in ('-c1over2','-c2over1'))
 refs.append(dict(root=f['id'],controls=controls))
queries=[]
for z in X['rows']:
 f=next(f for f in D['roots'] if f['id']==z['root']);w=D['profiles'][z['profile']]['weights'];assert z['weights']==w and z['metadata']['full_history']==f['history'] and z['metadata']['root_fen']==f['initial_fen'];b=chess.Board(f['initial_fen'])
 for text in f['history']:b.push_uci(text)
 assert chess.Move.from_uci(z['action']) in b.legal_moves
 assert z['table_ack']['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')};assert len(z['leaf_probes'])==5
 for p in z['leaf_probes']:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
 for line in z['metadata']['uci_info']:
  if line.startswith('info ') and ' pv ' in line:
   bb=b.copy(stack=True)
   for pm in line.split(' pv ',1)[1].split():m=chess.Move.from_uci(pm);assert m in bb.legal_moves;bb.push(m)
queries.append(dict(root=f['id'],profile=z['profile'],limit=z['limit'],action=z['action'],reported_depth=z['metadata']['reported_depth'],reported_nodes=z['metadata']['reported_nodes']))
pairs=[]
for name in ('semantic','unit'):
 for f in D['roots']:
  for limit in (1024,16384):
   rr=[next(z for z in X['rows'] if z['profile']==name+s and z['root']==f['id'] and z['limit']==limit) for s in ('-c1over2','-c1over1','-c2over1')];ref=next(r for r in refs if r['root']==f['id']);pairs.append(dict(profile=name,root=f['id'],nodes=limit,actual_actions=[z['action'] for z in rr],actual_depths=[z['metadata']['reported_depth'] for z in rr],actual_nodes=[z['metadata']['reported_nodes'] for z in rr],changed_actions=len({z['action'] for z in rr})>1,rounded_reference_argmax_changed=len({tuple(ref['controls'][name+s]['rounded']['argmax']) for s in ('-c1over2','-c1over1','-c2over1')})>1))
out=dict(complete=True,actual_mature_queries=48,pairs=pairs,mature_changed_action_groups=sum(p['changed_actions'] for p in pairs),rounded_fullq0_changed_argmax_groups=sum(p['rounded_reference_argmax_changed'] for p in pairs),D2_terminal_leaf_visits=terminal_visits,reference=refs,seconds=time.monotonic()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task272/result.json').read_bytes()).hexdigest(),scope='Actual48queries/readbacks/PVs/fullhistory verified; purecompleteD2 exactrationalpositivecommon scale invariant(no terminalD2leaves); roundedcontrols independentlycomputed. Maturechanges candidateheuristic/budget interactions, notcausalidentificationofsinglepruningrule. NoallChess/generalpriorabsenceclaim.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:out[k] for k in ('complete','actual_mature_queries','mature_changed_action_groups','rounded_fullq0_changed_argmax_groups','D2_terminal_leaf_visits','seconds')})
