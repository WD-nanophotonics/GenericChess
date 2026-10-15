"""Fixed common-budget opponent sensitivity, not independent training replication."""
from pathlib import Path
from collections import Counter
import json,hashlib
from results.dev_aux.task1992.physical_audit import audit,read,lines
from results.dev_aux.task1988.audit import interval
ROOT=Path('results/dev_aux/task1991');OUT=Path('results/dev_aux/task1992')
def run():
 p=read(ROOT/'run-plan.json');physical=audit(ROOT);rows=lines(ROOT/'games.jsonl');moves=lines(ROOT/'moves.jsonl');assert physical['full_study_complete']
 assert p['opponent_cached'] and p['opponent_proof_nodes']==p['candidate_proof_nodes']==1024
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 assert len(rows)==128 and all('bank_hit' in m and not m['bank_hit'] for m in moves)
 def key(g):return g['family'],g['candidate_side'],g['R'],g['opponent_R']
 cells={key(g):g for g in rows};r=read('results/dev_aux/task1985/selection.json')['selected_R']
 assert set(cells)=={(f,s,price,o) for f in range(8) for s in (0,1) for price in (720,r) for o in (360,720,1440,2880)}
 old={key(g):g for g in lines('results/dev_aux/task1987/games.jsonl')}
 ds=[sum(cells[f,s,r,o]['finite_event_score']-cells[f,s,720,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(8)]
 oldds=[sum(old[f,s,r,o]['finite_event_score']-old[f,s,720,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(8)]
 interaction=[a-b for a,b in zip(ds,oldds)]
 result=dict(status='PASS_FIXED_COMMON_BUDGET_SENSITIVITY',physical=physical,prices=[720,r],mean_price_delta=sum(ds)/8,family_deltas=ds,bootstrap8family_interval=interval(ds,20261016661992),old_same8family_price_delta=sum(oldds)/8,interaction=dict(mean=sum(interaction)/8,bootstrap8family_interval=interval(interaction,20261016661993)),outcomes={price:dict(Counter(x['outcome'] for x in rows if x['R']==price)) for price in (720,r)},recorded_game_seconds=sum(x['seconds'] for x in rows),old_samecases_seconds=sum(old[key(x)]['seconds'] for x in rows),outer_late_steps=sum(m['seconds']>=p['step_seconds'] for m in moves),scope='ALLfirst8ordinal shared1986families/fourfixedopponentprices/bothroles, notfresh32familyreplication or learning. Bothactorssame cachedPN1024/verify/normal4096/phasecaps, independentcoldperactorbanks. Priceeffect is controlled WITHIN newcondition; crosscondition changes opponentproof+cache completepolicy, cannotisolatePN-onlycausality. No theoreticalWDL/materialreward/parameterfilter; UNKNOWNdistinct.')
 with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k not in ('physical','family_deltas')}))
if __name__=='__main__':run()
