from pathlib import Path
import json,importlib.util,collections,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1544';O.mkdir(exist_ok=False)
sp=importlib.util.spec_from_file_location('T',R/'results/dev_aux/task1531/rules.py');T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T)
G=R/'results/dev_aux/task1538';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));v=json.loads((G/'values.json').read_bytes())['value'];edge={x['id']:dict(x['moves']) for x in map(json.loads,(G/'edges.jsonl').read_text().splitlines())};summaries=[]
for tid,studyid,selector in [(1541,1538,None)]:
 P=R/f'results/dev_aux/task{tid}';result=json.loads((P/'result.json').read_bytes());assert result['status']=='COMPLETE' and result['all_owned_engines_closed'];study=json.loads((R/f'results/dev_aux/task{studyid}/study.json').read_bytes());gs=[json.loads(x) for x in (P/'choices.jsonl').read_text().splitlines()];phase=gs[0]['phase'];prices=study['R_grid'];fam=[x for x in study['families'] if x['phase']==phase];expected=[(b,p,f['family'],i) for b in study['nodes'] for p in prices for f in fam for i in f['state_ids']];assert [(x['node_budget'],x['leafR'],x['family'],x['state_id']) for x in gs]==expected
 counts=collections.Counter();observed=collections.defaultdict(list);contradictions=[]
 for x in gs:
  sid=x['state_id'];s=states[sid];assert x['phase']==phase and x['leafN']==720 and x['nativeR']==720 and x['position']=='position fen '+T.fen(s) and x['command']==f"go nodes {x['node_budget']}";assert x['move'] in edge[sid] and x['child_id']==edge[sid][x['move']] and x['root_WDL']==v[sid] and x['chosen_WDL']==-v[x['child_id']] and x['regret']==v[sid]+v[x['child_id']];counts['exact_labels']+=1
  maxnodes=0
  for line in x['uci_info']:
   fs=line.split()
   if 'tbhits' in fs:assert int(fs[fs.index('tbhits')+1])==0;counts['no_external_tablebase']+=1
   if 'nodes' in fs:maxnodes=max(maxnodes,int(fs[fs.index('nodes')+1]))
   if 'score' in fs and fs[fs.index('score')+1]=='mate':
    score=int(fs[fs.index('score')+2]);counts['mate_scores']+=1
    if score and (1 if score>0 else -1)!=v[sid]:contradictions.append({'tid':tid,'state_id':sid,'line':line,'exact_rootWDL':v[sid]})
   if 'pv' in fs:
    q=s
    for u in fs[fs.index('pv')+1:]:ll=dict(T.moves(q));assert u in ll;q=ll[u];counts['literal_PVmoves']+=1
  observed[x['node_budget']].append(maxnodes)
 summaries.append({'task':tid,'phase':phase,'counts':dict(counts),'reported_node_counters':{b:{'min':min(a),'max':max(a),'sum':sum(a)} for b,a in observed.items()},'native_mate_score_vs_exact_WDL_contradictions':contradictions,'choices_sha256':hashlib.sha256((P/'choices.jsonl').read_bytes()).hexdigest()})
(O/'result.json').write_text(json.dumps({'status':'PASS_CASES_CHOICES_PV_LABELS_COUNTERS','rows':summaries,'scope':'Every sampled engine choice/legalPV and exactWDL label audited; native mate score disagreements separately listed, not treated as certificate. Initial1498 split remains downgraded,1503newfullorbits.'},indent=2));print([{k:v for k,v in x.items() if k!='native_mate_score_vs_exact_WDL_contradictions'}|{'mate_contradictions':len(x['native_mate_score_vs_exact_WDL_contradictions'])} for x in summaries])
