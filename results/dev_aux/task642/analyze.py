import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task642';d=json.loads((R/'results/dev_aux/task639/declaration.json').read_bytes());old=json.loads((R/'results/dev_aux/task635/endpoints.json').read_bytes());assert hashlib.sha256((R/'results/dev_aux/task635/games.jsonl').read_bytes()).hexdigest()==d['old_games_sha256'];games=[json.loads(t) for t in (R/'results/dev_aux/task635/games.jsonl').open(encoding='utf-8')];new={};counts=[0,0]
def fast(g):return F(0) if g['termination']['winner'] is None else F(13-len(g['actions'])) if g['termination']['winner']==g['color'] else F(-13)
for line,t in enumerate((R/'results/dev_aux/task640/games.jsonl').open(encoding='utf-8'),1):
 g=json.loads(t);k=(g['replica'],g['profile'],g['root']['index'],g['color']);assert k not in new;new[k]=dict(fast=fast(g),terminal=F(0 if g['termination']['winner'] is None else 32 if g['termination']['winner']==g['color'] else -32),quantity=F(g['raw_quantity'],19),source=dict(file='results/dev_aux/task640/games.jsonl',line=line));counts[g['replica']]+=1
assert counts==[5200,5200];cells=[(r['index'],c,r['source_family']) for r in d['roots'] for c in [0,1]];families=sorted({f for r,c,f in cells});rows=[]
for ctx in d['contexts']:
 u=next(u for u in old['updates'] if u['start']==ctx['start'] and u['iteration']==ctx['iteration']);initial=[]
 for c in u['candidates']:
  gg=[games[s['line']-1] for s in c['sources']];assert [(g['root']['index'],g['color'],g['root']['source_family']) for g in gg]==cells;assert all(g['weights']==c['weights'] for g in gg);initial.append([fast(g) for g in gg]);assert list(map(str,initial[-1]))==c['goals']
 for replica in [-1,0,1]:
  vals=initial if replica==-1 else [[new[(replica,p,r,c)]['fast'] for r,c,f in cells] for p in ctx['profile_indices']];diffs=[[v-vals[0][i] for i,v in enumerate(a)] for a in vals];means=[sum(v)/104 for v in diffs];loo=[[sum(v[i] for i,(r,c,ff) in enumerate(cells) if ff!=f)/sum(ff!=f for r,c,ff in cells) for f in families] for v in diffs];scores=list(map(min,loo));choice=max(range(3),key=lambda j:scores[j]);selected=u['selected_index']
  if replica==-1:assert list(map(str,scores))==u['robust_scores'] and choice==selected
  rows.append(dict(start=ctx['start'],iteration=ctx['iteration'],replica=replica,original_choice=selected,original_accepted=selected!=0,counterfactual_local_choice=choice,all_mean_gains=list(map(str,means)),all_robust_gains=list(map(str,scores)),original_selected_mean_gain=str(means[selected]),original_selected_robust_gain=str(scores[selected]),by_family_for_original_selected=[dict(family=f,gain=str(sum(diffs[selected][i] for i,(r,c,ff) in enumerate(cells) if ff==f)/sum(ff==f for r,c,ff in cells))) for f in families],all_candidate_omission_gains=[list(map(str,x)) for x in loo]))
summ=[]
for st in ['unit','random2514']:
 for replica in [-1,0,1]:
  rr=[x for x in rows if x['start']==st and x['replica']==replica];ac=[x for x in rr if x['original_accepted']];summ.append(dict(start=st,replica=replica,original_accepted_contexts=len(ac),accepted_contexts_positive_mean=sum(F(x['original_selected_mean_gain'])>0 for x in ac),accepted_contexts_positive_robust=sum(F(x['original_selected_robust_gain'])>0 for x in ac),local_choices_same=sum(x['original_choice']==x['counterfactual_local_choice'] for x in rr),accepted_rows=[dict(iteration=x['iteration'],mean=x['original_selected_mean_gain'],robust=x['original_selected_robust_gain']) for x in ac]))
net=[]
for pair in json.loads((O/'netgain_declaration.json').read_bytes())['pairs']:
 for replica in [0,1]:
  for metric in ['fast','terminal','quantity']:
   diffs=[new[(replica,pair['endpoint_profile'],r,c)][metric]-new[(replica,pair['initial_profile'],r,c)][metric] for r,c,f in cells];net.append(dict(start=pair['start'],replica=replica,metric=metric,mean_gain=str(sum(diffs)/104),by_family=[dict(family=f,gain=str(sum(diffs[i] for i,(r,c,ff) in enumerate(cells) if ff==f)/sum(ff==f for r,c,ff in cells))) for f in families],leave_one=[dict(omit=f,gain=str(sum(diffs[i] for i,(r,c,ff) in enumerate(cells) if ff!=f)/sum(ff!=f for r,c,ff in cells))) for f in families],min_leave_one_gain=str(min(sum(diffs[i] for i,(r,c,ff) in enumerate(cells) if ff!=f)/sum(ff!=f for r,c,ff in cells) for f in families))))
out=dict(status='ALL_CONTEXT_AND_RNG_CONTRASTS_FROZEN',rows=rows,summary=summ,endpoint_net_gain=net,physical640games=len(new),new_go=0,original635control_source_hash=d['old_games_sha256'],rng_assignment_limit=json.loads((R/'results/dev_aux/task643/result.json').read_bytes()),scope='ALL24frozenoriginalactualproposalcontexts/ALL3prices/twofreshdrawsets +cachedoriginalcontrol. Localcounterfactualchoice notnewtrainedtrajectory; acceptedcontextgains notsumofdeployedendpointperformance. Allfamily omissions andbothsigns retained; PRNG204unique streamsprefixes vs208nominalslots, no globalIIDconfidence. Independent641physicalaudit requiredbeforevalidatedclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summ));print(json.dumps([x for x in net if x["metric"]=="fast"]))
