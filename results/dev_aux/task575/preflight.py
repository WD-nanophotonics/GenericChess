import sys,json,time,re,hashlib,os
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task575';D=R/'results/dev_aux/task574/declaration.json';d=json.loads(D.read_bytes())
for n in [360,364,381,509,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
from warm_adapter import ControlledEngine
sys.path.insert(0,str(O));from controller_pair import native_game
A.EXE=R/'.local_agent/yaneura27/yaneura-material1-hand-see.exe';assert hashlib.sha256(A.EXE.read_bytes()).hexdigest()==d['executable_sha256'];assert not (O/'games.jsonl').exists();pd=dict(question='Differentcandidate/opponentprices fullhistory/warmbothroles reproduce actualphysicalpaths?',study_sha256=hashlib.sha256(D.read_bytes()).hexdigest(),profiles=[0,1],root_index=0,colors=[0,1],repetitions=2,nodes=1024,cap=24,fuse=120,expected_cost='4actualshortgames max96go under15seconds/120fuse; firstrepetitioneachcolor reused900panel, no rerunforbenchmark',scope='Finiteinitialpair qualification notall100pricecontexts; fullmetadata/rawquery/priceACK/Pythonrules check, no sourcefitness');(O/'declaration.json').write_text(json.dumps(pd,indent=2),encoding='utf-8');start=time.monotonic();gs=[];acks=[];pairs=[]
semq=lambda q:{k:([' '.join(re.sub(r'\b(?:time|nps) \d+','',l).split()) for l in v] if k=='lines' else v) for k,v in q.items() if k!='seconds'}
semg=lambda g:{k:([semq(q) for q in v] if k=='queries' else v) for k,v in g.items() if k!='seconds'}
with (O/'queries.jsonl').open('w') as qj,(O/'games.jsonl').open('w') as gj:
 for c in [0,1]:
  rr=[]
  for rep in range(2):
   G.stop();ec=ControlledEngine(d['profiles'][0]['weights'],qj,'warm_game');eu=ControlledEngine(d['profiles'][1]['weights'],qj,'warm_game');acks.extend([dict(role=role,weights=e.w,prices=e.prices) for role,e in [('candidate',ec),('opponent',eu)]]);ec.begin_game();eu.begin_game()
   try:g=native_game(ec,eu,ec.w,d['roots'][0],c,None,d,start+120)
   finally:ec.close();eu.close()
   g.update(candidate_profile=0,opponent_profile=1);gj.write(json.dumps(g)+'\n');gj.flush();os.fsync(gj.fileno());gs.append(g);rr.append(g)
  assert semg(rr[0])==semg(rr[1]);pairs.append(dict(color=c,non_time_equal=True,cached_tournament_source=dict(file='results/dev_aux/task575/games.jsonl',line=2*c+1)))
# IndependentPythonrule/material/checkpoint/metadata verification of realnative paths.
expected=[];pv=0;actions=0
for g in gs:
 b,keys,checks,movers=G.full_root(g['root']);h=list(g['root']['history']);rolecounts={}
 for ply,(a,q) in enumerate(zip(g['actions'],g['queries'])):
  assert G.terminal(b,keys,checks,movers) is None;role='candidate' if b.turn==g['color'] else 'opponent';w=g['weights'] if role=='candidate' else g['opponent_weights'];assert q['player']==role and q['weights']==w and q['history']==h and q['initial_sfen']==g['root']['initial_sfen'] and q['ply']==ply and q['bestmove']==a['move'] and q['nodes_limit']==1024;assert q['reset_policy']=='warm_game' and q['cold_isready']==[] and q['query_index_in_game']==rolecounts.get(role,0);rolecounts[role]=rolecounts.get(role,0)+1;assert q['game_start_ready'][-1]=='readyok';state=q['state'].split(' ',7);mat=A.material(b,w);assert int(state[3])==int(state[4])==mat and int(state[5])==(mat if b.turn==0 else -mat);pv+=V.query(q);expected.append(V.bare(q));m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves and a['before_sfen']==b.sfen();cap=b.piece_at(m.to_square);moving=b.piece_at(m.from_square) if m.from_square is not None else None;assert a['captured']==(str(cap) if cap else None) and a['moving']==(str(moving) if moving else None) and a['promotion']==bool(m.promotion) and a['drop']==m.drop_piece_type;assert a['actor']==b.turn;movers.append(b.turn);b.push(m);h.append(a['move']);keys.append(G.key(b));checks.append(b.is_check());assert a['after_sfen']==b.sfen();actions+=1
 assert len(g['actions'])==len(g['queries']);term=G.terminal(b,keys,checks,movers);assert g['termination']==(term or dict(kind='cap24',winner=None));qty=G.quantity(b,g['color']);goal=Fraction(qty,19) if not term else Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==g['color'] else -32);assert qty==g['raw_quantity'] and str(goal)==g['goal'] and b.sfen()==g['final_sfen']
assert expected==[json.loads(x) for x in (O/'queries.jsonl').open()];s=(R/'results/dev_aux/task522/audit.py').read_text();exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'ACKtablecheck','exec'));entries=tables(acks);out=dict(status='PASS',actual_games=len(gs),actual_go=len(expected),PV_moves=pv,Python_actions=actions,price_ACK_entries=entries,price_acks=acks,pairs=pairs,seconds=time.monotonic()-start,scope=pd['scope']);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['price_acks','pairs']})
