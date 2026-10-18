"""Post-seal derivative responsiveness, not actual TD credit or learning gain."""
from pathlib import Path
from collections import defaultdict
from math import sqrt
import json,sys,os
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
STOP=Path(os.environ.get('GC_REPLAY_STOP_ROOT',str(R)));assert all(not any(json.loads((STOP/'.local_agent'/(n+'.json')).read_bytes()).get(k)for k in('stopped','user_paused'))for n in('rollout','advisor','slack'));D=R/'.local_agent/static-input-objective-20261018';U=R/'.local_agent/filter-search-inputs-20261018';groups=defaultdict(list)
for model,directory in [('Unit',U),('static',D)]:
 for q in map(json.loads,(directory/'queries.jsonl').read_bytes().splitlines()):
  if q['status']=='TERMINAL_ROOT':norm=bound=0.
  elif q['status']=='USABLE_NATIVE_RETURN':norm=sqrt(sum(x*x for x in q['gradient']));bound=(1+abs(q['leaf_prediction']))*norm
  else:continue
  groups[model,q['prefix'],q['filter']].append(dict(l2=norm,bound=bound,nodes=q['query_nodes'],nonzero=q['gradient_nonzero']))
rows=[]
for k,values in sorted(groups.items()):
 l2=sorted(v['l2']for v in values);b=sorted(v['bound']for v in values);nodes=sum(v['nodes']for v in values);rows.append(dict(model=k[0],prefix=k[1],filter=k[2],returned_points=len(values),unavailable_generation=768-len(values),nonzero=sum(v['nonzero']for v in values),sum_gradient_l2=sum(l2),gradient_l2_per_intended_slot=sum(l2)/768,median_returned_gradient_l2=l2[len(l2)//2],sum_zero_incoming_trace_update_coefficient_bound=sum(b),bound_per_intended_slot=sum(b)/768,Native_nodes=nodes,gradient_l2_sum_per_million_Native_nodes=sum(l2)/nodes*1e6 if nodes else None))
write_json(D/'response-bound-analysis.json',dict(status='POSTHOC_DESCRIPTOR_NOT_UPDATE_ESTIMATE',rows=rows,formula='ForoneTDobservation withincomingeligibilityzero, boundednexttarget z in[-1,1], ||eta*(z-pred)*gradient||2 <=eta*(1+abs(pred))*||gradient||2. Noetaorerrorchosen/fitted.',scope='Actualselectedleafderivatives only, no residuals/episodecredit/learninggain orpopulationclaim. Terminalown-gradient0, pasteligibilitymayremain. Threegenerationrefusals unavailableinintendedslotmeasure, not measuredzero. Nativeworkcounts excludegeneration/profile/recording and are notfullwallcost. Coefficientcoordinates unnormalized, allactualtypes retained.'))
print('RESPONSIVENESS',[(r['model'],r['prefix'],r['filter'],round(r['gradient_l2_per_intended_slot'],6),round(r['bound_per_intended_slot'],6))for r in rows])
