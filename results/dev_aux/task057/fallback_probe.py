"""Validate captured primary provider draft in an isolated auxiliary process."""
import hashlib,json,sys
from pathlib import Path
from dataclasses import replace
B=Path(__file__).parent
E={'__file__':str(B/'probe.py')};exec((B/'probe.py').read_text(encoding='utf-8').split("out={'complete':False")[0],E)
from generic_chess.ai.alphabeta import native_legality as nl
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from test_f24c_mixed_mechanic_certification_r1 import _state
from generic_chess.rules.schema import RuleTypeRef
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for,_semantic_public_action
from generic_chess.rules.compiler import compile_semantic_ruleset
from test_f24c_mixed_mechanic_certification import _mixed_ruleset,_position
from scripts.research_record import record_value
D=json.loads((B/'fallback-declaration.json').read_bytes());snippet=(B/'provider_try_create.py').read_bytes()
assert hashlib.sha256(snippet).hexdigest()==D['function_ast_sha256']
ns=dict(nl.__dict__);exec(compile(snippet,'<captured primary try_create>','exec'),ns)
support=(B/'provider_supports_position.py').read_bytes();assert hashlib.sha256(support).hexdigest()==D['supports_position_ast_sha256'];exec(compile(support,'<captured primary supports_position>','exec'),ns)
original_support=nl.NativeSemanticLegalityProvider.supports_position;nl.NativeSemanticLegalityProvider.supports_position=ns['supports_position']
original=nl.NativeSemanticLegalityProvider.__dict__['try_create'];nl.NativeSemanticLegalityProvider.try_create=ns['try_create']
old=json.loads((B/'result.json').read_bytes());out={'complete':False,'declaration':D,'rows':[],'scope':D['scope']}
try:
 for r in old['rows']:
  case=r['case'];ref=RuleTypeRef('explicit',case[9:]) if case.startswith('explicit_') else RuleTypeRef(case)
  rules=_mixed_ruleset();rules=replace(rules,semantic_actions=tuple(replace(a,effects=tuple(replace(e,piece_type_ref=ref) if e.kind=='remove' else e for e in a.effects)) if a.name=='capture_B0_A0_leap' else a for a in rules.semantic_actions));c=compile_semantic_ruleset(rules)
  pos=_position(c,[(1,1,Piece(0,'B0','B0')),(2,1,Piece(1,'A0','A0')),(0,0,Piece(0,'H0','H0')),(6,6,Piece(1,'H0','H0'))]);state=_state(c,pos)
  assert c.ruleset_fingerprint==r['ruleset_fingerprint']
  provider=nl.NativeSemanticLegalityProvider.try_create(c,strict=True);rt=SearchPathRuntime.from_state(state,c,history_witnesses=(pos,),legal_binding_provider=provider);stats=SearchStatistics();rt.attach_stats(stats)
  before=(rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),rt._history_context)
  actual=set(rt.legal_actions());engine=semantic_engine_for(c);core={_semantic_public_action(engine,a) for a in engine.legal_actions(pos)}
  assert actual==core and len(actual)==r['core_count'];rt.assert_balanced();assert before==(rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),rt._history_context)
  affected=case in ['action_base','action_current'];assert (provider is None)==affected
  assert stats.native_legality_fallbacks==stats.native_legality_operational_failures==0
  assert bool(stats.native_legality_calls)==bool(provider)
  assert bool(stats.native_legality_enabled)==bool(provider)
  out['rows'].append({'case':case,'ruleset_fingerprint':c.ruleset_fingerprint,'native_requested':True,'provider_created':provider is not None,'actual_route':'Core capability refusal' if affected else 'Native legality with Core execution','actual_legal_count':len(actual),'full_frontier_matches_core':True,'native_enabled':stats.native_legality_enabled,'native_calls':stats.native_legality_calls,'native_fallback_counter':stats.native_legality_fallbacks,'native_operational_failures':stats.native_legality_operational_failures,'root_restored':True,'actions':record_value(sorted(actual,key=str))})
 out['complete']=True;(B/'fallback-result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps([{k:r[k] for k in r if k!='actions'} for r in out['rows']]))
finally:
 nl.NativeSemanticLegalityProvider.supports_position=original_support;nl.NativeSemanticLegalityProvider.try_create=original;E['nc']._sem_effect=E['original']
