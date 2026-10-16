"""Resource-equivalence limits for explicit source reuse, no trajectory-equality claim."""
from pathlib import Path
from collections import defaultdict,Counter
import json,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2370')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());stop();folder=Path('results/dev_aux/task2358');games=[json.loads(x)for x in(folder/'games.jsonl').read_text().splitlines()];ds=[json.loads(x)for x in(folder/'decisions.jsonl').read_text().splitlines()];gs={g['slot']:g for g in games};groups=defaultdict(list)
 for d in ds:groups[(gs[d['slot']]['reused'],d['is_candidate'])].append(d)
 rows=[]
 for key,data in groups.items():
  stop();rows.append(dict(reused=key[0],candidate=key[1],calls=len(data),caller_shortened=sum(dict(d['phase_limits'])['total_seconds']<d['caller_seconds']-1e-6 for d in data),ordinary_depths=dict(Counter(str(d['normal_receipt']['completed_depth'])for d in data if d['normal_receipt']is not None)),ordinary_causes=dict(Counter(d['normal_receipt']['exit_cause']for d in data if d['normal_receipt']is not None)),measured_seconds=sum(d['measured_seconds']for d in data)))
 result=dict(status='PASS_RECORDED_SOURCE_RESOURCE_DIAGNOSIS',groups=rows,game_seconds_by_source={kind:sum(g['seconds']for g in games if g['reused']==(kind=='reused'))for kind in('reused','new')},new_commits_bytes=Path('results/dev_aux/task2355/commits.jsonl').stat().st_size,prepaid_reference_seconds={'2248':259.22648009998375,'2249':15.940337800013367,'2250':27.08972819999326},caller_shortened=sum(r['caller_shortened']for r in rows),seconds=time.perf_counter()-t,scope='SameAST/configuration/callerceilings doNOTprove identicalwalllimitedtrajectories; record depth/time/node exits and actual phaseceiling truncation. Gamecostincludeslogging; residual game-minusdecisioncost is NOTpurejournaloverhead. Prepaidreference cost302.26 is separate from reused1217.52gamecost; no free teacher. Reuse65paid/outcomes already exposed, no independentreplication, no control ofordinaryconcurrency or automaticreruns. CompletegridstillTRAIN-only; price-unqueriedinitialfamilies required for validation.')
 with(OUT/'resources.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
