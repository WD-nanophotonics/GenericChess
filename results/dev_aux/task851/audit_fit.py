import json,sys,time,math,random,hashlib,copy,inspect
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task856';O.mkdir(exist_ok=False);start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
MAP=V.MAP;ls=(R/'results/dev_aux/task381/audit.py').read_text(encoding='utf-8-sig');ls=ls[ls.index('def literal('):ls.index('def query(')].replace('sum(owned)==38','sum(owned) in [4,6]');exec(compile(ls,'independent_reduced_literal','exec'));V.literal=literal
src=inspect.getsource(G.quantity).replace('sum(counts)==38','sum(counts) in [4,6]');exec(compile(src,'independent_reduced_quantity','exec'));G.quantity=quantity
roots_record=json.loads((R/'results/dev_aux/task850/roots_frozen.json').read_bytes());prefixes=0;rejections=0
for tr in roots_record['trace']:
 r=tr['root'];b=C.Board(r['initial_sfen']);white=C.Board(r['initial_sfen'].replace(' b ',' w '));bc=b.is_check();wc=white.is_check()
 if tr['failure'] and tr['failure']['kind']=='initial_king_check':assert bc==tr['failure']['black'] and wc==tr['failure']['white'] and (bc or wc);rejections+=1;continue
 assert not bc and not wc;states=[' '.join(b.sfen().split()[:3])];mo=[];ch=[]
 for a in tr['actions']:
  assert V.terminal(b,states,mo,ch) is None;legal=sorted(C.move_to_usi(m) for m in b.legal_moves);assert legal==a['legal'] and a['move']==legal[a['index']] and b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);mo.append(b.turn);b.push(m);ch.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));assert b.sfen()==a['after_sfen'];prefixes+=1
 assert b.sfen()==r['expected_sfen'];assert sum(pc!=0 and pc%16!=8 for pc in b.pieces)+sum(sum(h) for h in b.pieces_in_hand)==r['inventory']
 if tr['failure']:assert V.terminal(b,states,mo,ch)==tr['failure']['termination'];rejections+=1
 else:assert V.terminal(b,states,mo,ch) is None and len(r['history'])==8
P=R/'results/dev_aux/task855';d=json.loads((R/'results/dev_aux/task853/execution_inputs.json').read_bytes());counts=dict(games=0,actual_go=0,PV_moves=0,Python_actual_actions=0,random_draws=0,sorted_legal_arrays=0,price_ACK_entries=0);s=(R/'results/dev_aux/task522/audit.py').read_text(encoding='utf-8-sig');exec(compile(s[s.index('def tables('):s.index('nativegames=0')],'ACKtables','exec'));s=(R/'results/dev_aux/task600/audit.py').read_text(encoding='utf-8-sig');s=s[s.index('def game('):s.index('for task,opp in')].replace('cap=12;','cap=g["cap"];').replace("dict(kind='cap12' if cap==12 else 'cap24',winner=None)","dict(kind='cap'+str(cap),winner=None)").replace("q['nodes_limit']==1024","q['nodes_limit']==d['nodes']").replace("q['command']=='go nodes 1024'","q['command']=='go nodes '+str(d['nodes'])");exec(compile(s,'independent_reduced_fullgame','exec'));constructor=G.full_root;cache={}
def clone(f):
 k=json.dumps(f,sort_keys=True)
 if k not in cache:cache[k]=constructor(f)
 b,ks,ch,mo=cache[k];return copy.deepcopy(b),list(ks),list(ch),list(mo)
G.full_root=clone;raw=iter((P/'queries.jsonl').open(encoding='utf-8'));seen=[]
for line in (P/'games.jsonl').open(encoding='utf-8'):
 g=json.loads(line);assert g['root'] in d['roots'];game(g,'unit' if g['opponent']=='unit_search' else 'random',raw);seen.append((g['opponent'],g['root']['seed'],g['color']))
assert next(raw,None) is None;counts['price_ACK_entries']=tables(json.loads((P/'price_acks.json').read_bytes()));ep=json.loads((P/'endpoints.json').read_bytes());old=[json.loads(l) for l in (R/'results/dev_aux/task853/games.jsonl').open(encoding='utf-8')];new=[json.loads(l) for l in (P/'games.jsonl').open(encoding='utf-8')];assert ep['qualified_cache_source_sha256']==hashlib.sha256((R/'results/dev_aux/task853/games.jsonl').read_bytes()).hexdigest();logical=0
for u in ep['updates']:
 w=list(u['start_weights']);axis=u['axis'];rr=[f for f in d['roots'] if f['variant']==u['variant']];cells=[(opp,f,c) for opp in ['unit_search','uniform_random'] for f in rr for c in [0,1]];means=[]
 for factor,batch in zip([1,.25,.5,2,4,8,16],u['candidates']):
  ww=list(w);ww[axis]=ww[axis+8]=max(32,min(4096,math.floor(w[axis]*factor+.5)));assert ww==batch['weights'];gs=[(old if ref['file']=='task853/games.jsonl' else new)[ref['line']-1] for ref in batch['sources']];assert [(g['opponent'],g['root'],g['color']) for g in gs]==cells;assert all(g['weights']==ww for g in gs);vv=[]
  for g in gs:
   t=g['termination'];v=0 if t['kind'].startswith('cap') or t['winner'] is None else 1 if t['winner']==g['color'] else -1;vv.append((Fraction(v),Fraction(25-len(g['actions']),25) if v>0 else Fraction(-1) if v<0 else Fraction(0)))
  mm=tuple(sum(v[j] for v in vv)/len(vv) for j in [0,1]);assert [str(v) for v in mm]==batch['mean'];means.append(mm);logical+=len(gs)
 best=max(range(7),key=lambda i:means[i]);assert u['selected_index']==best and u['after_weights']==u['candidates'][best]['weights']
for e in ep['endpoints']:
 uu=[u for u in ep['updates'] if u['variant']==e['variant'] and u['start']==e['start']];assert uu[0]['start_weights']==e['initial'] and uu[-1]['after_weights']==e['endpoint'];assert len(uu)==(1 if e['variant']=='NR' else 2)
assert counts['games']==ep['actual_new_games'] and counts['actual_go']==ep['actual_go'];result=dict(status='PASS_ALL_REDUCED_TRUE_TERMINAL_FIT_GAMES_AND_SELECTION',counts=counts,logical_cells=logical,prefix_moves=prefixes,rejected_preserved=rejections,new_go=0,seconds=time.perf_counter()-start,scope='Allnewphysicalgames/fullPythonrules/RNG/terminal/query/material/PV/ACK; original64pilotqualifiedcache hash andALL42logicalpricebatches/6base-firstlexcoordinate selections. Noquantityfitness/oldholdoutfit.');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
