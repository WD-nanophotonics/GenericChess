"""Diagnose saved KRK continuations with complete RULE minimax WDL/DTM."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,array,collections,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1742';O.mkdir(exist_ok=False);proof=json.loads((R/'results/dev_aux/task1741/proof8.json').read_bytes());wdl=(R/'results/dev_aux/task1741/wdl8.bin').read_bytes();rank=array.array('H');rank.frombytes((R/'results/dev_aux/task1741/rank8.bin').read_bytes());assert hashlib.sha256(wdl).hexdigest()==proof['wdl_sha256'];assert hashlib.sha256(rank.tobytes()).hexdigest()==proof['rank_sha256'];records=[];summaries=[]
def lookup(s):
 pieces=[p for p in s[:-1] if p not in('.','K','k')]
 if len(pieces)!=1 or pieces[0].upper()!='R':return None
 owner=int(pieces[0].islower());n=tuple(p.swapcase() for p in s[:-1])+(1-s[-1],) if owner else tuple(s);k=n[:-1].index('K');b=n[:-1].index('k');r=n[:-1].index('R');i=(((k*64+b)*64+r)*2+n[-1]);v=wdl[i];assert v!=255;assert v==0 or (v==1 and n[-1]==0) or(v==2 and n[-1]==1)
 return dict(id=i,owner=owner,turn_R_side=n[-1]==0,wdl=v,DTM=rank[i],R_forced_win=v!=0)
for task in (1723,1728,1730,1736):
 D=R/f'results/dev_aux/task{task}';p=json.loads((D/'start.json').read_bytes())['plan'];choices={(x['nodes'],tuple(x['price']),tuple(x['state'])):x for x in map(json.loads,(D/'choices.jsonl').open())};cc=collections.Counter();states=set();families=set();witness=[]
 for x in map(json.loads,(D/'games.jsonl').open()):
  hit=None
  for i,s in enumerate([z['state'] for z in x['trajectory']]+[x['end']]):
   q=lookup(tuple(s))
   if q is not None:hit=i,s,q;break
  if hit is None:continue
  i,s,q=hit;cc['episodes_enter_KRK']+=1;states.add(q['id']);families.add(x['family'])
  if q['DTM']==0 and q['R_forced_win']:cc['terminal_mate_at_entry']+=1;continue
  if not q['R_forced_win']:cc['optimal_Draw_at_entry_NOT_fixedpolicyadjudication']+=1;continue
  cc['live_exact_R_forced_win_entries']+=1;candidate=x['root'][-1];expected=1 if q['owner']==candidate else -1
  cat='ACTUALLY_CONVERTED_R_WIN' if x['payoff']==expected else 'ACTUAL_DRAW_DESPITE_RULE_FORCED_WIN' if x['payoff']==0 else 'UNKNOWN_CENSORED' if x['payoff'] is None else 'IMPOSSIBLE_OPPONENT_SOLO_KING_MATE';assert cat!='IMPOSSIBLE_OPPONENT_SOLO_KING_MATE';cc[cat]+=1
  erows=[]
  for j,z in enumerate(x['trajectory'][i:],start=i):
   parent=lookup(tuple(z['state']));assert parent is not None
   if not parent['turn_R_side'] or not parent['R_forced_win']:continue
   child=tuple(x['trajectory'][j+1]['state']) if j+1<len(x['trajectory']) else tuple(x['end']);nxt=lookup(child)
   assert nxt is not None # R-side cannot capture its own lastR.
   preserving=nxt['R_forced_win'];minimal=preserving and nxt['DTM']==parent['DTM']-1
   cc['R_side_moves_in_forced_win']+=1;cc['R_side_moves_preserve_WDL']+=preserving;cc['R_side_moves_reduce_DTM_optimally']+=minimal;cc['R_side_moves_allow_optimal_Draw']+=not preserving
   nodes=p['candidate_nodes'] if z['own'] else x['opponent_nodes'];pp=tuple(x['price']) if z['own'] else tuple(x['opponent_price']);choice=choices.get((nodes,pp,tuple(z['state'])));maxdepth=None;mateinfo=[]
   if choice:
    dd=[]
    for raw in choice['uci_info']:
     a=raw.split()
     if 'depth' in a:dd.append(int(a[a.index('depth')+1]))
     if 'score mate' in raw:mateinfo.append(raw)
    maxdepth=max(dd) if dd else None;cc['Native_reported_depth_below_exact_DTM']+=maxdepth is not None and maxdepth<parent['DTM']
   erows.append(dict(ply=j,state=z['state'],move=z['move'],DTM=parent['DTM'],child_DTM=nxt['DTM'],preserve_WDL=preserving,DTM_optimal=minimal,nodes=nodes,max_reported_depth=maxdepth,mate_info=mateinfo))
  row=dict(source_task=task,phase=x['phase'],price=x['price'],family=x['family'],color=x['color'],opponent=x['opponent'],entry_ply=i,entry_state=s,entry=q,actual_category=x['category'],actual_payoff=x['payoff'],conversion=cat,R_side_moves=erows);records.append(row)
  if cat=='ACTUAL_DRAW_DESPITE_RULE_FORCED_WIN' and len(witness)<8:witness.append(row)
 summaries.append(dict(source_task=task,counts=dict(cc),distinct_entry_states=len(states),distinct_root_families=len(families),draw_witnesses=witness))
(O/'records.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in records));out=dict(status='COMPLETE_ZERO_QUERY_RULE_DTM_CONVERSION_DIAGNOSIS',summaries=summaries,actual_new_native_go=0,interpretation='Exact RULE minimax win does not assert actualfixedpolicywin. OptimalDraw is NOT a fixedpolicyDraw shortcut (defender can blunder), and KRKwin is NOT a training/adjudication reward. Tableonlydiagnoses alreadyobservedphysical/cycle outcomes. Repeatedprices/opponents/colors dependent; counts notindependentN. ReportedNative depth is selective, notfullwidthcertificate orproofwhichheuristic failed.')
(O/'result.json').write_text(json.dumps(out,indent=2))
for x in summaries:print({k:v for k,v in x.items() if k!='draw_witnesses'})

