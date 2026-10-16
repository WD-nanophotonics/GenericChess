from pathlib import Path
import json,statistics
P=Path('.local_agent/alias-teacher-20261016');d=json.loads((P/'input-dependency-results.json').read_bytes());out=[]
for b in(4,8,12,16):
 rows=[r for r in d['rows']if r['board']==b];m=[m for r in rows for m in r['measurements']];out.append(dict(board=b,states=len(rows),observations=len(m),median_seconds={k:statistics.median(x[k]for x in m)for k in('pack_seconds','dynamic_seconds','dense_input_seconds')},allzero_vectors=sum(not any(r['dynamic_values'])for r in rows)))
print(json.dumps(out,indent=2));(P/'input-dependency-analysis.json').write_text(json.dumps(dict(rows=out,scope='Root/hashlegalchildcomponentcalls, notactualleafdistribution or optimizedsearch. Repeatedsamevectors only, notindependentCoretruth.'),indent=2)+'\n')
