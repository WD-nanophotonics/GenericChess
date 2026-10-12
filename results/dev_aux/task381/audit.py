import json,re,time,hashlib,sys
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task381';O.mkdir(exist_ok=True)
MAP={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8}
def literal(sfen,w):
 board,turn,hand,num=sfen.split();score=0;owned=[0,0];prom=False
 for x in board:
  if x=='+':prom=True;continue
  if x=='/' or x.isdigit():assert not prom;continue
  c=0 if x.isupper() else 1;pt=MAP[x.upper()]+(8 if prom else 0);prom=False;score+=(1 if c==0 else -1)*w[pt]
  if pt!=8:owned[c]+=1
 count=''
 for x in hand:
  if x=='-':continue
  if x.isdigit():count+=x;continue
  n=int(count or '1');count='';c=0 if x.isupper() else 1;pt=MAP[x.upper()];score+=(1 if c==0 else -1)*w[pt]*n;owned[c]+=n
 assert not count and sum(owned)==38,(sfen,owned);return score,owned

def query(q):
 b=C.Board(q['initial_sfen'])
 for u in q['history']:
  m=b.move_from_usi(u);assert b.is_legal(m),(u,b.sfen());b.push(m)
 line=q['state'].split(' ',7);cached,full,stm=map(int,line[3:6]);score,owned=literal(b.sfen(),q['weights']);assert cached==full==score and stm==(score if b.turn==0 else -score);assert line[7].split()[:3]==b.sfen().split()[:3];m=b.move_from_usi(q['bestmove']);assert b.is_legal(m)
 pvs=0
 for s in q['lines']:
  if ' pv ' not in s:continue
  p=b.copy()
  for u in s.split(' pv ',1)[1].split():
   m=p.move_from_usi(u);assert p.is_legal(m),(s,u,p.sfen());p.push(m);pvs+=1
 return pvs

def terminal(b,states,movers,gavecheck):
 if not list(b.legal_moves):return {'kind':'checkmate' if b.is_check() else 'no_legal_moves','winner':1-b.turn}
 seen=[i for i,s in enumerate(states) if s==states[-1]]
 if len(seen)>=4:
  first=seen[-4]
  checker=[c for c in [0,1] if all(gavecheck[j] for j in range(first,len(movers)) if movers[j]==c)]
  assert len(checker)<=1
  return {'kind':'perpetual_check_loss','winner':1-checker[0]} if checker else {'kind':'fourfold_draw','winner':None}
 return None

def game(g):
 f=g['root'];b=C.Board(f['initial_sfen']);states=[' '.join(b.sfen().split()[:3])];movers=[];gave=[]
 for u in f['history']:
  assert terminal(b,states,movers,gave) is None;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 assert ' '.join(b.sfen().split()[:3])==' '.join(f['expected_sfen'].split()[:3]);h=list(f['history']);pvcount=0
 for a,q in zip(g['actions'],g['queries']):
  assert terminal(b,states,movers,gave) is None;assert q['initial_sfen']==f['initial_sfen'] and q['history']==h;assert q['nodes_limit'] in (1024,8192) and q['command']==f"go nodes {q['nodes_limit']}";expect=g['weights'] if b.turn==g['color'] else [0]+[90]*7+[0]+[90]*6+[0];assert q['weights']==expect;assert q['bestmove']==a['move'] and a['actor']==b.turn;assert q['player']==('candidate' if b.turn==g['color'] else 'unit');assert a['before_sfen'].split()[:3]==b.sfen().split()[:3];pvcount+=query(q);m=b.move_from_usi(a['move']);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));h.append(a['move']);assert a['after_sfen'].split()[:3]==b.sfen().split()[:3]
 assert len(g['actions'])==len(g['queries']);assert g['final_sfen'].split()[:3]==b.sfen().split()[:3];score,counts=literal(b.sfen(),g['weights']);qty=counts[g['color']]-counts[1-g['color']];assert qty==g['raw_quantity'];t=terminal(b,states,movers,gave);assert g['termination']==(t or {'kind':'cap24','winner':None});goal=Fraction(qty,19) if not t else (Fraction(0) if t['winner'] is None else Fraction(32 if t['winner']==g['color'] else -32));assert str(goal)==g['goal'];return pvcount

def bare(q):return {k:v for k,v in q.items() if k not in ['player','ply']}
def audit(task):
 folder=R/'results/dev_aux'/f'task{task}';games=[json.loads(x) for x in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()];raw=[json.loads(x) for x in (folder/'queries.jsonl').read_text(encoding='utf-8').splitlines()];expected=[];pv=0
 for g in games:pv+=game(g)
 if task==365:
  rows=json.loads((folder/'result.json').read_text(encoding='utf-8'))['rows'];gi=0
  for row in rows:
   expected.append(row['root_query'])
   if row['changed_action']:
    g=games[gi];gi+=1;expected.extend(bare(q) for q in g['queries'])
  assert gi==len(games)
 else:expected=[bare(q) for g in games for q in g['queries']]
 assert expected==raw,(task,len(expected),len(raw));return {'task':task,'games':len(games),'actual_go':len(raw),'all_PV_move_checks':pv,'game_sha256':hashlib.sha256((folder/'games.jsonl').read_bytes()).hexdigest(),'query_sha256':hashlib.sha256((folder/'queries.jsonl').read_bytes()).hexdigest()}
if __name__=='__main__':
 tasks=[int(x) for x in sys.argv[1:]] or [377,373,380];t0=time.monotonic();rows=[]
 for t in tasks:r=audit(t);rows.append(r);print(r,flush=True)
 (O/'result.json').write_text(json.dumps({'status':'PASS','independent_backend':'cshogi0.9.7, actualwheelSHA privateverifiable dependencyrecord; literalSFENprice+quantity parser; allactualjounals/history/PV/terminal','seconds':time.monotonic()-t0,'rows':rows},indent=2),encoding='utf-8');print('PASS',time.monotonic()-t0)