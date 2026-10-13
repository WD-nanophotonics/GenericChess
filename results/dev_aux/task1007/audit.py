from pathlib import Path
import json,chess,hashlib,random
from fractions import Fraction as F
from collections import Counter
R=Path.cwd();O=R/'results/dev_aux/task1014';O.mkdir(exist_ok=False);data=json.loads((R/'results/dev_aux/task1008/roots.json').read_bytes());mirrors=json.loads((R/'results/dev_aux/task1010/roots.json').read_bytes());api={r['seed']:r for r in map(json.loads,(R/'results/dev_aux/task1009/responses.jsonl').read_text().splitlines())};q=list(map(json.loads,(R/'results/dev_aux/task1011/queries.jsonl').read_text().splitlines()));values={'win':1,'loss':-1,'draw':0,'cursed-win':0,'blessed-loss':0};rootlabels={};out=[];pv=0;tb=0
assert len(data['trace'])==1024 and len(q)==384 and len(api)==64
for r in data['trace']:
 sq=random.Random(r['seed']).sample([chess.square(f,t) for t in range(1,6) for f in range(1,6)],len(r['types']));assert sq==r['squares'];b=chess.Board(None)
 for s,t,c in zip(sq,r['types'],r['colors']):b.set_piece_at(s,chess.Piece(t,bool(c)))
 b.turn=not((r['index']//4)%2);assert b.fen()==r['fen'];assert sorted(m.uci() for m in b.legal_moves)==r['legal']
for r in data['roots']:
 a=api[r['seed']];assert a['fen']==r['fen'] and hashlib.sha256(a['raw_utf8'].encode()).hexdigest()==a['sha256'];z=json.loads(a['raw_utf8']);assert sorted(m['uci'] for m in z['moves'])==r['legal'];labs={m['uci']:-values[m['category']] for m in z['moves']};assert max(labs.values())==values[z['category']];rootlabels[r['seed']]=labs
for x in q:
 r=x['root'];assert r in mirrors['roots'];w=dict(P=208,N=90,B=208,R=x['price'],Q=208,K=0);assert x['table_ack']['alignment']==3 and {int(k):v for k,v in x['table_ack']['prices'].items()}=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')};assert x['metadata']['search_arm']==dict(kind='nodes',limit=64)
 for p in x['leaf_probes']:assert abs(p['measured']-w[p['type']]/208)<=.011
 original=chess.Move.from_uci(x['move']);original=chess.Move(chess.square_mirror(original.from_square),chess.square_mirror(original.to_square),promotion=original.promotion) if r['mirror'] else original;labs=rootlabels[r['seed']];value=labs[original.uci()]
 for line in x['metadata']['uci_info']:
  fs=line.split()
  if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0;tb+=1
  if 'pv' in fs:
   b=chess.Board(r['fen'])
   for m in fs[fs.index('pv')+1:]:assert chess.Move.from_uci(m) in b.legal_moves;b.push_uci(m);pv+=1
 out.append(dict(price=x['price'],seed=r['seed'],mirror=r['mirror'],composition=r['composition'],move=x['move'],label=value,root_label=max(labs.values()),legalrange=max(labs.values())-min(labs.values())))
rows=[];families=[]
for mirror in [False,True]:
 for price in [64,102,1718]:
  xx=[r for r in out if r['mirror']==mirror and r['price']==price];assert len(xx)==64;rows.append(dict(mirror=mirror,price=price,N=64,J=str(F(sum(r['label'] for r in xx),64)),regret=str(F(sum(r['root_label']-r['label'] for r in xx),64)),counts=dict(Counter(r['label'] for r in xx))))
for seed in sorted(rootlabels):
 xx=[r for r in out if r['seed']==seed];by={(r['price'],r['mirror']):r for r in xx};delta={str(price):str(F(sum(by[(price,c)]['label']-by[(64,c)]['label'] for c in [False,True]),2)) for price in [102,1718]};families.append(dict(seed=seed,composition=xx[0]['composition'],delta=delta,legalrange=xx[0]['legalrange'],chosenrange=max(r['label'] for r in xx)-min(r['label'] for r in xx)))
(O/'result.json').write_text(json.dumps(dict(status='PASS_NEW64_FAMILIES_AND384_MIRROR_QUERIES',rows=rows,families=families,cases=out,PVmoves=pv,tbhits_zero_lines=tb,new_go=0,limits='Mirrorsmechanicalisomorphism labelschecked838legaltransitions; paircolorsonefamily not128independent. No refit/holdoutextension/unknownselectedactiondrop'),indent=2),encoding='utf-8');print(rows);print('INFORMATION',sum(f['legalrange']>0 for f in families),sum(f['chosenrange']>0 for f in families))
