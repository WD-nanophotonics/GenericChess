from pathlib import Path
import json,chess,random
from fractions import Fraction as F
from collections import Counter
R=Path.cwd();O=R/'results/dev_aux/task1015';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task1012/plan.json').read_bytes());roots=[r for r in json.loads((R/'results/dev_aux/task1008/roots.json').read_bytes())['roots'] if r['composition_ordinal']<8];raw=iter(map(json.loads,(R/'results/dev_aux/task1013/queries.jsonl').read_text().splitlines()));games=list(map(json.loads,(R/'results/dev_aux/task1013/games.jsonl').read_text().splitlines()));assert len(games)==384;seen=[];pv=go=actions=draws=tb=0
for g in games:
 assert g['root'] in roots;seen.append((g['price'],g['opponent'],g['root']['seed'],g['color']));b=chess.Board(g['root']['fen']);qs=iter(g['queries']);randturn=0;expected_weights=dict(plan['candidate_other'],R=g['price']);assert g['weights']==expected_weights
 for ply,a in enumerate(g['actions']):
  assert b.outcome(claim_draw=False) is None;assert a['before']==b.fen() and a['actor']==b.turn;actor=b.turn
  if actor==g['color'] or g['opponent']=='unit_search':
   q=next(qs);assert q==next(raw);assert q['ply']==ply and q['move']==a['move'] and q['game']==g['game'];assert q['weights']==(expected_weights if actor==g['color'] else plan['opponent_weights']);m=q['metadata'];assert m['root_fen']==g['root']['fen'] and m['full_history']==[a0['move'] for a0 in g['actions'][:ply]] and m['search_arm']==dict(kind='nodes',limit=64);assert a['draw'] is None
   for line in m['uci_info']:
    fs=line.split()
    if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0;tb+=1
    if 'pv' in fs:
     child=b.copy()
     for text in fs[fs.index('pv')+1:]:assert chess.Move.from_uci(text) in child.legal_moves;child.push_uci(text);pv+=1
   go+=1
  else:
   seed=(plan['random_seed_base']+2*g['root']['seed']+int(g['color']))*100+randturn;legal=sorted(m.uci() for m in b.legal_moves);idx=random.Random(seed).randrange(len(legal));assert a['draw']==dict(seed=seed,index=idx,legal=legal,opponent_turn=randturn);assert a['move']==legal[idx];randturn+=1;draws+=1
  assert chess.Move.from_uci(a['move']) in b.legal_moves;b.push_uci(a['move']);assert a['after']==b.fen();actions+=1
 assert next(qs,None) is None and b.fen()==g['final_fen'];out=b.outcome(claim_draw=False);term=dict(kind='cap16',winner=None) if out is None else dict(kind=out.termination.name,winner=out.winner);label='C' if out is None else 'D' if out.winner is None else 'W' if out.winner==g['color'] else 'L';assert term==g['termination'] and label==g['label'];assert len(g['actions'])==16 if out is None else len(g['actions'])<=16
assert next(raw,None) is None;expected=[(price,opp,r['seed'],color) for price in [64,90,102] for opp in ['unit_search','uniform_random'] for r in roots for color in [False,True]];assert seen==expected
acks=json.loads((R/'results/dev_aux/task1013/price_acks.json').read_bytes())
for a in acks:
 w=a['weights'];assert a['ack']['alignment']==3 and {int(k):v for k,v in a['ack']['prices'].items()}=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 for p in a['probes']:assert abs(p['measured']-w[p['type']]/208)<=.011
rows=[];pairs=[]
def value(g):return {'W':1,'L':-1,'D':0,'C':0}[g['label']]
for opp in plan['opponents']:
 for price in plan['profiles']:
  xx=[g for g in games if g['price']==price and g['opponent']==opp];counts=Counter(g['label'] for g in xx);rows.append(dict(price=price,opponent=opp,N=len(xx),counts=dict(counts),J16=str(F(sum(map(value,xx)),len(xx)))))
 for seed in sorted(r['seed'] for r in roots):
  cases={(g['price'],g['color']):g for g in games if g['root']['seed']==seed and g['opponent']==opp}
  if opp=='unit_search':assert [a['move'] for a in cases[(90,False)]['actions']]==[a['move'] for a in cases[(90,True)]['actions']];assert value(cases[(90,False)])+value(cases[(90,True)])==0
  pairs.append(dict(seed=seed,opponent=opp,delta102vs64=str(F(sum(value(cases[(102,c)])-value(cases[(64,c)]) for c in [False,True]),2)),delta102vs90=str(F(sum(value(cases[(102,c)])-value(cases[(90,c)]) for c in [False,True]),2))))
(O/'result.json').write_text(json.dumps(dict(status='PASS384_REAL_SHORT_POLICY_GAMES_AND3984_QUERIES',rows=rows,pairs=pairs,counters=dict(games=len(games),go=go,PVmoves=pv,actions=actions,randomdraws=draws,tbhits_zero_lines=tb,price_acks=len(acks)),new_go=0,scope='Fullactualstandardrulesautomaticoutcome16ply; Cnotdrawnotmaterialreward; coldgameswarmwithincompletehistory; oraclelabelsnotfedtoanymove'),indent=2),encoding='utf-8');print(rows);print('AUDIT',go,actions,pv,draws)
