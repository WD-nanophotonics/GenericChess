"""Separate action sensitivity, decisive feedback and family information; no fitting."""
from pathlib import Path
from collections import Counter,defaultdict
import json
OUT=Path('results/dev_aux/task2042')
def rows(path):return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()]
def inspect(task,parameter):
 folder=Path('results/dev_aux')/task;games=rows(folder/'games.jsonl');steps=rows(folder/'moves.jsonl');by=defaultdict(list);groups=defaultdict(list)
 for step in steps:by[step['slot']].append(step)
 for g in games:
  opponent=(g.get('opponent_R'),g.get('opponent_B'));phase=g['phase'];groups[(phase,g['family'],g['candidate_side'],opponent)].append(g)
 diagnostics=[]
 for key,gs in groups.items():
  # Unit study separates its two common units; B studies compare all available prices.
  subgroups=defaultdict(list)
  for g in gs:subgroups[g['N'] if parameter=='R' else 720].append(g)
  for unit,group in subgroups.items():
   if len(group)<2:continue
   trajectories=[json.dumps(g['record']['actions'],sort_keys=True) for g in group]
   candidate_first=[];first_sources=[]
   for g in group:
    step=next((s for s in by[g['slot']] if s['side']==g['candidate_side']),None)
    candidate_first.append(None if step is None else json.dumps(step['choice'],sort_keys=True));first_sources.append(None if step is None else step['source'])
   diagnostics.append(dict(phase=key[0],family=key[1],side=key[2],opponent=key[3],unit=unit,profiles=[g[parameter] for g in group],outcomes=[g['outcome'] for g in group],trajectory_sensitive=len(set(trajectories))>1,first_candidate_action_sensitive=len(set(candidate_first))>1,first_sources=first_sources,WDL_sensitive=len({g['outcome'] for g in group})>1,all_draw=all(g['outcome']=='DRAW' for g in group),all_decisive=all(g['outcome'] in ('WIN','LOSS') for g in group),all_candidate_first_proof=all(x in ('PROOF','PROOF_CONTINUATION') for x in first_sources),no_candidate_move=all(x is None for x in first_sources)))
 summary={}
 for phase in sorted({d['phase'] for d in diagnostics}):
  ds=[d for d in diagnostics if d['phase']==phase]
  summary[phase]=dict(comparable_cells=len(ds),family_clusters=len({d['family'] for d in ds}),trajectory_sensitive=sum(d['trajectory_sensitive'] for d in ds),first_action_sensitive=sum(d['first_candidate_action_sensitive'] for d in ds),WDL_sensitive=sum(d['WDL_sensitive'] for d in ds),WDL_informative_families=sorted({d['family'] for d in ds if d['WDL_sensitive']}),all_draw=sum(d['all_draw'] for d in ds),all_decisive=sum(d['all_decisive'] for d in ds),action_sensitive_but_all_draw=sum(d['trajectory_sensitive'] and d['all_draw'] for d in ds),all_candidate_first_proof=sum(d['all_candidate_first_proof'] for d in ds),no_candidate_move=sum(d['no_candidate_move'] for d in ds))
 return dict(summary=summary,cells=diagnostics)
def main():
 result=dict(status='PASS_DESCRIPTIVE_INFORMATION_AUDIT',studies={t:inspect(t,p) for t,p in [('task2030','R'),('task2020','B'),('task2037','B')]},scope='Exposed existing frozen records; no optimizer or price/root selection, no new Native/proof calls. Complete trajectory sensitivity is not strength; finite actual maxply draw is distinguished from UNKNOWN. Counts describe conditional cohorts, not an independent sample or causal board/inventory effect.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v['summary'] for k,v in result['studies'].items()}))
if __name__=='__main__':main()
