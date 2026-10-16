"""Audit sixteen repeated old80 anchor configurations; not new independent evidence."""
from pathlib import Path
import json,time,hashlib,ast
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2348')
def run():
 t=time.perf_counter();stop=EvidenceStopReader(Path.cwd());read=lambda p:json.loads(Path(p).read_text());old=read('results/dev_aux/task2325/plan.json');new=read('results/dev_aux/task2340/plan.json');assert old['candidate']==new['candidate']and old['H']==new['H']and old['step_seconds']==new['step_seconds']and old['candidate_proof_caller_seconds']==new['candidate_proof_caller_seconds'];assert old['opponents'][0]==new['opponents'][1]
 def policy_ast(path):
  tree=ast.parse(Path(path).read_text());tree.body=[n for n in tree.body if not(isinstance(n,ast.Assign)and any(isinstance(x,ast.Name)and x.id=='OUT'for x in n.targets))];return ast.dump(tree)
 assert policy_ast('results/dev_aux/task2325/pilot.py')==policy_ast('results/dev_aux/task2340/pilot.py')
 a={g['slot']:g for g in map(json.loads,Path('results/dev_aux/task2325/games.jsonl').read_text().splitlines())};b=list(map(json.loads,Path('results/dev_aux/task2340/games.jsonl').read_text().splitlines()));oldroots={r['index']:r for r in read(old['input'])};newroots={r['index']:r for r in read(new['input'])};matches=[]
 for g in b:
  stop()
  if g['ratio']!=1. or g['opponent']!=1:continue
  prior=next(x for x in a.values()if x['root']==g['root']and x['candidate_color']==g['candidate_color']and x['ratio']==1.);r=oldroots[g['root']];q=newroots[g['root']];assert r['rules']==q['rules']and r['record']==q['record']and r['state_sha']==q['state_sha'];matches.append(dict(slot=g['slot'],old_slot=prior['slot'],root=g['root'],color=g['candidate_color'],outcomes=[prior['outcome'],g['outcome']],records_identical=prior['record']==g['record'],reward_identical=prior['reward']==g['reward'],repeated_seconds=g['seconds']))
 result=dict(status='AUDITED_REPEATED_BASELINE_ANCHOR_CONFIGURATIONS',expected_repeated=16,executed_repeated=len(matches),records_identical=sum(x['records_identical']for x in matches),rewards_identical=sum(x['reward_identical']for x in matches),repeated_seconds=sum(x['repeated_seconds']for x in matches),rows=matches,seconds=time.perf_counter()-t,scope='These16baseline1/foe2/oldTRAIN configurations couldhavebeenreusedaftercompatibilityaudit; thiscomplete96slotTRAINsweep repeatedthem. Treat asrepeatedanchors/costnotnewindependentfamilies. No removalofstartedfrozenrows, capchange orloadtriggeredrerun. Compareactualrecords/outcomes; matchingconfigurationdoesnotguaranteewalllimitedpaths. Old80dataNOTpooledtwiceintonewTRAINselection.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='rows'}))
if __name__=='__main__':run()
