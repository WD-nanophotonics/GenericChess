import json,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task681';d=json.loads((R/'results/dev_aux/task675/deployment_declaration.json').read_bytes());prefix=json.loads((R/'results/dev_aux/task678/result.json').read_bytes())['prefixes'];lookup={(x['replica'],x['profile'],x['root'],x['color'],x['cap']):x for x in prefix};games=[json.loads(x) for x in (R/'results/dev_aux/task676/games.jsonl').open(encoding='utf-8')];gameidx={(g['replica'],g['profile'],g['root']['index'],g['color']):(g,i) for i,g in enumerate(games,1)};rows=[];witness=[]
for pair in d['pairs']:
 for replica in [0,1]:
  for f in d['roots']:
   for c in [0,1]:
    a,b=[[lookup[(replica,pi,f['index'],c,H)] for H in [12,24]] for pi in [pair['initial_profile'],pair['endpoint_profile']]];q=[F(b[i]['quantity']-a[i]['quantity'],19) for i in range(2)];rec=dict(route=pair['route'],start=pair['start'],replica=replica,root=f['index'],family=f['source_family'],color=c,H12_quantity_gain=str(q[0]),H24_quantity_gain=str(q[1]),positive12_nonpositive24=q[0]>0 and q[1]<=0,positive12_negative24=q[0]>0 and q[1]<0,positive12_endpoint_loss24=q[0]>0 and b[1]['termination']['winner'] is not None and b[1]['termination']['winner']!=c,terminations=dict(initial12=a[0]['termination'],endpoint12=b[0]['termination'],initial24=a[1]['termination'],endpoint24=b[1]['termination']));rows.append(rec)
    if rec['positive12_nonpositive24']:
     aa,ai=gameidx[(replica,pair['initial_profile'],f['index'],c)];bb,bi=gameidx[(replica,pair['endpoint_profile'],f['index'],c)];n=0
     while n<min(len(aa['actions']),len(bb['actions'])) and aa['actions'][n]['move']==bb['actions'][n]['move']:n+=1
     witness.append(dict(**rec,initial_source_line=ai,endpoint_source_line=bi,first_action_divergence=n,initial_weights=aa['weights'],endpoint_weights=bb['weights'],initial_actions=[dict(ply=i,move=a['move'],actor=a['actor'],captured=a['captured'],drop=a['drop'],promotion=a['promotion']) for i,a in enumerate(aa['actions'])],endpoint_actions=[dict(ply=i,move=a['move'],actor=a['actor'],captured=a['captured'],drop=a['drop'],promotion=a['promotion']) for i,a in enumerate(bb['actions'])]))
summ=[]
for route in ['joint','coordinate']:
 for st in ['unit','random2514']:
  x=[r for r in rows if r['route']==route and r['start']==st];summ.append(dict(route=route,start=st,cells=len(x),positive12=sum(F(r['H12_quantity_gain'])>0 for r in x),positive12_nonpositive24=sum(r['positive12_nonpositive24'] for r in x),positive12_negative24=sum(r['positive12_negative24'] for r in x),positive12_endpoint_loss24=sum(r['positive12_endpoint_loss24'] for r in x)))
out=dict(status='ALL256_SAME_CELL_TEMPORAL_PROXY_CONTRASTS',summary=summ,rows=rows,all_counterexamples=witness,new_go=0,source_sha256=hashlib.sha256((R/'results/dev_aux/task676/games.jsonl').read_bytes()).hexdigest(),scope='Everyfourendpoint/owninitial×2draw×16root×bothcolor samephysicalH24paths andliteralH12prefix. PositiveH12quantity laternonpositive/negative oractualendpointloss24 cases retainedALL, no favorablemodel selection. Temporalcontradiction doesnotprovebadprice/horizonuniformly andH24cutoffnotfinalWDL; root/policydistribution distinctfromhumanvaluevalidation. Differentpaths notsameactions afterfirstchange. Already677physical/678prefix/679actualcapqualification verified; zeronewgo/no learning.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summ));print('ALL_COUNTEREXAMPLES',len(witness))
