"""Post-seal physical cost breakdown; no search, continuation or outcome change."""
from pathlib import Path
from collections import defaultdict
import json,hashlib,sys,time
D=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists();start=time.perf_counter();expected={'games.jsonl': '60c8ac952c55e11ff44d5d1707331bf2c807a8b30b7136c15c594ef0ffaf4b1c', 'queries.jsonl': '99bbfb3131a66884e46d207d64680af826aa4ee209ed40046e1de354037f8043'}
for n,h in expected.items():
 with(D/n).open('rb')as f:assert hashlib.file_digest(f,'sha256').hexdigest()==h,n
rows={g['slot']:g for g in map(json.loads,(D/'games.jsonl').read_bytes().splitlines())};assert len(rows)==7040;groups=defaultdict(lambda:dict(games=0,queries=0,nodes=0,caller_seconds=0.,kernel_seconds=0.));caps=set()
for g in rows.values():
 if g['reward']is None:caps.add(g['slot'])
 for key in(('all','all'),('censor'if g['reward']is None else'terminal','all'),('rule',str(g['rule'])),('foe',g['foe'])):
  a=groups[key];a['games']+=1;a['queries']+=g['queries'];a['nodes']+=g['nodes']
for line in(D/'queries.jsonl').open():
 q=json.loads(line);g=rows[q['slot']]
 for key in(('all','all'),('censor'if g['reward']is None else'terminal','all'),('rule',str(g['rule'])),('foe',g['foe'])):
  a=groups[key];a['caller_seconds']+=q['caller_seconds'];a['kernel_seconds']+=q['kernel_seconds']
a=groups['all','all'];c=groups['censor','all'];assert c['games']==467 and c['queries']==467*128;assert a['queries']==166514 and a['nodes']==31606003
result=dict(status='COMPLETE_POSTSEAL_PHYSICAL_COST_BREAKDOWN',input_sha256=expected,groups=[dict(kind=k[0],label=k[1],**v)for k,v in sorted(groups.items())],censored_fractions={k:c[k]/a[k]for k in('games','queries','nodes','caller_seconds','kernel_seconds')},seconds=time.perf_counter()-start,scope='Physical7040games ONLY;128logicalUnitrolecopies incur noextraexecutions. Allcandidate+foeworkpaid; equalquerylimits/Hnot equalactualwork/wholelearningcost. CensorstratificationisPOSTHOCdiagnosisnotfilter/newlabel/holdout; no futurecostextrapolation oroldcapextension. NewlargerfamilycountdoesnoteliminateH128identificationwidth; choosechangedquestionbeforeanothercampaign. Recordedclockfieldscome fromoriginalfrozenjournal, notnewsearch.')
out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in result.items()if k!='groups'}))
