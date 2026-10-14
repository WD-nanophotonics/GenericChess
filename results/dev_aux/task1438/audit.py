from pathlib import Path
import json,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1440';O.mkdir(exist_ok=False)
new=[json.loads(s) for s in (R/'results/dev_aux/task1439/games.jsonl').read_text().splitlines()];logical=[json.loads(s) for s in (R/'results/dev_aux/task1439/logical_games.jsonl').read_text().splitlines()];old=[json.loads(s) for s in (R/'results/dev_aux/task1405/games.jsonl').read_text().splitlines()]
names={x['game']:x for x in old};phys={x['game']:x for x in new};assert len(new)==56 and len(logical)==64 and len(phys)==56;derived=[]
def info(lines):
 out=[]
 for line in lines:
  fs=line.split()
  for key in ['time','nps']:
   if key in fs:i=fs.index(key);del fs[i:i+2]
  out.append(' '.join(fs))
 return out
for g in new:
 ref=names[g['game']]
 for field in ['root','arm','profile','nativeR','leafR','leafB','parameter_price','color','weights','actions','termination','label','final_fen']:assert g[field]==ref[field]
 assert len(g['queries'])==len(ref['queries'])
 for q,o in zip(g['queries'],ref['queries']):
  for field in ['ply','player','weights','native_weights','move']:assert q[field]==o[field]
  for field in ['root_fen5','root_fen8','full_history','command','backend']:assert q['metadata'][field]==o['metadata'][field]
  assert info(q['metadata']['uci_info'])==info(o['metadata']['uci_info'])
for l in logical:
 source=phys[l['source_game']];ref=names[l['game']];assert l['label']==ref['label'] and source['actions']==ref['actions'] and source['termination']==ref['termination'] and source['final_fen']==ref['final_fen']
 if l['derived']:
  assert l['color'] is True and source['color'] is False and source['weights']==source['queries'][0]['native_weights']==dict(P=1664,N=720,B=720,R=720,Q=1664,K=0) and source['opponent']=='unit_search'
  assert l['source_actions_sha256']==hashlib.sha256(json.dumps(source['actions'],sort_keys=True).encode()).hexdigest();derived.append(l)
 else:assert l['game']==l['source_game'] and l['color']==source['color']
assert len(derived)==8
expected_old=[names[l['game']] for l in logical];old_go=sum(len(g['queries']) for g in expected_old);new_go=sum(len(g['queries']) for g in new);saved=sum(len(names[l['game']]['queries']) for l in derived)
assert old_go-new_go==saved
result=json.loads((R/'results/dev_aux/task1439/result.json').read_bytes());assert result['complete'] and result['closed_games']==56 and result['logical_games']==64 and result['all_owned_engines_closed']
out=dict(status='PASS_ACTUAL_DEDUP_PHYSICAL_AND_LOGICAL_CONTROLS',actual_physical_games=56,logical_perspective_rows=64,derived_rows=8,old_physical_reference_games=64,old_go=old_go,actual_go=new_go,saved_go=saved,producer_seconds=result['seconds'],source_compression_only_identical_unit=True,scope='All56actual completeactions+allnon-time/nps UCIinfo matchold1405reference;8derivedperspectives exactoldseconddraw labels/trajectories. Originaldual64actual unchanged/notretroactively discounted. Random/nonuniformeach8rootsbothcolorsactual; no independentextra64sciencegames.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
