"""Frozen unit experiment: independent replay and family-paired descriptive inference."""
from pathlib import Path
import json,hashlib,random,statistics
from collections import Counter
from results.dev_aux.task2034.physical_audit import audit,read,lines
P=Path('results/dev_aux/task2030'); OUT=Path('results/dev_aux/task2034')

def main():
 plan=read(P/'run-plan.json'); done=read(P/'completion.json'); rows=lines(P/'games.jsonl')
 assert len(plan['slots'])==64 and plan['expected_games']==64
 assert read(P/'audit-plan.json')['slots']==plan['slots']
 for path,sha in plan['source_sha'].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==sha,path
 assert done['source_sha']==plan['source_sha'] and done['source_unchanged']
 assert all(x['opponent_R']==720 and x['opponent_nodes']==4096 for x in rows)
 assert Counter((x['family'],x['profile_index'],x['candidate_side']) for x in rows)==Counter((x['family'],x['profile_index'],x['candidate_side']) for x in plan['slots'])
 qualification=read(P/'qualification.json');assert qualification['status']=='PASS' and len(qualification['perfts'])==32
 for journal in ('qualification-run/transport.jsonl','run/transport.jsonl'):
  profile=None;cleared=False
  for event in lines(P/journal):
   if event['event']=='PROFILE':
    profile=event['values'];r,n,b,pawn=profile
    assert f'info string DEV_AUX leafRNBP {r} {n} {b} {pawn} nativeP {pawn} nativeR {r} nativeN {n} nativeB {b} captureP {pawn} captureR {r} captureN {n} captureB {b}' in event['ack'];cleared=False
   elif event['event']=='CLEAR':assert profile==event['values'];cleared=True
   elif event['event']=='INTENT':assert profile==event['R'] and cleared;cleared=False
 physical=audit(P)
 cells={(g['family'],g['candidate_side'],g['profile_index']):g for g in rows}
 assert len(cells)==64 and not physical['incomplete_game_slots']
 families=[]; transitions={}; outcomes={}
 for prof in range(4):outcomes[str(prof)]=dict(Counter(g['outcome'] for g in rows if g['profile_index']==prof))
 for a,b in ((0,1),(2,3)):
  transitions[str((a,b))]=dict(Counter(cells[f,s,a]['outcome']+'->'+cells[f,s,b]['outcome'] for f in range(8) for s in range(2)))
 for f in range(8):
  gains=[statistics.mean(cells[f,s,b]['finite_event_score']-cells[f,s,a]['finite_event_score'] for s in range(2)) for a,b in ((0,1),(2,3))]
  families.append(dict(family=f,delta360=gains[0],delta720=gains[1],interaction=gains[0]-gains[1]))
 rng=random.Random(20261016682029); boots={k:[] for k in ('delta360','delta720','interaction')}
 for _ in range(10000):
  sample=rng.choices(families,k=8)
  for k in boots:boots[k].append(statistics.mean(x[k] for x in sample))
 summary={k:dict(mean=statistics.mean(x[k] for x in families),percentile95=[sorted(v)[249],sorted(v)[9749]],nonzero_families=sum(x[k]!=0 for x in families)) for k,v in boots.items()}
 result=dict(status='PASS',physical=physical,outcomes=outcomes,transitions=transitions,families=families,summary=summary,planned=64,observed=len(rows),unrun=[],qualification=32,interpretation='Descriptive ONLY. No equivalence margin: interval containing zero does not establish unit invariance. Eight families, fixed opponent, finite rule max96, modified material search. No selector or new Native/proof execution in audit.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(outcomes=outcomes,summary=summary,physical=physical)))
if __name__=='__main__':main()
