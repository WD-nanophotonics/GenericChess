"""Finite actual semantic-effect controls for readonly material summary."""
import argparse,json,sys
from dataclasses import replace
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path('tests/product').resolve()))
sys.path.insert(0,str(Path('tests').resolve()))
from test_qsearch_semantic_effects import transform_rules,noop_target_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.alphabeta.quiescence import material_inventory,enemy_board_count,noisy_child
from scripts.native_capsule_inventory import InventoryCapsulePathRuntime
from scripts.research_record import write_record,record_value

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);b=Path(ap.parse_args().output);b.mkdir(parents=True,exist_ok=True)
 if (b/'declaration.json').exists():raise RuntimeError('frozen output exists')
 cases=[(k,transform_rules(k)) for k in ('transform','nochange','balanced')]+[('terminal-nochange',transform_rules('nochange',max_ply=1)),('enemy-target-noop',noop_target_rules())]
 write_record(b/'declaration.json',{'question':'Can actual current-type inventory retain balanced transformation, no-op enemy target and quiet terminal support without trusting public promotion/capture metadata?','cases':[n for n,_ in cases],'decision':'Any supported count/inclusion mismatch rejects summary; compiler exclusions stay explicit. No frozen cohort/default changes.','cost':'Five existing 4x4 fixtures, one-ply legal children only; under1minute','scope':'Existing finite semantic effects; not all generated rules or complete noisy classification'})
 rows=[]
 for name,rules in cases:
  c=compile_ruleset_for_execution(rules);s=GameSession(c);core=SearchPathRuntime(s.state,c,history_witnesses=s._search_history_witnesses)
  try:rt=InventoryCapsulePathRuntime(s.state,c,s._search_history_witnesses)
  except (ValueError,RuntimeError,NotImplementedError) as e:
   rows.append({'case':name,'scope':'unsupported','error':repr(e)});continue
  root=rt.state;full=rt.full_snapshot();summary=rt.material_summary();side=root.position.side_to_move;enemies=enemy_board_count(root.position,side);inventory=material_inventory(root.position)
  assert set(rt.legal_actions())==set(core.legal_actions())
  for action in rt.legal_actions():
   rt.push(action);core.push(action)
   try:
    expected=noisy_child(action,core.state,side,enemies,inventory,lambda:core.in_check(core.position.side_to_move));views=rt.views;actual=rt.noisy_child(side,enemies,summary[3]);assert expected==actual and views==rt.views
    inv=material_inventory(core.position);assert rt.material_summary()[3]==tuple(inv.get((o,t),0) for o in (0,1) for t in rt.native.type_ids)
    assert rt.position==core.position and rt.ply_count==core.ply_count and rt.terminal_status==core.terminal_status
    rows.append({'case':name,'action':record_value(action),'noisy':actual,'terminal':core.terminal_status.is_terminal,'inventory_changed':inv!=inventory,'exact':True})
   finally:rt.pop();core.pop()
  assert rt.state==root and rt.full_snapshot()==full;rt.assert_balanced();core.assert_balanced()
 write_record(b/'result.json',{'complete':True,'rows':rows});print('cases',len(cases),'rows',len(rows),'unsupported',sum(x.get('scope')=='unsupported' for x in rows))
if __name__=='__main__':main()
