from pathlib import Path
import ast,json,hashlib,time
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2356')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class RemoveJournal(ast.NodeTransformer):
 def visit_Global(self,n):return None
 def visit_Assign(self,n):
  if any(isinstance(t,ast.Name)and t.id=='SNAPSHOT'for t in n.targets):return None
  return self.generic_visit(n)
 def visit_Expr(self,n):
  if isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Attribute)and isinstance(n.value.func.value,ast.Name)and n.value.func.value.id=='jf':return None
  return self.generic_visit(n)
 def visit_With(self,n):
  n.items=[x for x in n.items if not(isinstance(x.optional_vars,ast.Name)and x.optional_vars.id=='jf')];return self.generic_visit(n)
def policy(path,new=False):
 tree=ast.parse(Path(path).read_text(encoding='utf-8-sig'));n=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==('_run'if new else'run'));n.name='run';n=RemoveJournal().visit(n)if new else n;return ast.dump(n)
def run():
 stop=EvidenceStopReader(Path.cwd());stop();t=time.perf_counter();read=lambda n:json.loads(Path(n).read_text());old=read('results/dev_aux/task2325/plan.json');prior=read('results/dev_aux/task2340/plan.json');assert old['candidate']==prior['candidate']and old['H']==prior['H']and old['step_seconds']==prior['step_seconds']and old['candidate_proof_caller_seconds']==prior['candidate_proof_caller_seconds'];assert old['opponents'][0]==prior['opponents'][1]
 assert policy('results/dev_aux/task2340/pilot.py')==policy('results/dev_aux/task2325/pilot.py')==policy('results/dev_aux/task2354/pilot.py',True)
 assert read('results/dev_aux/task2326/task2325-audit.json')['status'].startswith('PASS')and read('results/dev_aux/task2343/task2340-audit.json')['status'].startswith('PASS')
 roots={r['index']:r for r in read(prior['input'])};r0={r['index']:r for r in read(old['input'])};assert roots.keys()==r0.keys()
 for index,r in roots.items():assert(r['rules'],r['record'],r['state_sha'])==(r0[index]['rules'],r0[index]['record'],r0[index]['state_sha'])
 entries=[];keys=set()
 for task in(2340,2325):
  plan=prior if task==2340 else old;gs=[json.loads(x)for x in Path(f'results/dev_aux/task{task}/games.jsonl').read_text().splitlines()]
  for g in gs:
   if task==2325 and g['ratio']!=2.:continue
   key=(g['root'],plan['opponents'][g['opponent']]['ratio'],g['candidate_color'],g['ratio']);assert key not in keys and g['reward']is not None and g['ending']=='ACTUAL_TERMINAL';keys.add(key);entries.append(dict(key=list(key),task=task,slot=g['slot'],game=g))
 assert len(entries)==65
 result=dict(status='PASS_POLICY_AST_CONTRACT_AND65_DISTINCT_REUSABLE_TERMINALS',entries=entries,reuse_count=65,source_counts={'2340':49,'2325':16},paid_game_seconds=sum(e['game']['seconds']for e in entries),seconds=time.perf_counter()-t,scope='SamefixedLOW12 policy after removing ONLY committed journal/global snapshots; actual normal/proof/search/commit tree AST identical. Existing independentlyreplayed49TRAIN+16old80price2/foe2 terminals, uniqueconfigurationkeys; no duplicateanchors/newqueries. Original2340partial stayspartial. Canonicalteacherexposed, TRAINoutcomesalreadyexposed; notblindselection/independentreplication. Stopfailclosed same, atomicclosure onlyinstrumentation; journalwalloverhead separatelyqualified.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='entries'}))
if __name__=='__main__':run()
