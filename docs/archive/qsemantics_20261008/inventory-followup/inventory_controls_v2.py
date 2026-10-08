"""Local limited signal prototype; neither deployed nor complete tactics."""
import sys,json,time,hashlib,types
from pathlib import Path
from collections import Counter
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from scripts.research_record import write_record
p=Path(__file__).parent;out=p/'inventory-controls-v2.json';assert not out.exists()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def inventory(position):
    values=Counter((x.owner,x.current_type_id) for x in position.board if x is not None)
    for owner,hand in enumerate(position.hands):
        for tid,count in hand.items():values[(owner,tid)]+=count
    return values
qsource=(root/'generic_chess/ai/alphabeta/quiescence.py').read_text()
qsource=qsource.replace('parent_enemies = enemy_board_count(state.position, side)','parent_enemies = enemy_board_count(state.position, side)\n    parent_inventory = inventory(state.position)')
qsource=qsource.replace('if action_promotion_target_id(action) is not None:','if semantic_engine is None and action_promotion_target_id(action) is not None:')
qsource=qsource.replace('    for action, child in successors:\n','    for action, child in successors:\n        if inventory(child.position) != parent_inventory:\n            noisy.append(action)\n            continue\n')
q=types.ModuleType('generic_chess.ai.alphabeta.inventory_qpilot');q.__package__='generic_chess.ai.alphabeta';q.inventory=inventory;exec(qsource,q.__dict__)
ssource=(root/'generic_chess/ai/alphabeta/search.py').read_text()
ssource=ssource.replace('parent_enemies = enemy_board_count(state.position, side)','parent_enemies = enemy_board_count(state.position, side)\n    parent_inventory = inventory(state.position)')
needle='if action_promotion_target_id(action) is not None:'
assert ssource.count(needle)==1
ssource=ssource.replace(needle,'if semantic_engine_for(ctx.compiled) is None and action_promotion_target_id(action) is not None:')
needle='            child = runtime.state\n            if enemy_board_count(child.position, side) < parent_enemies:'
assert needle in ssource
ssource=ssource.replace(needle,'            child = runtime.state\n            if inventory(child.position) != parent_inventory:\n                noisy.append(action)\n                continue\n            if enemy_board_count(child.position, side) < parent_enemies:')
s=types.ModuleType('generic_chess.ai.alphabeta.inventory_spilot');s.__package__='generic_chess.ai.alphabeta';sys.modules[s.__name__]=s;s.inventory=inventory;exec(ssource,s.__dict__);s.classify_noisy=q.classify_noisy
r={'complete':False,'producer_sha256':sha(Path(__file__)),'declaration':'Fixed three recorded4x4 witnesses, all variants/mutable modes, q1/hard8. Local actual owner/current board+owner/base hand count signal replaces unconditional semantic promotion shortcut; legacy shortcut retained. Parent inventory snapshotted before push. Expected transform both1726; no-change both1726 with equal support; balanced count-conserving transform deliberately not detected, both2000. No deployed change, full classifier, timing claim, or capture-only option claim. Subsequent cost/normaldrop/pass/terminal controls required before any product proposal. <=30sec/4096nodes per call.','inputs':{},'cases':[]}
started=time.perf_counter();write_record(out,r)
try:
 for name in ('promotion-encoding','promotion-nochange-v4','promotion-balanced'):
  f=p/(name+'.json');r['inputs'][f.relative_to(root).as_posix()]=sha(f);d=json.loads(f.read_bytes())
  for v in d['variants']:
   c=compile_ruleset_for_execution(ruleset_from_dict(v['rules']));state=GameSession(c).state
   cfg=EvaluationConfig(dynamic_mobility_weight=0,anchor_escape_weight=0,promotion_potential_weight=0);ev=Evaluator(c,build_ruleset_profile(c,cfg),cfg)
   row={'witness':name,'variant':v['label'],'calls':[]};r['cases'].append(row)
   for mutable in (False,True):
    assert time.perf_counter()-started<30
    limits=SearchLimits(max_nodes=4096,max_time_seconds=5,quiescence_max_depth=1,quiescence_hard_max_depth=8)
    stats=SearchStatistics();ctx=s._Context(c,ev,TranspositionTable(),stats,s._Budget(limits,None),SearchTuning(),True,True,1,8,None,runtime=SearchPathRuntime(state,c) if mutable else None)
    value=s.quiescence(state,-s.INF,s.INF,0,0,ctx)
    row['calls'].append({'mutable':mutable,'value':value,'qnodes':stats.qnodes})
    if mutable:ctx.runtime.assert_balanced()
   write_record(out,r)
 for name in ('promotion-encoding','promotion-nochange-v4','promotion-balanced'):
  calls=[x['calls'] for x in r['cases'] if x['witness']==name]
  assert all(x[0]['value']==x[1]['value'] and x[0]['qnodes']==x[1]['qnodes'] for x in calls)
  assert len({x[0]['value'] for x in calls})==1
  assert calls[0]==calls[1]  # distinct rulesets; combined retains duplicate public actions
 from ai_fixtures import build_4x4_rooks
 from conftest import make_state
 from generic_chess.core.actions import action_is_drop,PassAction
 from generic_chess.core.transition import legal_successors
 sys.path.insert(0,str(root/'tests/product'))
 from test_generic_pass_action import _compiled
 r['controls']=[]
 c=build_4x4_rooks();state=make_state(c,['....','....','....','K.k.'],hands=([('R',1)],()))
 for action,child in legal_successors(state,c):
  if not action_is_drop(action):continue
  assert inventory(state.position)==inventory(child.position)
  runtime=SearchPathRuntime(state,c);parent=inventory(runtime.position)
  with runtime.pushed(action):assert parent==inventory(runtime.position)
  runtime.assert_balanced()
  r['controls'].append({'kind':'ordinary_Rdrop','inventory_unchanged':True})
 for semantic in (False,True):
  _,c=_compiled(semantic,True);state=GameSession(c).state
  for action,child in legal_successors(state,c):
   if isinstance(action,PassAction):
    assert inventory(state.position)==inventory(child.position)
    runtime=SearchPathRuntime(state,c);parent=inventory(runtime.position)
    with runtime.pushed(action):assert parent==inventory(runtime.position)
    runtime.assert_balanced()
    r['controls'].append({'kind':'pass','semantic':semantic,'inventory_unchanged':True})
 assert len([x for x in r['controls'] if x['kind']=='pass'])==2
 r['complete']=True
finally:r['seconds']=time.perf_counter()-started;write_record(out,r)
print([(x['witness'],x['variant'],x['calls']) for x in r['cases']])
