from pathlib import Path
import json,collections
R=Path.cwd();O=R/'results/dev_aux/task1715';plan=json.loads((R/'results/dev_aux/task1677/plan.json').read_bytes());families={f['family']:f for f in plan['families']};BASE=(720,720,720,720);C=(1440,720,720,360);full={(tuple(x['price']),tuple(x['state'])):x for x in map(json.loads,(R/'results/dev_aux/task1696/full_choices.jsonl').open())};games={}
for task in [1678,1696]:
 for line in (R/f'results/dev_aux/task{task}/games.jsonl').open():
  x=json.loads(line)
  if x['phase']=='DEV':games[task,tuple(x['price']),x['family'],x['color']]=x
counts=collections.defaultdict(collections.Counter);examples=[];rows=[]
for fam in families.values():
 if fam['phase']!='DEV':continue
 for color,root in enumerate(fam['roots']):
  s=tuple(root);pown=any(p.upper()=='P' and int(p.islower())==s[-1] for p in s[:-1]);key='P_HOLDER' if pown else 'NO_OWN_P'
  for p in [BASE,C]:
   native=games[1678,p,fam['family'],color];exact=games[1696,p,fam['family'],color];f=full[p,s];scores={x['move']:x['score'] for x in f['scores']};u=native['trajectory'][0]['move'];v=exact['trajectory'][0]['move'];assert v==f['move'] and scores[v]==f['value'];gap=scores[v]-scores[u];assert gap>=0;cat='SAME_MOVE' if u==v else 'DIFFERENT_FINITE3_TIE' if gap==0 else 'LOWER_FINITE3_VALUE';counts[key,str(p)][cat]+=1
   row={'family':fam['family'],'color':color,'own_P':pown,'price':p,'root':root,'Native_move':u,'completeD3_move':v,'Native_move_finite3':scores[u],'best_finite3':scores[v],'gap':gap,'classification':cat,'Native_actual_policy_payoff':native['payoff'],'completeD3_actual_policy_payoff':exact['payoff'],'full_rule_scope':'Royal4x4 RNP mandatoryRNBpromotion/nohistorydraw'};rows.append(row)
   if p==C and gap>0 and exact['payoff']>native['payoff'] and len(examples)<8:examples.append(row)
(O/'all_roots.json').write_text(json.dumps(rows,indent=2));out={'status':'PASS_ZERO_QUERY_MATCHED_ROOT_FINITE3_DISAGREEMENT_DIAGNOSTIC','counts':{str(k):dict(v) for k,v in counts.items()},'examples':examples,'actual_go':0,'scope':'All matched128DEVroot/color records, bothfixedprices, completeD3scores independentlyverifiedALLbeforethisanalysis. Native64selective reporteddepth notcompletefinite3guarantee; gapisfinite3 nottrueoptimalWDLerror. Fullpolicyrealizeddifference includesallfutureactions/opresponse, NOTisolatedrootmovecausalexperiment. PostspecifiedP-holderstrata descriptive.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
