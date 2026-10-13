import json,sys,time,math,random,hashlib,copy,inspect
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task959';O.mkdir(exist_ok=False);start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
MAP=V.MAP;ls=(R/'results/dev_aux/task381/audit.py').read_text(encoding='utf-8-sig');ls=ls[ls.index('def literal('):ls.index('def query(')].replace('sum(owned)==38','sum(owned) in [4,6,8]');exec(compile(ls,'independent_reduced_literal','exec'));V.literal=literal
src=inspect.getsource(G.quantity).replace('sum(counts)==38','sum(counts) in [4,6,8]');exec(compile(src,'independent_reduced_quantity','exec'));G.quantity=quantity
roots_record=json.loads((R/'results/dev_aux/task953/roots_frozen.json').read_bytes());prefixes=0;rejections=0
assert len(roots_record['trace'])==128
for tr in roots_record['trace']:
 r=tr['root'];bb=['']*81
 for sq,pt,c,j in tr['placement']:
  assert not bb[sq];z={3:'n',5:'g',6:'b',8:'k'}[pt];bb[sq]=z.upper() if c==0 else z
 ranks=[]
 for rank_start in range(0,81,9):
  rank='';empty=0
  for z in bb[rank_start:rank_start+9]:
   if z:
    if empty:rank+=str(empty);empty=0
    rank+=z
   else:empty+=1
  if empty:rank+=str(empty)
  ranks.append(rank)
 assert '/'.join(ranks)+' b - 1'==r['initial_sfen']
 assert tr['placement']==[x for x in tr['full_placement'] if r['inventory']==8 or x[3] in [-1,0,2]]
 b=C.Board(r['initial_sfen']);white=C.Board(r['initial_sfen'].replace(' b ',' w '));bc=b.is_check();wc=white.is_check();legal=sorted(C.move_to_usi(m) for m in b.legal_moves);assert bc==tr['black_check'] and wc==tr['white_check'] and legal==tr['initial_legal'];term=V.terminal(b,[' '.join(b.sfen().split()[:3])],[],[])
 expected=dict(kind='initial_white_check',black=bc,white=wc) if wc else dict(kind='initial_terminal',termination=term) if term else dict(kind='too_few_actions',count=len(legal)) if len(legal)<2 else None
 assert expected==tr['failure'];rejections+=expected is not None;assert r['history']==[] and r['expected_sfen']==r['initial_sfen'];assert sum(pc!=0 and pc%16!=8 for pc in b.pieces)==r['inventory']
P=R/'results/dev_aux/task958';d=json.loads((P/'execution_inputs.json').read_bytes());counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0);s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8-sig');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'ACKtables','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8-sig');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)").replace("q['nodes_limit']==1024","q['nodes_limit']==d['nodes']").replace("q['command']=='go nodes 1024'","q['command']=='go nodes '+str(d['nodes'])");exec(compile(s,'independent_reduced_fullgame','exec'));constructor=G.full_root;cache={}
def clone(f):
 k=json.dumps(f,sort_keys=True)
 if k not in cache:cache[k]=constructor(f)
 b,ks,ch,mo=cache[k];return copy.deepcopy(b),list(ks),list(ch),list(mo)
G.full_root=clone;raw=iter((P/'queries.jsonl').open(encoding='utf-8'));seen=[]
for line in (P/'games.jsonl').open(encoding='utf-8'):
 g=json.loads(line);assert g['root'] in d['roots'];game(g,'unit' if g['opponent']=='unit_search' else 'random',raw);seen.append((g['endpoint'],g['mode'],g['opponent'],g['root']['seed'],g['color']))
 for q in g['queries']:
  leaf=g['leaf_weights'] if q['player']=='candidate' else d['fixed_opponent'];assert q['leaf_weights']==leaf;b=A.replay(q['initial_sfen'],q['history']);a=q['leaf_state'].split(' ',4);assert int(a[3])==A.material(b,leaf)*(1 if b.turn==0 else -1) and a[4].split()[:3]==b.sfen().split()[:3]
assert next(raw,None) is None;expected=[(p['endpoint'],p['mode'],opp,f['seed'],c) for p in d['configs'] for opp in ['unit_search','uniform_random'] for f in d['roots'] for c in [0,1]];assert seen==expected;counts['price_ACK_entries']=tables(json.loads((P/'price_acks.json').read_bytes()));result=dict(status='PASS_ALL288_VALID_STOCK_LEAF_NATIVE_GAMES',counts=counts,prefix_moves=prefixes,rejected_preserved=rejections,new_go=0,seconds=time.perf_counter()-start,scope='ALLgenerated/rejectedroots cshogi vsPython legalfrontier/initialroyalchecks/prefix/inventory andALL288physicalgames queryjournal/Python fullhistory/actions/RNG/terminal/price/PV. 4/8nonkingreducedinventory explicit. Notstandardopening/fullgenerateddomain/force-mateproof.');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
