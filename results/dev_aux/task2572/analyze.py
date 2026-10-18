"""Candidate-only search-context interaction; fixed plain foes, all censoring."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,itertools,sys
from results.dev_aux.task2568.summary import contrast,bounds
D=Path('results/dev_aux/task2572')
def load(p):return json.loads(Path(p).read_text())
def run():
 p=load(D/'eval-plan.json');reg=load(D/'freeze.json');ev=load(D/'eval-result.json');t=load(D/'result.json');old=load('results/dev_aux/task2568/result.json');start=load(D/'eval-started.json')
 assert start['utc']>reg['registered_at']
 for n,h in reg['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert t['source_sha']==hashlib.sha256(Path('results/dev_aux/task2568/result.json').read_bytes()).hexdigest()
 for a in t['arms']:
  src=next(x for x in old['arms']if x['seed']==a['seed']and x['method']==('TD'if a['original_method']=='initial'else a['original_method']));assert a['weights']==src['initial'if a['original_method']=='initial'else'weights']
 expected=set(itertools.product([0],[1977,8173,27182,31415],range(451001,451003),[0,1],[m+'|'+c for m in('initial','TD','TC','WDL')for c in('plain','q2')],p['foes']));assert len(p['slots'])==256 and set(map(tuple,p['slots']))==expected
 rr={tuple(g['slot']):g for g in map(json.loads,(D/'eval-games.jsonl').open())};assert len(rr)==ev['actual'];stats=defaultdict(Counter);queries=0
 for q in map(json.loads,(D/'eval-queries.jsonl').open()):
  gs,seed,family,color,treatment,foe=q['slot'];candidate=q['actor']==color;quiet=candidate and treatment.endswith('|q2');assert q['candidate_q2']==quiet
  s=q['search_stats'];assert s['q_limit']==2
  if not quiet:assert s['qnodes']==s['q_truncated_leaf_labels']==s['q_cap_still_tactical']==0
  stats[treatment+('/candidate'if candidate else'/fixed_plain_foe')].update(dict(queries=1,nodes=q['nodes'],failed=not q['complete'],qnodes=s['qnodes'],check_evasion_nodes=s['check_evasion_nodes'],q_truncated_leaf_labels=s['q_truncated_leaf_labels'],q_cap_still_tactical=s['q_cap_still_tactical']));queries+=1
 assert queries==ev['queries'];assert sum(v['qnodes']for k,v in stats.items()if k.endswith('|q2/candidate'))>0,'Tacticalcandidatecontextmustactuallyexecuteqnodes'
 within={m:{c:{f:contrast(rr,[s for s in p['slots']if s[5]==f],m+'|'+c,'initial|'+c)for f in p['foes']}for c in('plain','q2')}for m in('TD','TC','WDL')};interaction={}
 for m in('TD','TC','WDL'):
  interaction[m]={}
  for foe in p['foes']:
   cells=[]
   for seed,fam,color in itertools.product([1977,8173,27182,31415],range(451001,451003),[0,1]):
    a,b,c,d=[bounds(rr.get((0,seed,fam,color,label,foe)))for label in(m+'|q2','initial|q2',m+'|plain','initial|plain')];lo=a[0]-b[1]-c[1]+d[0];hi=a[1]-b[0]-c[0]+d[1];cells.append(dict(seed=seed,family=fam,color=color,bounds=[lo,hi]))
   interaction[m][foe]=dict(n=len(cells),bounds=[sum(c['bounds'][i]for c in cells)/len(cells)for i in(0,1)],cells=cells)
 seedcurves={str(seed):{m:{ctx:{foe:contrast(rr,[s for s in p['slots']if s[1]==seed and s[5]==foe],m+'|'+ctx,'initial|'+ctx)for foe in p['foes']}for ctx in('plain','q2')}for m in('TD','TC','WDL')}for seed in [1977,8173,27182,31415]}
 rolecurves={str(color):{m:{ctx:{foe:contrast(rr,[s for s in p['slots']if s[3]==color and s[5]==foe],m+'|'+ctx,'initial|'+ctx)for foe in p['foes']}for ctx in('plain','q2')}for m in('TD','TC','WDL')}for color in(0,1)}
 controls=uncertain=0
 for g in rr.values():
  for h in rr.values():
   if tuple(g['slot'])>=tuple(h['slot'])or g['slot'][:4]!=h['slot'][:4]or g['slot'][5]!=h['slot'][5]or g['slot'][4].split('|')[1]!=h['slot'][4].split('|')[1]or g['weights']!=h['weights']:continue
   if g['outcome']is None or h['outcome']is None:uncertain+=1;continue
   assert all(g[k]==h[k]for k in('record','reward','nodes','queries'));controls+=1
 r=dict(status='PASS_ALL_CONTEXT_BINDINGS_AND_QUERY_POLICIES',EVAL=ev,within_context_gain=within,difference_of_gains=interaction,all_seed_curves=seedcurves,all_role_curves=rolecurves,actual_query_cost_by_candidate_context_and_actor=dict(stats),same_weight_same_context_terminal_controls=controls,unresolved_controls=uncertain,new_training_nodes=0,additional_eval_nodes=ev['nodes'],additional_eval_seconds=ev['seconds'],scope='Candidatecontext changesonly; opponent remainsD2plain. Same8192node/2second querycaps, actualcosts differ. Tacticalq2approximation retainsallcheckevasions, maytruncate noncheckcaptures. CensorboundsnotCI; unknownnotdraw. Allseed/role/pricecells, norefit/bestselection. Finiteinteraction[-4,4] ofW-L gains, notpurepricecausalidentifiability.')
 (D/'summary.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(status=r['status'],eval=ev,gains={m:{c:{f:v['bounds']for f,v in fs.items()}for c,fs in cs.items()}for m,cs in within.items()},interaction={m:{f:v['bounds']for f,v in fs.items()}for m,fs in interaction.items()},controls=controls)))
if __name__=='__main__':run()
