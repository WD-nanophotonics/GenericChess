from pathlib import Path
import json,collections,random,math
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task1089';O.mkdir(exist_ok=False)
def load(task):return [json.loads(x) for x in (R/f'results/dev_aux/task{task}/games.jsonl').read_text().splitlines()]
def val(g):return (g['label']=='W')-(g['label']=='L')
whole=load(1043)+load(1046);families=sorted(set(g['root']['seed'] for g in whole));comp={g['root']['seed']:g['root']['composition'] for g in whole};index={(g['price'],g['opponent'],g['root']['seed'],g['color']):g for g in whole};opps=['unit_search','high_search','uniform_random'];groups=[[s for s in families if comp[s]==c] for c in sorted(set(comp.values()))];out=[]
for p,b in [(262,90),(1718,90),(1718,262)]:
 d={s:sum(val(index[p,opp,s,c])-val(index[b,opp,s,c]) for opp in opps for c in [False,True]) for s in families};rng=random.Random(2026179000);samples=sorted(sum(d[rng.choice(group)] for group in groups for _ in group)/(len(families)*6) for _ in range(10000));byopp=[]
 for opp in opps:
  changes=[(index[p,opp,s,c]['label'],index[b,opp,s,c]['label']) for s in families for c in [False,True]]
  byopp.append(dict(opponent=opp,delta=str(F(sum(val(index[p,opp,s,c])-val(index[b,opp,s,c]) for s in families for c in [False,True]),128)),label_transitions=dict(collections.Counter(a+'<-'+z for a,z in changes)),composition_delta={cc:str(F(sum(val(index[p,opp,s,c])-val(index[b,opp,s,c]) for s in families if comp[s]==cc for c in [False,True]),32)) for cc in sorted(set(comp.values()))}))
 out.append(dict(price=p,baseline=b,paired64_family_delta=str(F(sum(d.values()),384)),stratified_family_bootstrap_95_percentile=[samples[249],samples[9749]],bootstrap_replicates=10000,seed=2026179000,opponents=byopp))
base=load(1043);joint=load(1059);fixed=load(1068);fac=[]
for p in [90,262]:
 profiles={}
 for sc,os in [(1,1),(4,1),(1,4),(4,4)]:
  gg=base if sc==os==1 else joint if sc==os==4 else fixed
  xx=[g for g in gg if g['price']==p and g['opponent']=='unit_search' and (sc==os==1 or g.get('scale')==sc and (sc==os==4 or g['opp_scale']==os))]
  assert len(xx)==32;profiles[f'{sc},{os}']=dict(N=len(xx),J16=str(F(sum(val(g) for g in xx),32)),counts=dict(collections.Counter(g['label'] for g in xx)),by_case={(g['root']['seed'],g['color']):g for g in xx})
 origin=profiles['1,1'];summ=[]
 for tag,v in profiles.items():
  summ.append(dict(condition=tag,J16=v['J16'],counts=v['counts'],same_paths=sum([a['move'] for a in g['actions']]==[a['move'] for a in origin['by_case'][k]['actions']] for k,g in v['by_case'].items()),real_reward_changed=sum(val(g)!=val(origin['by_case'][k]) for k,g in v['by_case'].items()),label_changed=sum(g['label']!=origin['by_case'][k]['label'] for k,g in v['by_case'].items())))
 fac.append(dict(price=p,conditions=summ,interaction=str(F(profiles['4,4']['J16'])-F(profiles['4,1']['J16'])-F(profiles['1,4']['J16'])+F(profiles['1,1']['J16']))))
trees=json.loads((R/'results/dev_aux/task1085/result.json').read_bytes())['roots'];theorem=dict(roots=len(trees),positive_rank_boundary_gt270=sum(any(F(x)>270 for x in r['pairwise_positive_boundaries']) for r in trees),allbest262_vs419_changed=sum(next(x for x in r['curve'] if x['price']==262)['all_best']!=next(x for x in r['curve'] if x['price']==419)['all_best'] for r in trees),allbest419_vs671_changed=sum(next(x for x in r['curve'] if x['price']==419)['all_best']!=next(x for x in r['curve'] if x['price']==671)['all_best'] for r in trees),largest_rank_boundaries=sorted(set(F(x) for r in trees for x in r['pairwise_positive_boundaries']))[-8:])
theorem['largest_rank_boundaries']=list(map(str,theorem['largest_rank_boundaries']))
result=dict(status='ZERO_GO_DESCRIPTIVE_PAIRED_FAMILY_AND_FACTORIAL_REANALYSIS',interval_replication=out,factorial=fac,richer_two_ply=theorem,scope='Conditional estimates/exploratoryuncertainty; no equivalence/significance declaration/multipletestfit. Bootstrapfamilieswithin4frozencomposition strata preservesbothcolors/oppscorrelation. NOTuniversalpriceproof.')
(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print([(x['price'],x['baseline'],x['paired64_family_delta'],x['stratified_family_bootstrap_95_percentile']) for x in out]);print(fac);print(theorem)
