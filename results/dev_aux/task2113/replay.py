"""Source-only consumers write NEW reports, never overwrite frozen receipts."""
from pathlib import Path
import importlib,json,time
OUT=Path('.replay_output/71')
def call(name,folder,run_kwargs=None,**overrides):
 m=importlib.import_module(name);target=OUT/folder;target.mkdir(parents=True,exist_ok=False);m.OUT=target
 for key,value in overrides.items():setattr(m,key,value)
 (getattr(m,'run',None)or m.main)(**(run_kwargs or {}));assert 'generic_chess.learning.alphasho_bridge'not in __import__('sys').modules;return target

def verify_entries():
 from generic_chess.rules.serialization import deserialize_ruleset
 from generic_chess.rules.compiler import compile_ruleset_for_execution
 from generic_chess.session.session import GameSession
 from generic_chess.session.serialization import deserialize_game_record
 rows=json.loads(Path('results/dev_aux/task2106/first-entries.json').read_text(encoding='utf-8'));roots=json.loads(Path('results/dev_aux/task2105/inputs.json').read_text(encoding='utf-8'))['roots'];games={g['physical_id']:g for g in(json.loads(x)for x in Path('results/dev_aux/task2105/games.jsonl').read_text(encoding='utf-8').splitlines())if g['reused_from']is None};compiled={};entered=0
 for row in rows:
  g=games[row['physical_id']];entry=row['entry']
  if not entry['entered']:continue
  if row['family']not in compiled:compiled[row['family']]=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[row['family']]['rules']).read_text(encoding='utf-8')))
  c=compiled[row['family']];record=deserialize_game_record(json.dumps(entry['full_record']));full=deserialize_game_record(json.dumps(g['record']));assert record.actions==full.actions[:entry['entry_ply']];s=GameSession.replay(c,record);assert sum(p is not None for p in s.state.position.board)<=4 and entry['remaining_rule_plies']==96-s.state.ply_count and entry['side']==s.state.position.side_to_move;entered+=1
 assert len(rows)==368 and entered==362
 return dict(status='PASS_ALL_FIRST_ENTRY_RECORDS',physical_denominator=len(rows),entered=entered,nonentered=6,newpolicy_queries=0)

def run():
 start=time.perf_counter();OUT.mkdir(parents=True,exist_ok=False);reports=[]
 for name,folder in [('results.dev_aux.task2112.input_replay','inputs'),('results.dev_aux.task2090.audit','certificates'),('results.dev_aux.task2095.audit','3x3'),('results.dev_aux.task2099.audit','5piece'),('results.dev_aux.task2103.audit','model'),('results.dev_aux.task2107.audit','prices')]:
  reports.append(str(call(name,folder,run_kwargs={'publication_projection':'results/dev_aux/task2115/projection.json'}if folder in('model','prices')else{})))
 from results.dev_aux.task2108 import derive
 derive.CEN=OUT/'view-census';derive.LAB=OUT/'view-labels';derive.CEN.mkdir();derive.LAB.mkdir();derive.main()
 va=call('results.dev_aux.task2110.audit','view-audit',ROOT=derive.CEN,LAB=derive.LAB)
 from results.dev_aux.task2111 import view_check
 view_check.OUT=OUT/'view-interface';view_check.OUT.mkdir();view_check.run(str(derive.CEN),str(derive.LAB),str(va))
 entries=verify_entries();result=dict(status='PASS_SOURCE_ONLY_CLOSED_STUDIES',reports=reports,derived_view_states=244080,entries=entries,seconds=time.perf_counter()-start,scope='ONEunusedbridgepublicationpathprojectionexplicitlychecked/reported; nofulloriginalbyteidentityclaim. Existingfixedteacher/source/record/certificateconsumers; noNative/census/train/policycampaign ornewcounterfactuals. SamehostPython/OSnotbundled. UnitpytestseparateincludesboundedPythonPNandrankqueries, notfrozenfitnessreruns. Active2100partial notinsidethisclosedcapsule; separatePN_PARTIALreceiptlater.')
 (OUT/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
