import json,sys,time,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task678';d=json.loads((R/'results/dev_aux/task675/deployment_declaration.json').read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
vals={};prefixes=[]
for line,t in enumerate((R/'results/dev_aux/task676/games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(t)
 for H in [12,24]:
  b,k,ch,mo=G.full_root(g['root']);n=min(H,len(g['actions']))
  for a in g['actions'][:n]:
   assert G.terminal(b,k,ch,mo) is None and b.sfen()==a['before_sfen'];m=A.shogi.Move.from_usi(a['move']);assert m in b.legal_moves;mo.append(b.turn);b.push(m);ch.append(b.is_check());k.append(G.key(b));assert b.sfen()==a['after_sfen']
  tr=G.terminal(b,k,ch,mo);term=tr or dict(kind='cap'+str(H),winner=None);qty=G.quantity(b,g['color']);winner=term['winner'];terminal=F(0 if winner is None else 32 if winner==g['color'] else -32);fast=F(0) if winner is None else F(25-n,25) if winner==g['color'] else F(-1);legacy=F(0) if winner is None else F(H+1-n) if winner==g['color'] else F(-H-1);mixed=F(qty,19) if tr is None else terminal
  if H==24:assert term==g['termination'] and qty==g['raw_quantity'] and str(mixed)==g['goal']
  key=(g['replica'],g['profile'],g['root']['index'],g['color'],H);assert key not in vals;vals[key]=dict(quantity=F(qty,19),terminal=terminal,common_fast=fast,legacy_fast=legacy,mixed=mixed);prefixes.append(dict(source_line=line,replica=g['replica'],profile=g['profile'],root=g['root']['index'],color=g['color'],cap=H,plies=n,actual_queries=sum(q['ply']<n for q in g['queries']),quantity=qty,termination=term,final_sfen=b.sfen()))
assert len(vals)==768;rows=[];families=sorted({r['source_family'] for r in d['roots']});cells=[(r,c) for r in d['roots'] for c in [0,1]]
for pair in d['pairs']:
 for replica in [0,1]:
  for metric in ['quantity','common_fast','terminal','mixed','legacy_fast']:
   dd={H:[vals[(replica,pair['endpoint_profile'],r['index'],c,H)][metric]-vals[(replica,pair['initial_profile'],r['index'],c,H)][metric] for r,c in cells] for H in [12,24]};lo={H:[sum(dd[H][i] for i,(r,c) in enumerate(cells) if r['source_family']!=f)/sum(r['source_family']!=f for r,c in cells) for f in families] for H in [12,24]};rows.append(dict(route=pair['route'],start=pair['start'],replica=replica,metric=metric,H12_gain=str(sum(dd[12])/32),H24_gain=str(sum(dd[24])/32),horizon_interaction=str(sum(dd[24][i]-dd[12][i] for i in range(32))/32) if metric!='legacy_fast' else None,H12_min_LOO=str(min(lo[12])),H24_min_LOO=str(min(lo[24])),by_family=[dict(family=f,H12_gain=str(sum(dd[12][i] for i,(r,c) in enumerate(cells) if r['source_family']==f)/2),H24_gain=str(sum(dd[24][i] for i,(r,c) in enumerate(cells) if r['source_family']==f)/2)) for f in families]))
out=dict(status='ALL_INDEPENDENT_ORDINARY_HORIZON_CONTRASTS_FROZEN',rows=rows,prefixes=prefixes,physical_games=384,literal_H12_prefix_controls=384,new_go=0,seconds=time.perf_counter()-start,common_fast_definition='WIN(25-actualplies)/25 LOSS-1 DRAW/UNFINISHED0 atBOTHhorizons. Sameactualmatewithsameplies hasSAMEscore; do notcomparelegacy13/25scoremagnitude ashorizonquality.',scope=d['scope']+' EveryliteralH12prefix independentlyPythonterminal/quantity/legality/history replayed. H24physical/H12prefixnotnewgo. All2freshsets/16families/fourendpoints/all5scoredefinitions retained; no postdepthfilter/favorablecondition selection. 677fullphysical+680generator audit required beforevalidatedclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([{k:x[k] for k in ['route','start','replica','metric','H12_gain','H24_gain','H12_min_LOO','H24_min_LOO']} for x in rows if x['metric'] in ['quantity','common_fast']]))
