"""Existing finite semantic effects and reply/policy boundaries for availability."""
import argparse,hashlib,json,sys,time
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path('tests/product').resolve()));sys.path.insert(0,str(Path('tests').resolve()))
from test_qsearch_semantic_effects import transform_rules,noop_target_rules
from test_generic_pass_action import _compiled
from rule_semantics_ir_fixtures import uchifuzume_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.session import GameSession
from scripts.native_core_availability import NativeCoreAvailability
from scripts.full_q_refresh_comparison import runtime_state
from scripts.research_record import write_record
from generic_chess.native import semantic as ns

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);b=Path(ap.parse_args().output);b.mkdir(parents=True,exist_ok=True);assert not (b/'declaration.json').exists()
 write_record(b/'declaration.json',dict(question='Does readonly availability preserve Core on existing transformation/noop/quietterminal/pass/S4 fixtures, including maxply1 reply boundary?',decision='Mismatch rejects primitive consumer in that scope; unsupported compiled/provider scope and actual fallback retained. No quiet terminal/history shortcut.',cost='Five existing4x4 effect fixtures plus pass/S4 roots and legalchildren, expectedunder1min, no new generated cohort',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()))
 cases=[(k,compile_ruleset_for_execution(transform_rules(k))) for k in ('transform','nochange','balanced')]+[('terminal-nochange',compile_ruleset_for_execution(transform_rules('nochange',max_ply=1))),('enemy-target-noop',compile_ruleset_for_execution(noop_target_rules())),('pass',_compiled(True,True)[1]),('s4-reply',compile_ruleset_for_execution(uchifuzume_ruleset())),('s4-reply-maxply1',compile_ruleset_for_execution(replace(uchifuzume_ruleset(),max_ply=1)))]
 rows=[];start=time.perf_counter()
 for name,c in cases:
  s=GameSession(c);rt=SearchPathRuntime(s.state,c,history_witnesses=s._search_history_witnesses);root=runtime_state(rt);query=NativeCoreAvailability(c);engine=semantic_engine_for(c)
  def check(label):
   saved=runtime_state(rt);expected=engine.has_legal_action(rt.position);actual=query(rt);assert actual==expected,(name,label,expected,actual);assert runtime_state(rt)==saved
   rows.append(dict(case=name,label=label,available=actual,actual_imports=query.imports,queries=query.queries,fallbacks=query.fallbacks,provider=query.provider is not None))
  check('root')
  for i,action in enumerate(rt.legal_actions()):
   rt.push(action)
   try:check('child'+str(i))
   finally:rt.pop()
  rt.assert_balanced();assert runtime_state(rt)==root
 write_record(b/'result.json',dict(complete=True,rows=rows,seconds=time.perf_counter()-start));print('rows',len(rows),'fallbackcalls',sum(r['fallbacks']>0 for r in rows))
if __name__=='__main__':main()
