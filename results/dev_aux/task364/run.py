import sys,json,random,time,os,hashlib
from pathlib import Path
from fractions import Fraction
sys.path.insert(0,str(Path.cwd()/'results/dev_aux/task360'));import adapter as A
R=Path.cwd()
def stop():
 for root in [R,R.parent/'GenericChess 2']:
  for file in ['rollout.json','advisor.json','slack.json']:
   d=json.loads((root/'.local_agent'/file).read_text(encoding='utf-8'));assert not d.get('user_paused') and not d.get('stopped'),'Persistent user stop'
def key(b):return ' '.join(b.sfen().split()[:3])
def terminal(b,keys,checks,movers):
 legal=sorted(m.usi() for m in b.legal_moves)
 if not legal:return {'kind':'checkmate' if b.is_check() else 'no_legal_moves','winner':1-b.turn}
 occurrences=[i for i,k in enumerate(keys) if k==keys[-1]]
 if len(occurrences)>=4:
  begin=occurrences[-4];losers=[]
  for c in (0,1):
   js=[j for j in range(begin,len(movers)) if movers[j]==c]
   if js and all(checks[j+1] for j in js):losers.append(c)
  assert len(losers)<=1
  if losers:return {'kind':'perpetual_check_loss','winner':1-losers[0]}
  return {'kind':'fourfold_draw','winner':None}
 return None

def full_root(f):
 b=A.shogi.Board(f['initial_sfen']);keys=[key(b)];checks=[b.is_check()];movers=[]
 for u in f['history']:
  assert terminal(b,keys,checks,movers) is None; m=A.shogi.Move.from_usi(u);assert m in b.legal_moves;movers.append(b.turn);b.push(m);keys.append(key(b));checks.append(b.is_check())
 return b,keys,checks,movers

def quantity(b,color):
 counts=[0,0]
 for sq in range(81):
  p=b.piece_at(sq)
  if p and p.piece_type!=A.shogi.KING:counts[p.color]+=1
 for c in (0,1):counts[c]+=sum(b.pieces_in_hand[c].values())
 assert sum(counts)==38,(counts,b.sfen());return counts[color]-counts[1-color]

def game(candidate,unit,w,f,color,journal,cap=24,nodes=1024,deadline=None):
 stop();t=time.monotonic();b,keys,checks,movers=full_root(f);h=list(f['history']);acts=[];qs=[];term=terminal(b,keys,checks,movers)
 for ply in range(cap):
  if term:break
  if deadline and time.monotonic()>deadline:raise RuntimeError('Predeclared batch fuse')
  stop();e=candidate if b.turn==color else unit;r=e.search(f['initial_sfen'],h,nodes);A.validate_search(r);assert r['weights']==(w if b.turn==color else unit.w);r['player']='candidate' if b.turn==color else 'unit';r['ply']=ply;qs.append(r)
  u=r['bestmove'];m=A.shogi.Move.from_usi(u);assert m in b.legal_moves;before=b.sfen();captured=b.piece_at(m.to_square);moving=b.piece_at(m.from_square) if m.from_square is not None else None;actor=b.turn;movers.append(actor);b.push(m);h.append(u);acts.append({'move':u,'actor':actor,'captured':str(captured) if captured else None,'moving':str(moving) if moving else None,'promotion':bool(m.promotion),'drop':m.drop_piece_type,'before_sfen':before,'after_sfen':b.sfen()});keys.append(key(b));checks.append(b.is_check());term=terminal(b,keys,checks,movers)
 rawq=quantity(b,color);goal=Fraction(rawq,19)
 if term:
  goal=Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==color else -32)
 r={'weights':w,'root':f,'color':color,'actions':acts,'queries':qs,'termination':term or {'kind':'cap24','winner':None},'final_sfen':b.sfen(),'raw_quantity':rawq,'goal':str(goal),'seconds':time.monotonic()-t}
 if journal:journal.write(json.dumps(r,ensure_ascii=False)+'\n');journal.flush();os.fsync(journal.fileno())
 return r

if __name__=='__main__':
 O=R/'results/dev_aux/task364';O.mkdir(exist_ok=True);t0=time.monotonic();unit=[0]+[90]*7+[0]+[90]*6+[0];rng=random.Random(2026102514);randomw=[0]+[int(round(2**rng.uniform(5,10))) for _ in range(14)]+[0];randomw[1]=90;randomw[8]=0;roots=[]
 for phase,seeds in [('train',range(2026102510,2026102514)),('development',range(2026102580,2026102584))]:
  for i,seed in enumerate(seeds):
   b=A.shogi.Board();f={'phase':phase,'index':i,'seed':seed,'initial_sfen':b.sfen(),'history':[]};rg=random.Random(seed)
   for ply in range(40):
    moves=sorted(m.usi() for m in b.legal_moves);assert moves;u=rg.choice(moves);b.push_usi(u);f['history'].append(u)
   f['expected_sfen']=b.sfen();full_root(f);assert not b.is_game_over();roots.append(f)
 d={'source_sha':'c1b80eaa09fe13d5f12b1599d1ae4d53c224de30','executable_sha256':hashlib.sha256(A.EXE.read_bytes()).hexdigest(),'profiles':[{'name':'unit','weights':unit},{'name':'random2514','weights':randomw}],'roots':roots,'pilot':'all2 profiles/all4training roots/bothcolors16games; NO development outcomes beforeall endpoint freeze','goal':'actual rule win/loss +/-32, rule draw0; ongoingH24 unweighted board+hand nonking owned countdiff/19','cap':24,'nodes':1024,'opponent':'fixedunit Material1 candidateSEE samebackend/fullhistory','learning_future':'max2rounds perprofile,12mutablepieces excludingP90K0,25base+half/double proposals withclip32..4096;8traincells/price,strict improvement/base-first exactties,cache exactfullinputs; max800logical games across2starts under2400sfuse; inspect pilot projectedcost first','limitations':['NoEnteringKing declared scope','SEE candidateboardprice LVA; upstream board-only omission of handgain/recapturepromotions','other fixed search margins/order heuristics and fixedP90USIscale retained','ordinary concurrent computer computation','randomprefix algorithm fixed, no outcomes/human screen']};(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');rows=[]
 with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
  eu=A.Engine(unit,qj)
  try:
   for p in d['profiles']:
    ec=A.Engine(p['weights'],qj)
    try:
     for f in [x for x in roots if x['phase']=='train']:
      for c in (0,1):
       r=game(ec,eu,p['weights'],f,c,gj,deadline=t0+600);r['family']=p['name'];rows.append(r);print(p['name'],f['index'],c,r['goal'],round(r['seconds'],3),flush=True)
    finally:ec.close()
  finally:eu.close()
 summary=[]
 for p in d['profiles']:
  rs=[x for x in rows if x['family']==p['name']];summary.append({'family':p['name'],'mean_goal':str(sum((Fraction(x['goal']) for x in rs),Fraction())/len(rs)),'mean_quantity':str(sum(Fraction(x['raw_quantity']) for x in rs)/len(rs)),'rule_outcomes':[x['termination']['kind'] for x in rs],'plies':sum(len(x['actions']) for x in rs)})
 result={'status':'complete','seconds':time.monotonic()-t0,'games':len(rows),'go':sum(len(x['queries']) for x in rows),'summary':summary};(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)