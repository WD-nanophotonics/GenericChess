from pathlib import Path
import json,random,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1601';O.mkdir(exist_ok=False);G=R/'results/dev_aux/task1583';states=list(map(tuple,json.loads((G/'states.json').read_bytes())));ix={s:i for i,s in enumerate(states)};v=json.loads((G/'values.json').read_bytes())['value'];edges=[json.loads(x)['moves'] for x in (G/'edges.jsonl').open()];old=json.loads((R/'results/dev_aux/task1586/study.json').read_bytes());excluded={f['orbit_id'] for f in old['families']};families={}
def orbit(s):
 out=[]
 for fx in [False,True]:
  for fy in [False,True]:
   a=[12 if z==12 else (2-z%3 if fx else z%3)+3*(3-z//3 if fy else z//3) for z in s[:8]];out.extend([tuple(a+[s[8]]),tuple(a[4:]+a[:4]+[1-s[8]])])
 return sorted(set(ix[q] for q in out))
for i,s in enumerate(states):
 if sum(x!=12 for x in s[:8])!=5 or sum(x!=12 for x in s[4*s[8]:4*s[8]+4])!=3:continue
 ll=edges[i]
 if len(ll)<2 or len({-v[j] for u,j in ll})<2 or any(v[j]==-1 and not edges[j] for u,j in ll):continue
 ids=orbit(s);key=min(ids)
 if key not in excluded:families.setdefault(key,ids)
keys=sorted(families);random.Random(2026676000).shuffle(keys);out=[]
for f,key in enumerate(keys[:192]):
 ids=families[key];a=min(i for i in ids if states[i][8]==0);s=states[a];b=ix[tuple(s[4:8]+s[:4]+(1-s[8],))];out.append({'family':f,'phase':'TRAIN' if f<64 else 'DEV','orbit_id':key,'all_symmetry_ids':ids,'state_ids':[a,b]})
plan={'status':'INPUTS_ONLY_NO_QUERY_OR_LEARNING_EXECUTED','question':'Can firstchoiceperfectfuture cheaptrueWDL pricelearning predict complete5policy/common4 gains on freshrootfamilies?','source_graph':'task1583','source_previous_root_study':'task1586','rule_domain':old['pieces'],'seed':2026676000,'TRAIN':64,'DEV':128,'R_grid':old['R_grid'],'B_grid':old['B_grid'],'N':720,'nodes':64,'firstchoice_selector':'TRAINglobalmax lowerlexR,B tie, noDEVselection','firstchoice_max_go':2048,'firstchoice_seconds':180,'fullpolicy_control_seconds':3300,'fullpolicy_control':'OnlyTRAINselectedprimary plus720720, newDEV128; opponentALLuntilcapture thencommon4oracle, exactclosureorUNKNOWNbounds','long_run_limit':'No singleexpected>1h; do notresetexisting1587cap. This inputs-only nextstudy cannotcomplete or extend1587.','family_filter':old['family_filter'],'heldout_scope':'Newrootfullorbits disjoint1586, continuationstatesmayoverlap. No unexposedallstates claim.','families':out,'excluded_prior_family_orbits':len(excluded),'input_hashes':old['input_hashes'],'actual_new_go':0}
(O/'plan.json').write_text(json.dumps(plan,indent=2));(O/'result.json').write_text(json.dumps({'status':plan['status'],'frozen_families':len(out),'excluded_prior_families':len(excluded),'new_go':0,'scope':'Nextcost-reductiondecision begun by actualpriceblindinputfreezing; not claimedrun orsuccess.'},indent=2));print(plan['status'],len(out))
