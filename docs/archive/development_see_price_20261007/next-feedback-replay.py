import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'.local_agent/certificate_source/python-chess')]
import scripts.chess_development as d
p=ROOT/'.local_agent/see-feedback-20261007';cohort=sys.argv[1]
raw=(p/(cohort+'.json')).read_bytes();v=json.loads(raw);assert v['complete']
assert len(v['games'])==12 and cohort in ('price','original')
build=json.loads((p/'declaration.json').read_bytes())
c=d.compile_ruleset_for_execution(d.build_western_chess_ruleset());out=p/(cohort+'-replay.json');assert not out.exists()
report=dict(complete=False,input_sha256=hashlib.sha256(raw).hexdigest(),games=[],errors=[])
for i,g in enumerate(v['games']):
 other=d.UciOpponent(None,g['initial_fen'],1);s,_=d.replay_prefix(g['initial_fen'],c,g['opening_uci'],(other,));cost={}
 for r in g['moves']:
  legal={d.uci(a):a for a in d.iter_legal_actions(s,c)}
  assert set(legal)=={m.uci() for m in other.board.legal_moves}
  assert r['legal'] and r['move'] in legal and r['side']==s.position.side_to_move and r['ply']==s.ply_count
  mode=r.get('leaf_mode','reference');z=cost.setdefault(mode,dict(calls=0,wall_seconds=0.,reported_nodes=0));z['calls']+=1;z['wall_seconds']+=r['wall_seconds']
  key='opponent_nodes' if mode=='reference' else 'engine_nodes';n=r.get(key);z['reported_nodes']=None if n is None or z['reported_nodes'] is None else z['reported_nodes']+n
  if mode!='reference':
   assert r['leaf_binary_sha256']==build['binaries'][mode]['sha256'] and r['requested_seconds']==1 and r['policy']==g['table']
   assert mode==cohort and r['side']==g['candidate_color']
   assert r['reason']=='uci_bestmove'
  board=other.board.copy(stack=True)
  for move in r['pv']:assert move in {m.uci() for m in board.legal_moves};board.push_uci(move)
  s=d.apply_action(s,legal[r['move']],c);other.push(r['move'],s)
 assert d.record_value(s)==g['final_state'] and len(s.history)==len(g['opening_uci'])+len(g['moves'])+1
 report['games'].append(dict(index=i,id=g['id'],table=g['table'],candidate_color=g['candidate_color'],opponent_setting=build['opponent_setting'],plies=len(g['moves']),prefix_plies=len(g['opening_uci']),end=g['end'],winner=g['winner'],finished=g['finished'],cost=cost))
 d.write_record(out,report,indent=None)
report.update(complete=True,played_plies=sum(g['plies'] for g in report['games']),prefix_plies=sum(g['prefix_plies'] for g in report['games']));d.write_record(out,report)
print(cohort,'replayed',len(report['games']),report['played_plies'],'zero mismatches',flush=True)
