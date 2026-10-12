import sys,json,time,random,os,hashlib
from pathlib import Path
from fractions import Fraction
R=Path.cwd()
sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
A.EXE=R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe';A.validate_search=V.query
d=json.loads((R/'results/dev_aux/task410/declaration.json').read_text(encoding='utf-8'));assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256']
def random_game(ec,w,f,c,journal,deadline):
 G.stop();t=time.monotonic();b,keys,checks,movers=G.full_root(f);h=list(f['history']);acts=[];qs=[];term=G.terminal(b,keys,checks,movers)
 rng=random.Random(d['seed_base']+2*f['index']+c)
 for ply in range(d['cap']):
  if term:break
  assert time.monotonic()<deadline,'predeclared fuse';G.stop();actor=b.turn
  draw=None
  if actor==c:
   q=ec.search(f['initial_sfen'],h,d['nodes']);V.query(q);assert q['weights']==w;q['player']='candidate';q['ply']=ply;qs.append(q);u=q['bestmove']
  else:
   legal=sorted(m.usi() for m in b.legal_moves);i=rng.randrange(len(legal));u=legal[i];draw={'legal':legal,'index':i,'seed':d['seed_base']+2*f['index']+c}
  m=A.shogi.Move.from_usi(u);assert m in b.legal_moves;before=b.sfen();captured=b.piece_at(m.to_square);moving=b.piece_at(m.from_square) if m.from_square is not None else None;movers.append(actor);b.push(m);h.append(u);acts.append({'move':u,'actor':actor,'captured':str(captured) if captured else None,'moving':str(moving) if moving else None,'promotion':bool(m.promotion),'drop':m.drop_piece_type,'before_sfen':before,'after_sfen':b.sfen(),'random_draw':draw});keys.append(G.key(b));checks.append(b.is_check());term=G.terminal(b,keys,checks,movers)
 qty=G.quantity(b,c);goal=Fraction(qty,19) if not term else (Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==c else -32))
 out=dict(weights=w,root=f,color=c,actions=acts,queries=qs,termination=term or {'kind':'cap24','winner':None},final_sfen=b.sfen(),raw_quantity=qty,goal=str(goal),seconds=time.monotonic()-t)
 journal.write(json.dumps(out)+'\n');journal.flush();os.fsync(journal.fileno());return out
arm=sys.argv[1];assert arm in d['opponents'];O=R/'results/dev_aux'/('task411' if arm=='unit' else 'task412');O.mkdir(exist_ok=True);assert not (O/'games.jsonl').exists();t0=time.monotonic();rows=[];prices=[]
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(d['fixed_unit'],qj) if arm=='unit' else None
 try:
  if eu:prices.append({'role':'unit','weights':eu.w,'prices':eu.prices})
  for p in d['profiles']:
   ec=A.Engine(p['weights'],qj)
   try:
    prices.append({'role':'candidate','weights':ec.w,'prices':ec.prices})
    for f in d['roots']:
     for c in (0,1):
      g=G.game(ec,eu,p['weights'],f,c,gj,cap=d['cap'],nodes=d['nodes'],deadline=t0+300) if eu else random_game(ec,p['weights'],f,c,gj,t0+300)
      term=g['termination'];sg=Fraction(g['goal'])
      if term['winner'] is not None:sg=(1 if term['winner']==c else -1)*(32+Fraction(d['cap']-len(g['actions']),d['cap']))
      rows.append(dict(names=p['names'],weights=p['weights'],root_index=f['index'],color=c,goal=g['goal'],speed_goal=str(sg),termination=term,plies=len(g['actions']),go=len(g['queries']),seconds=g['seconds']))
   finally:ec.close()
   print(arm,p['names'],len(rows),flush=True)
 finally:
  if eu:eu.close()
out=dict(arm=arm,seconds=time.monotonic()-t0,games=len(rows),actual_go=sum(x['go'] for x in rows),rows=rows,price_acknowledgements=prices,declaration_sha256=hashlib.sha256((R/'results/dev_aux/task410/declaration.json').read_bytes()).hexdigest());(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['rows','price_acknowledgements']})
