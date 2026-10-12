import sys,json,time,copy,os
from pathlib import Path
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task365';O.mkdir(exist_ok=True);games=[json.loads(x) for x in (R/'results/dev_aux/task364/games.jsonl').read_text(encoding='utf-8').splitlines()];points=[];coverage=[]
for gi,g in enumerate(games):
 chosen=None;nroot=0;npv=0
 for qi,q in enumerate(g['queries']):
  if q['player']!='candidate':continue
  b=A.replay(q['initial_sfen'],q['history']);optional=sorted(m.usi() for m in b.legal_moves if m.promotion and A.shogi.Move(m.from_square,m.to_square) in b.legal_moves);pv=[]
  for l in q['lines']:
   if ' pv ' in l:pv=l.split(' pv ',1)[1].split()
  qpv=b.__class__(q['initial_sfen'])
  for h in q['history']:qpv.push_usi(h)
  parameter=None
  if optional:
   nroot+=1;m=A.shogi.Move.from_usi(optional[0]);parameter=A.MAP[b.piece_at(m.from_square).piece_type]+8
  for u in pv:
   m=A.shogi.Move.from_usi(u)
   if m.promotion:
    npv+=1
    if parameter is None and qpv.turn==g['color']:parameter=A.MAP[qpv.piece_at(m.from_square).piece_type]+8
   qpv.push(m)
  if chosen is None and parameter is not None:chosen={'game_index':gi,'query_index':qi,'parameter':parameter,'root':g['root'],'color':g['color'],'base_query':q,'base_final_goal':g['goal'],'base_final_quantity':g['raw_quantity'],'optional':optional,'pv':pv,'remaining':24-q['ply']}
 coverage.append({'game_index':gi,'candidate_optional_points':nroot,'pv_promotion_events':npv,'selected':chosen is not None})
 if chosen:points.append(chosen)
 # Finite panel first4 unit games and first4 random games, selected by file index before response outcomes.
points=[p for p in points if p['game_index'] in [0,1,2,3,8,9,10,11]]
(O/'declaration.json').write_text(json.dumps({'selection':'first4 game IDs ofeach frozen initial; first root-optional or candidate PV promotion in chronological candidate queries; firstsorted optional/lastcompletePV; no goal selection','points':points,'coverage':coverage,'changed_prices':'one related promoted piece half/double clipped32..4096','continuation':'only ifrootaction differs fromactualbase; end atoriginalabsoluteH24, fullhistory andfixedunit unchanged','scope':'no human fitting orendpoint selection; saturation/coverage distinctfromreward response'},indent=2),encoding='utf-8');unit=[0]+[90]*7+[0]+[90]*6+[0];rows=[];t0=time.monotonic()
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=A.Engine(unit,qj)
 try:
  for p in points:
   for mode in ['half','double']:
    w=list(p['base_query']['weights']);j=p['parameter'];w[j]=max(32,min(4096,(w[j]+1)//2 if mode=='half' else w[j]*2));ec=A.Engine(w,qj)
    try:
     q=ec.search(p['base_query']['initial_sfen'],p['base_query']['history']);A.validate_search(q);changed=q['bestmove']!=p['base_query']['bestmove'];tail=None
     if changed:
      f=copy.deepcopy(p['root']);f['history']=p['base_query']['history'];f['expected_sfen']=A.replay(f['initial_sfen'],f['history']).sfen();tail=G.game(ec,eu,w,f,p['color'],gj,cap=p['remaining'],deadline=t0+600)
      assert tail['actions'][0]['move']==q['bestmove']
     rows.append({'game_index':p['game_index'],'parameter':j,'mode':mode,'weights':w,'price_readback':ec.prices,'root_query':q,'base_bestmove':p['base_query']['bestmove'],'changed_action':changed,'base_goal':p['base_final_goal'],'base_quantity':p['base_final_quantity'],'tail_goal':tail['goal'] if tail else None,'tail_quantity':tail['raw_quantity'] if tail else None,'goal_delta':str(Fraction(tail['goal'])-Fraction(p['base_final_goal'])) if tail else None,'tail_go':len(tail['queries']) if tail else 0});print(p['game_index'],j,mode,changed,rows[-1]['goal_delta'],flush=True)
    finally:ec.close()
 finally:eu.close()
result={'seconds':time.monotonic()-t0,'points':len(points),'response_queries':len(rows),'continuations':sum(x['changed_action'] for x in rows),'new_go':len(rows)+sum(x['tail_go'] for x in rows),'changed_quantity_or_rule_goal':sum(x['goal_delta'] not in (None,'0') for x in rows),'rows':rows};(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print({k:v for k,v in result.items() if k!='rows'})