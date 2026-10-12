import json,hashlib,time,math
from pathlib import Path
from fractions import Fraction
import chess
R=Path.cwd();O=R/'results/dev_aux/task256';O.mkdir(exist_ok=True);start=time.monotonic();D=json.loads((R/'results/dev_aux/task252/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task252/result.json').read_bytes());assert X['complete'] and len(X['calls'])==32
# Independent history/RNG/action/score audit for both snapshot and replay physicalgames.
import importlib.util,random
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);searches=0
for c in X['calls']:
 r=c['result'];b=P.board(D['roots'][c['root']]);rng=random.Random(c['random_seed']);si=0
 for ply,text in enumerate(r['actions']):
  assert chess.Move.from_uci(text) in b.legal_moves
  if b.turn==r['agent_color']:
   m=r['search_records'][si];assert m['root_fen']==b.fen() and m['full_history']==[z.uci() for z in b.move_stack];assert m['result']['completed_depth']==2 and not m['result']['used_fallback'];si+=1;searches+=1
  elif c['opponent']=='random':assert text==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci())).uci()
  b.push_uci(text)
 assert b.fen()==r['final_fen'];assert P.G.score(b,r['agent_color'],len(r['actions']),8)==r['score'];assert si==len(r['search_records'])
def nt(v):
 if isinstance(v,dict):return {k:nt(x) for k,x in v.items() if 'elapsed' not in k and k not in ('seconds','wall_seconds')}
 if isinstance(v,list):return [nt(x) for x in v]
 return v
for pair in X['pairs']:
 rr=[c for c in X['calls'] if c['pair']==pair['pair']];assert len(rr)==2 and nt(rr[0]['result'])==nt(rr[1]['result'])
# Independent JSON object_hook decoder, not imported producerdecode.
C=json.loads((R/'results/dev_aux/task253/result.json').read_bytes());tag='$dev_aux_constant_telemetry_v1'
def hook(o):
 if set(o)=={tag}:v=o[tag];return [v['value'] for _ in range(v['count'])]
 return o
Z=json.loads((R/'results/dev_aux/task253/compact_236.json').read_bytes(),object_hook=hook);raw=json.loads((R/'results/dev_aux/task236/games.json').read_bytes());canon=lambda v:json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode();assert hashlib.sha256(canon(Z)).hexdigest()==C['canonical_semantic_sha256']==hashlib.sha256(canon(raw)).hexdigest()
# Independent scalar evaluation ofall625 mean/min3control outcomes fromcompressedbranchsets.
T=json.loads((R/'results/dev_aux/task250/tree.json').read_bytes());Y=json.loads((R/'results/dev_aux/task250/result.json').read_bytes());models={z['method']:z for z in Y['models']};checked=0
for group in Y['root_policies']:
 tr=next(t for t in T['roots'] if t['root']==group['root']);goals=[Fraction(r['goal']) for r in tr['rows']]
 for j,m in enumerate(models['mean']['configs']):
  w=[208]+[round(208*m['ratios'][k]) for k in 'NBRQ'];mins=[];means=[]
  for row in tr['rows']:
   vals=[]
   for br in row['branches']:
    if 'terminal' in br:vals.append(br['terminal'])
    else:vals.append(max(v[1] if v[0]=='terminal' else sum(a*b for a,b in zip(v,w)) for v in br['unique_leaves']))
   mins.append(min(vals));means.append(Fraction(sum(vals),len(vals)))
  for mode,values in [('min',mins),('mean',means)]:
   chosen=max(range(len(values)),key=lambda i:values[i]);assert chosen==group['methods'][mode]['chosen_indices'][j];assert str(goals[chosen])==group['methods'][mode]['goal_values'][j];checked+=1
out=dict(complete=True,physicalgames_audited=32,actual_agent_queries=searches,all16paired_nontime_results_equal=True,independent_objecthook_fullsource_semantic_sha=C['canonical_semantic_sha256'],scalar_material_operator_controls_checked=checked,seconds=time.monotonic()-start,scope='Independentrecord/math/decoder audits, notnewgames; cachedbase invariance wasobserved liveby252producer pluswholematchedstateoutputs. No universalcloning/projectgenericclaim.');(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
