"""Serial actual root-price-scale queries and exact finite material controls."""
import json,math,time,sys,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task172'
s=importlib.util.spec_from_file_location('R172',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A
D=json.loads((O/'declaration.json').read_bytes())
def configure(e,w,deadline):
 assert set(w)==set('PNBRQK') and w['K']==0 and all(isinstance(w[k],int) and 1<=w[k]<=3328 for k in 'PNBRQ')
 config=O/'variant.ini';line=' '.join(k.lower()+':'+str(w[k]) for k in 'PNBRQ');config.write_bytes(('[aux_short:chess]\npieceValueMg = '+line+'\npieceValueEg = '+line+'\n').encode())
 names={x.split('option name ',1)[1].split(' type ',1)[0] for x in e.handshake if x.startswith('option name ')}
 for name,v in (('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(config)),('UCI_Variant','aux_short')):
  assert name in names;A.guard(deadline,P.stop);e.send('setoption name '+name+' value '+str(v));reply=e.ready()
  if name=='UCI_Variant':assert any(x.startswith('info string variant aux_short files 8 ranks 8 ') for x in reply)
 probes=[]
 for k in 'PNBRQ':
  fen='7k/8/8/3'+k+'4/8/8/8/K7 w - - 0 1';e.send('position fen '+fen);e.send('eval');reply=e.ready();value=[x for x in reply if x.startswith('Final evaluation')];assert len(value)==1;measured=float(value[0].split()[2]);assert abs(measured-w[k]/208)<=.011
  probes.append(dict(type=k,fen=fen,measured=measured,expected=w[k]/208))
 e.send('setoption name UCI_Variant value aux_short');reply=e.ready();acks=[x for x in reply if x.startswith('info string DEV_AUX alignment ')];assert len(acks)==1
 f=acks[0].split();assert int(f[4])==3;prices={int(x.split(':')[0]):list(map(int,x.split(':')[1:])) for x in f[5:]};assert prices=={i+1:[w[k],w[k]] for i,k in enumerate('PNBRQ')}
 e.send('ucinewgame');e.ready();return probes,dict(raw=acks[0],prices=prices,alignment=3)
def search(e,b,arm,deadline):
 A.guard(deadline,P.stop);history=[m.uci() for m in b.move_stack];e.send('position fen '+b.root().fen()+' moves '+' '.join(history));e.send('go '+arm['kind']+' '+str(arm['limit']));lines=e.until(lambda t:t.startswith('bestmove '));chosen=chess.Move.from_uci(lines[-1].split()[1]);assert chosen in b.legal_moves;e.ready()
 nodes=depth=None;score=None
 for text in lines[:-1]:
  f=text.split()
  if 'nodes' in f:nodes=int(f[f.index('nodes')+1])
  if 'depth' in f:depth=int(f[f.index('depth')+1])
  if 'score' in f:
   idx=f.index('score');score=dict(kind=f[idx+1],value=int(f[idx+2]))
 return chosen.uci(),dict(root_fen=b.root().fen(),full_history=history,reported_nodes=nodes,reported_depth=depth,last_score=score,uci_info=lines[:-1],backend=e.backend,search_arm=arm)
def material(b,c,w):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==c else -1000000)
 return sum(w[k]*(len(b.pieces(i+1,c))-len(b.pieces(i+1,not c))) for i,k in enumerate('PNBRQ'))
def oracle(b,w):
 color=b.turn;rows=[];nodes=0
 for m in sorted(b.legal_moves,key=lambda x:x.uci()):
  b.push(m)
  if b.is_game_over(claim_draw=False):values=[material(b,color,w)];nodes+=1
  else:
   values=[]
   for reply in sorted(b.legal_moves,key=lambda x:x.uci()):
    b.push(reply);values.append(material(b,color,w));nodes+=1;b.pop()
  rows.append(dict(move=m.uci(),worst=min(values),reply_count=len(values)));b.pop()
 best=max(x['worst'] for x in rows);return dict(value=best,best_moves=[x['move'] for x in rows if x['worst']==best],rows=rows,leaf_nodes=nodes)
def execute():
 if (O/'result.json').exists():raise FileExistsError('frozen')
 # Do not overlap another owned engine: require this segment's learning batch finished.
 assert json.loads((R/'results/dev_aux/task169/status.json').read_bytes())['status']=='COMPLETE'
 P.stop();binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];started=time.monotonic();deadline=started+D['deadline_seconds'];rows=[];oracles=[]
 for profile,base in D['profiles'].items():
  for oi,fixture in enumerate(D['roots']):
   b=P.board(fixture);scaled_oracles=[]
   for numerator,denominator in D['scales']:
    w={k:v*numerator//denominator for k,v in base.items()};assert all(v*numerator%denominator==0 for v in base.values());q=oracle(b,w);scaled_oracles.append(q);oracles.append(dict(profile=profile,root_index=oi,scale=[numerator,denominator],weights=w,oracle=q))
   assert all(q['best_moves']==scaled_oracles[0]['best_moves'] for q in scaled_oracles)
  for scale in D['scales']:
   w={k:v*scale[0]//scale[1] for k,v in base.items()}
   for arm in D['search_arms']:
    e=M.start(binary,3,deadline,P.stop)
    try:
     for oi,fixture in enumerate(D['roots']):
      probes,ack=configure(e,w,deadline);b=P.board(fixture);move,meta=search(e,b.copy(stack=True),arm,deadline);rows.append(dict(profile=profile,scale=scale,weights=w,search_arm=arm,root_index=oi,root=fixture,move=move,metadata=meta,probes=probes,table_ack=ack))
    finally:e.close()
 pairs=[]
 for profile in D['profiles']:
  for arm in D['search_arms']:
   for oi in range(len(D['roots'])):
    group=[next(r for r in rows if r['profile']==profile and r['scale']==sc and r['search_arm']==arm and r['root_index']==oi) for sc in D['scales']]
    pairs.append(dict(profile=profile,root_index=oi,search_arm=arm,moves=[r['move'] for r in group],same_actions=len({r['move'] for r in group})==1,nodes=[r['metadata']['reported_nodes'] for r in group],depths=[r['metadata']['reported_depth'] for r in group]))
 out=dict(complete=True,searches=len(rows),rows=rows,oracles=oracles,groups=pairs,changed_scale_groups=sum(not g['same_actions'] for g in pairs),wall_seconds=time.monotonic()-started,binary_sha256=D['binary_sha256'],declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),scope='Actual selective/q mature queries, exactfinite2ply material scalecontrol isdifferenttree; actionchange notstrength/gain/bug orprovenlearningcause.')
 A.atomic_json(O/'result.json',out);print(json.dumps(dict(complete=True,searches=len(rows),seconds=out['wall_seconds'],changed=sum(not g['same_actions'] for g in pairs),groups=len(pairs))))
if __name__=='__main__':execute()
