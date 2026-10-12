import json,sys,time,hashlib,re,math,collections
from pathlib import Path
from fractions import Fraction
R=Path.cwd();O=R/'results/dev_aux/task409';O.mkdir(exist_ok=True);t0=time.monotonic();folder=R/'results/dev_aux/task406';e=json.loads((folder/'endpoints.json').read_text(encoding='utf-8'));r=json.loads((folder/'result.json').read_text(encoding='utf-8'));games=[json.loads(x) for x in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()];d=json.loads((R/'results/dev_aux/task405/declaration.json').read_text(encoding='utf-8'));axes=d['axes'];metrics=[];resources=[]
def goalmean(v):return sum((Fraction(x) for x in v),Fraction())/len(v)
def sourcegames(rows):return [games[s['line']-1] for row in rows for s in row['sources']]
def cost(rows):
 refs=sorted({s['line'] for row in rows for s in row['sources']});gs=[games[i-1] for i in refs];qs=[q for g in gs for q in g['queries']];reported=[];missing=0;depth=[]
 for q in qs:
  infos=[l for l in q['lines'] if l.startswith('info ') and re.search(r'\bnodes (\d+)',l)]
  if infos:
   last=infos[-1];reported.append(int(re.search(r'\bnodes (\d+)',last).group(1)));dm=re.search(r'\bdepth (\d+)',last)
   if dm:depth.append(int(dm.group(1)))
  else:missing+=1
 return dict(logical_games=sum(len(row['sources']) for row in rows),distinct_physical_source_games=len(gs),go=sum(len(g['queries']) for g in gs),gamewall_sum=sum(g['seconds'] for g in gs),go_transport_seconds=sum(q['seconds'] for q in qs),reported_lastinfo_nodes_sum=sum(reported),queries_without_reported_nodes=missing,node_range=[min(reported),max(reported)] if reported else [],depth_range=[min(depth),max(depth)] if depth else [],scope='sourceunique resources may overlap acrossmethods; nocausalexclusivewall/equaltimeclaim, actual lastinfo counters not total hiddenwork certificate')
for endpoint in e['endpoints']:
 method=endpoint['method'];family=endpoint['family'];fitrows=[row for rr in e['rounds'] if rr['family']==family for row in rr['candidates']] if method=='coordinate' else [row for u in e['updates'] if u['family']==family for row in u['candidates'][1:]];resources.append(dict(method=method,family=family,**cost(fitrows)))
 for phase in ['train_endpoint_diagnostic','development']:
  prefix=method+'-'+family
  initial=next(x for x in r['diagnostics'] if x['phase']==phase and prefix+'-initial' in x['names']);final=next(x for x in r['diagnostics'] if x['phase']==phase and prefix+'-endpoint' in x['names']);pairs=[Fraction(a)-Fraction(b) for a,b in zip(final['goals'],initial['goals'])];familymeans=[sum(pairs[i:i+2])/2 for i in range(0,8,2)];leaveone=[sum(x for j,x in enumerate(familymeans) if j!=i)/3 for i in range(4)]
  metrics.append(dict(method=method,family=family,phase=phase,initial_mean=initial['mean_goal'],endpoint_mean=final['mean_goal'],mean_delta=str(sum(pairs)/8),quantity_initial=initial['mean_quantity'],quantity_endpoint=final['mean_quantity'],paired_cell_delta=[str(x) for x in pairs],root_family_delta=[str(x) for x in familymeans],leave_one_family_out_mean_delta=[str(x) for x in leaveone],initial_true_wins=initial['true_wins'],initial_true_losses=initial['true_losses'],endpoint_true_wins=final['true_wins'],endpoint_true_losses=final['true_losses'],changed_price_axes=sum(endpoint['initial'][a]!=endpoint['endpoint'][a] for a in axes),endpoint_log_distance_from_initial=sum((math.log(endpoint['endpoint'][a]/endpoint['initial'][a]))**2 for a in axes)/12,scope='eightpairedcells/fourindependentgeneratorseeds; no sampling CI/no price/model selection'))
probe=[]
for u in e['updates']:
 diffs=[Fraction(x) for x in u['paired_plus_minus_goal_difference']];fm=[sum(diffs[i:i+2])/2 for i in range(0,8,2)];avg=sum(fm)/4;loo=[sum(x for j,x in enumerate(fm) if i!=j)/3 for i in range(4)];sgn=lambda v:(v>0)-(v<0);probe.append(dict(family=u['family'],iteration=u['iteration'],mean=str(avg),rootfamily_means=[str(x) for x in fm],leave_one_rootfamily_means=[str(x) for x in loo],leaveone_sign_agreement=sum(sgn(x)==sgn(avg) for x in loo),directions=u['direction']))
result=dict(endpoint_sha256=hashlib.sha256((folder/'endpoints.json').read_bytes()).hexdigest(),metrics=metrics,resources=resources,probe_family_sensitivity=probe,actual_total={k:r[k] for k in ['seconds','new_games','new_go','logical_games','cache_hits']},fit_total={k:e[k] for k in ['fit_seconds','fit_new_games','fit_new_go','fit_cache_hits','fit_logical_games']},seconds=time.monotonic()-t0,new_go=0,scope='allfrozenendpoints nohumanread/selection; no density/uniquecoverage explanation inferred from meanonly')
(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['probe_family_sensitivity','resources']}))