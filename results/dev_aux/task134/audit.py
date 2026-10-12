"""Independent replay of saved2ply trees, exact2x2 objective/opponent arithmetic."""
import json,hashlib,time,sys
from fractions import Fraction as F
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task134';O.mkdir(exist_ok=True);S=R/'results/dev_aux/task133'
d=json.loads((S/'declaration.json').read_bytes());data=json.loads((S/'result.json').read_bytes());assert data['complete']
started=time.monotonic();edges=0;audited=[]
def values(b,color,w):
 v={chess.piece_symbol(t).upper():len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6)}
 out=b.outcome(claim_draw=False);raw=sum(v[k]*w[k] for k in v)
 terminal=None if out is None else dict(kind=out.termination.name,winner=out.winner)
 return v,raw,terminal
for root in d['roots']:
 pair=[next(x for x in data['rows'] if x['root_id']==root['id'] and x['arm']==arm) for arm in ('unit','learned')]
 assert [[(a['move'],[r['move'] for r in a['replies']]) for a in x['actions']] for x in pair][0]==[[(a['move'],[r['move'] for r in a['replies']]) for a in x['actions']] for x in pair][1]
 controls={}
 for arm,x in zip(('unit','learned'),pair):
  b=chess.Board()
  for m in root['history']:b.push_uci(m)
  assert b.fen()==root['fen'];assert x['metadata']['full_history']==root['history']
  assert x['mature'] in [m.uci() for m in b.legal_moves]
  assert [a['move'] for a in x['actions']]==sorted(m.uci() for m in b.legal_moves)
  scores={}
  for a in x['actions']:
   b.push_uci(a['move']);terminal=b.is_game_over(claim_draw=False)
   assert [r['move'] for r in a['replies']]==([None] if terminal else sorted(m.uci() for m in b.legal_moves))
   vv=[];uu=[]
   for r in a['replies']:
    if r['move'] is not None:b.push_uci(r['move'])
    v,raw,term=values(b,root['agent_color'],d['profiles'][arm]);assert v==r['vector'] and raw==r['raw_material'] and term==r['terminal']
    reward=raw if term is None else (0 if term['winner'] is None else (1000000 if term['winner']==root['agent_color'] else -1000000))
    unit=sum(v.values()) if term is None else reward
    assert reward==r['value'];vv.append(reward);uu.append(unit);edges+=1
    if r['move'] is not None:b.pop()
   scores[a['move']]={'material_minimax':F(min(vv)),'material_random':F(sum(vv),len(vv)),'unit_minimax':F(min(uu)),'unit_random':F(sum(uu),len(uu))}
   b.pop()
  cells={}
  for metric in next(iter(scores.values())):
   best=max(a[metric] for a in scores.values());cells[metric]=dict(best_fraction=str(best),actions=[m for m,a in scores.items() if a[metric]==best],mature_regret_fraction=str(best-scores[x['mature']][metric]))
  controls[arm]=cells
 learned=controls['learned'];pairs={'leaf_at_minimax':('unit_minimax','material_minimax'),'leaf_at_random':('unit_random','material_random'),'opponent_at_unit':('unit_minimax','unit_random'),'opponent_at_material':('material_minimax','material_random')}
 overlaps={k:sorted(set(learned[a]['actions'])&set(learned[b]['actions'])) for k,(a,b) in pairs.items()}
 audited.append(dict(root_id=root['id'],controls=controls,intersection=overlaps,disjoint={k:not v for k,v in overlaps.items()},terminal_reply_edges=sum(r['terminal'] is not None for a in pair[0]['actions'] for r in a['replies'])))
result=dict(complete=True,source_declaration_sha256=hashlib.sha256((S/'declaration.json').read_bytes()).hexdigest(),source_result_sha256=hashlib.sha256((S/'result.json').read_bytes()).hexdigest(),verified_reply_edges=edges,seconds=time.monotonic()-started,roots=audited,disjoint_count={k:sum(x['disjoint'][k] for x in audited) for k in pairs},scope='Exposedselected8roots; exactmatched2ply objective/opponent changes. Mature depth/selectivity/priors remain unseparated. No policy dominance or necessarySEEbuildclaim.')
(O/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('complete','verified_reply_edges','seconds','disjoint_count','scope')},indent=2))
