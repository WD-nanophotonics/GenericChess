from pathlib import Path
import json,collections,random,time
R=Path.cwd();O=R/'results/dev_aux/task1593';O.mkdir(exist_ok=False);states=list(map(tuple,json.loads((R/'results/dev_aux/task1532/states.json').read_bytes())));original=json.loads((R/'results/dev_aux/task1532/values.json').read_bytes())['value'];text=(R/'results/dev_aux/task1575/run.py').read_text();exec(text[text.index('def solve(g,bound):'):text.index('summaries=[];rootvals={}')]);rows=[];proofs=0
for task,budget in [(1576,64),(1579,4096)]:
 P=R/f'results/dev_aux/task{task}';parent=json.loads((P/'result.json').read_bytes());roots={};strata=[]
 for price in [720,1728]:
  g=json.loads((P/f'graph_R{price}.json').read_bytes());assert 'UNKNOWN_FRONTIER' not in g['basis']
  for i,(sid,c) in enumerate(g['keys']):
   if g['basis'][i]=='SOLVED_4ACTOR_ACTUAL_POLICY':g['payoff'][i]=original[sid]*(1 if states[sid][6]==c else -1);g['basis'][i]='COMMON_PERFECT_4ORACLE'
  v,rank=solve(g,'lower')
  for i,ll in enumerate(g['adj']):
   if ll:
    own=states[g['keys'][i][0]][6]==g['keys'][i][1];ch=[v[j] for j in ll];assert v[i]==(max(ch) if own else min(ch))
    if not v[i]:assert 0 in ch and (all(z<=0 for z in ch) if own else all(z>=0 for z in ch))
   else:assert v[i]==g['payoff'][i] and rank[i]==0
   proofs+=1
  (O/f'B{budget}_R{price}.json').write_text(json.dumps({'value':v,'rank':rank},separators=(',',':')));roots[price]=[(f,v[i]) for f,i in g['roots']];strata.append({'price':price,'root_WDL':dict(collections.Counter(y for f,y in roots[price])),'mean':sum(y for f,y in roots[price])/256})
 fam=collections.defaultdict(list)
 for (f,a),(ff,b) in zip(roots[720],roots[1728]):assert f==ff;fam[f].append(b-a)
 delta=[sum(fam[i])/2 for i in range(128)];change=[delta[i]-parent['family_gain_bounds'][str(i)][0] for i in range(128)];rng=random.Random(2026675000+budget);bs=[];bc=[]
 for _ in range(10000):
  ss=rng.choices(range(128),k=128);bs.append(sum(delta[i] for i in ss)/128);bc.append(sum(change[i] for i in ss)/128)
 bs.sort();bc.sort();rows.append({'fiveactor_budget':budget,'profiles':strata,'price_gain_B':sum(delta)/128,'family95_B':[bs[249],bs[9749]],'paired_BminusA':sum(change)/128,'family95_BminusA':[bc[249],bc[9749]],'family_B_gain':delta})
out={'status':'COMPLETE_SHARED_4ORACLE_REACHABLE_POLICY','rows':rows,'proofs':proofs,'new_go':0,'scope':'Sameactual5choices/ALLopponent edges; <=4commonperfectrule oracle, changedcompositepolicy. Exactstrictdecisiveranks+drawsafe. Existingexposedfamilies, no new learning.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k!='family_B_gain'} for x in rows])
