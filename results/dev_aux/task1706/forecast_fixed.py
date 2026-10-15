from pathlib import Path
import json,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1713';O.mkdir(exist_ok=False);proof=json.loads((R/'results/dev_aux/task1706/result.json').read_bytes());assert proof['status'].startswith('PASS');studies=[]
for runid,planid in [(1678,1677),(1686,1685),(1693,1692),(1696,1695),(1699,1698),(1703,1702),(1709,1708)]:
 plan=json.loads((R/f'results/dev_aux/task{planid}/plan.json').read_bytes());sp=importlib.util.spec_from_file_location('T',R/plan['model']);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);counts=collections.Counter();needed=set();allused=set();width=8 if len(plan['families'][0]['roots'][0])==65 else 4
 for line in (R/f'results/dev_aux/task{runid}/games.jsonl').open():
  x=json.loads(line);c=x['root'][-1];cut=None
  for i,step in enumerate(x['trajectory']):
   s=tuple(step['state']);nonking=[p for p in s[:-1] if p not in('.','K','k')];safe=len(nonking)==1 and nonking[0].upper() in('N','B')
   if cut is None and safe:cut=i;assert x['payoff']==0
   if len(T.moves(s))>1:
    p=tuple(x['price']) if s[-1]==c else tuple(plan['baseline']);n=plan.get('candidate_nodes',64) if s[-1]==c else(plan.get('strong_DEV_opponent_nodes',64) if x['phase']=='DEV_STRONG' else plan.get('opponent_nodes',64));key=n,p,s;allused.add(key)
    if cut is None:needed.add(key)
  counts['games']+=1
  if cut is not None:counts['earlier_stockDraw_games']+=1;counts['forecast_removed_plies']+=len(x['trajectory'])-cut
 newkeys=set()
 for line in (R/f'results/dev_aux/task{runid}/choices.jsonl').open():
  z=json.loads(line);n=z.get('nodes',int(z['command'].split()[-1]));newkeys.add((n,tuple(z['price']),tuple(z['state'])))
 # Full3candidate's dictionarymoves aren'tNativego; Nativequerynewkeys only.
 saved=newkeys-needed;assert saved<=allused;counts['forecast_new_native_go_unneeded']=len(saved);counts['actual_new_native_go']=len(newkeys);studies.append({'run':runid,'width':width,'counts':dict(counts),'removed_fraction_of_actual_new_go':len(saved)/len(newkeys) if newkeys else 0})
out={'status':'PASS_EXISTING_TRAJECTORY_RULE_STOCK_DRAW_COST_FORECAST','studies':studies,'actual_added_go':0,'scope':'PosthoccounterfactualworkaccountingONLY aftercompleteclosedruleproof1706. Originalallcycles/gameoutputsretained; noactualwalltimegainmeasured. RetainedprefixesfollowSAMEcachedpolicies andrequiredNativekeyunionacrossALLgames; noPawn/duplicate/twoN/B shortcut. Doesnotretroactivelypretendoldcontrollerusedproof.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(studies)
