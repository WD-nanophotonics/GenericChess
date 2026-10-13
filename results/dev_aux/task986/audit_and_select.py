from pathlib import Path
import json,chess,hashlib,random
from fractions import Fraction as F
from collections import Counter
R=Path.cwd();O=R/'results/dev_aux/task988';O.mkdir(exist_ok=False)
roots=json.loads((R/'results/dev_aux/task984/roots.json').read_bytes());api={r['seed']:r for r in map(json.loads,(R/'results/dev_aux/task985/responses.jsonl').read_text().splitlines())};qs=list(map(json.loads,(R/'results/dev_aux/task987/queries.jsonl').read_text().splitlines()));assert len(qs)==128
categories={'win':1,'loss':-1,'draw':0,'cursed-win':0,'blessed-loss':0};counts=Counter();checked=0;action_labels={};qual=[]
for r in roots['trace']:
 assert random.Random(r['seed']).sample(range(64),5)==r['squares'];b=chess.Board(None)
 for s,t,c in zip(r['squares'],[6,4,2,6,4],[True,True,True,False,False]):b.set_piece_at(s,chess.Piece(t,c))
 b.turn=not(r['index']%2);assert b.fen()==r['fen'];assert sorted(m.uci() for m in b.legal_moves)==r['legal']
for r in roots['roots']:
 a=api[r['seed']];assert a['fen']==r['fen'] and hashlib.sha256(a['raw_utf8'].encode()).hexdigest()==a['sha256'];z=json.loads(a['raw_utf8']);b=chess.Board(r['fen']);assert b.is_valid() and not b.is_game_over();assert sorted(m['uci'] for m in z['moves'])==r['legal'];counts[z['category']]+=1
 for m in z['moves']:
  b.push_uci(m['uci']);assert b.is_checkmate()==m['checkmate'] and b.is_stalemate()==m['stalemate'] and b.is_insufficient_material()==m['insufficient_material'];b.pop()
 action_labels[r['seed']]={m['uci']:-categories[m['category']] if m['category'] in categories else None for m in z['moves']}
 assert all(v is not None for v in action_labels[r['seed']].values());assert max(action_labels[r['seed']].values())==categories[z['category']]
for q in qs:
 r=q['root'];assert r in roots['roots'] and q['move'] in r['legal'];w=dict(P=208,N=90,B=208,R=q['price'],Q=208,K=0);assert q['table_ack']['alignment']==3 and {int(k):v for k,v in q['table_ack']['prices'].items()}=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 for p in q['leaf_probes']:assert abs(p['measured']-w[p['type']]/208)<=.011
 for line in q['metadata']['uci_info']:
  fs=line.split()
  if 'pv' in fs:
   b=chess.Board(r['fen'])
   for move in fs[fs.index('pv')+1:]:assert chess.Move.from_uci(move) in b.legal_moves;b.push_uci(move);checked+=1
 qual.append(dict(price=q['price'],seed=r['seed'],phase=r['phase'],move=q['move'],label=action_labels[r['seed']][q['move']],root_label=max(action_labels[r['seed']].values()),all_legal_labels=action_labels[r['seed']]))
train=[]
for p in [90,180,360,1448]:
 x=[r for r in qual if r['phase']=='train' and r['price']==p];assert len(x)==16;train.append(dict(price=p,N=16,score=str(F(sum(r['label'] for r in x),16)),regret=str(F(sum(r['root_label']-r['label'] for r in x),16)),labels=dict(Counter(r['label'] for r in x))))
best=max(F(r['score']) for r in train);selected=next(r['price'] for r in train if F(r['score'])==best)
(O/'training_endpoint.json').write_text(json.dumps(dict(status='FROZEN_TRAIN_ONLY_EXACTWDL_ENDPOINT',train=train,selected=selected,objective='chosenaction WDL withoptimalcontinuation',holdout_not_used_for_selection=True),indent=2),encoding='utf-8')
(O/'qualified_cases.json').write_text(json.dumps(qual,indent=2),encoding='utf-8');(O/'audit.json').write_text(json.dumps(dict(status='PASS_ALL32API_LEGAL_CATEGORIES_AND128_ENGINE_QUERIES',roots=32,queries=128,PVmoves=checked,rootcategories=dict(counts),new_go=0,limits='OracleAPItrusted source labels, notindependentretrograde regeneration; alllegal coverage/perspective/Bellman andterminalcontrolschecked'),indent=2),encoding='utf-8');print(train,selected,counts)
