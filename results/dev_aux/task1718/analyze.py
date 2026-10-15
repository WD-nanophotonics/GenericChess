from pathlib import Path
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1718';comparisons=[];B=(720,720,720,720);C4=(1440,720,720,360);C8=(1440,720,720,1440)
def rows(task,phase,p):
 dd=collections.defaultdict(list)
 for line in (R/f'results/dev_aux/task{task}/games.jsonl').open():
  x=json.loads(line)
  if x['phase']==phase and tuple(x['price'])==p:assert x['payoff'] is not None;dd[x['family']].append(x['payoff'])
 assert dd and all(len(v)==2 for v in dd.values());return {f:sum(v)/2 for f,v in dd.items()}
for name,taskA,phaseA,taskB,phaseB,C,subset in [('OPPONENT_STRONG_minus_WEAK',1703,'DEV_STRONG',1703,'DEV',C8,None),('ALIGNED_minus_LEAFONLY',1709,'DEV',1703,'DEV',C8,None),('CANDIDATE4096_minus64_FIRST16',1699,'DEV',1693,'DEV',C4,range(16))]:
 aa,ab,ba,bb=rows(taskA,phaseA,C),rows(taskA,phaseA,B),rows(taskB,phaseB,C),rows(taskB,phaseB,B);ids=sorted(set(aa)&set(ab)&set(ba)&set(bb));ids=[f for f in ids if subset is None or f in subset];g=[aa[f]-ab[f]-ba[f]+bb[f] for f in ids];rng=random.Random(2026700600+taskA);boot=[];half=len(ids)//2
 for _ in range(10000):
  ss=rng.choices([i for i,f in enumerate(ids) if f%2==0],k=half)+rng.choices([i for i,f in enumerate(ids) if f%2==1],k=half);boot.append(sum(g[i] for i in ss)/len(ids))
 boot.sort();comparisons.append({'name':name,'families':len(ids),'price':C,'gain_change':sum(g)/len(ids),'paired_family95':[boot[249],boot[9749]],'scope':'Bothmatchedprice-minusunitgains, samefamily/colorcoupling; allobservedactualpolicyWDLknown. No inferencefromdifferenceinmarginalsignificance, nohumangridfit/newholdout.'})
(O/'result.json').write_text(json.dumps({'status':'PASS_ZERO_QUERY_MATCHED_FAMILY_GAIN_INTERACTIONS','comparisons':comparisons,'actual_go':0},indent=2));print(comparisons)
