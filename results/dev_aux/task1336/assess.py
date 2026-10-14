from pathlib import Path
import json
R=Path.cwd();O=R/'results/dev_aux/task1365';O.mkdir()
d=json.loads((R/'results/dev_aux/task1337/result.json').read_bytes());rows=[]
for row in d['rows']:
 rows.append(dict(seed=row['seed'],requested_actions=list(row['actions']),known_values=row['scores'],unknown_actions=sorted(set(row['actions'])-set(row['scores'])),status=row['status']))
out=dict(status='PARTIAL_H6_DIAGNOSTIC_ASSESSMENT',visited_nodes=d['nodes'],seconds=d['seconds'],rows=rows,error=d['error'],all_unvisited_root_seeds=[r['seed'] for r in json.loads((R/'results/dev_aux/task1325/roots.json').read_bytes())['roots'][3:6]],scope='9 completed selectedactionlabels in first2roots all0, thirdroot andlater unknown. 8m boundednodes cost502s, no decision-changing certifiedwin contrast. Do not extend or pad by H8/allchildren proofs; next effort on actual TRAIN/DEV generalization.',new_go=0)
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
