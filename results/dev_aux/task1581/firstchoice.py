from pathlib import Path
import json,collections
R=Path.cwd();P=R/'results/dev_aux/task1587';O=R/'results/dev_aux/task1597';O.mkdir(exist_ok=False);oracle=json.loads((R/'results/dev_aux/task1583/values.json').read_bytes())['value'];study=json.loads((R/'results/dev_aux/task1586/study.json').read_bytes());rows=[]
for f in sorted(P.glob('*_TRAIN_result.json')):
 d=json.loads(f.read_bytes());prefix=f.name.removesuffix('_result.json');cache={x['sid']:x for x in map(json.loads,(P/(prefix+'_choices.jsonl')).open())};g=json.loads((P/(prefix+'_graph.json')).read_bytes());vv=json.loads((P/(prefix+'_values.json')).read_bytes())['value'];first=[];cross=collections.Counter();actualroot=dict()
 for fam,i in g['roots']:
  sid,c=g['keys'][i];child=cache[sid]['child'];one=-oracle[child];actual=vv[i];assert actual<=one;first.append([fam,one]);cross[one,actual]+=1
 rows.append({'R':d['R'],'B':d['B'],'onechoice_perfect_future_mean':sum(x for fam,x in first)/len(first),'actual_fivepolicy_common4_mean':d['mean'],'onechoice_to_full_WDL':{str(k):n for k,n in cross.items()},'root_vector':first,'minimum_native_root_go_if_only_firstchoice':len(first),'actual_profile_owned_go':sum(1 for _ in (P/(prefix+'_choices.jsonl')).open())})
out={'status':'COMPLETED_PROFILE_SNAPSHOT_ONECHOICE_VS_FULL_CONVERSION','rows':rows,'scope':'Exploratoryzero-go scoring of SAME completedTRAIN actualcoldfirstchoices; onechoiceperfectfuture is changedcompositepolicy trueWDL, notfullnativepolicy. NoTRAINselectorchange/no DEVselection/no humanfit. Costs hypotheticalrootonly counts, not executed alternatelearner.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{k:v for k,v in x.items() if k!='root_vector'} for x in rows])
