"""Distinct deferred aux-square operands in shared code, no timing."""
import hashlib,importlib.util,json,sys,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleAuxState,RuleInvariant
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset,_king_type
from scripts.reserve_refresh_diagnostic import stopped
spec=importlib.util.spec_from_file_location('own_immutable_shared',B.parent/'task025/compiled_effect_shared.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
A=PieceType('A','A',(LeapAtom((0,1)),))
board=[None]*16;board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K');board[5]=Piece(0,'A','A')
rows=[];started=time.monotonic()
for scope in ('global','per_owner'):
 slots=tuple(RuleAuxState(name,'square_or_none',scope,'expire_next_turn',None) for name in ('source_token','output_token'))
 actions=tuple(RuleSemanticAction(name=label,type_ids=('A',),geometry=RuleGeometrySpec(kind='leap',offset=(0,1)),target_relation='empty',composition='augment',aux_state=slots,
  effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),RuleActionEffect('set_token',slot_name='output_token',square_ref=ref)),
  invariants=(RuleInvariant('own_anchor_safe'),)) for label,ref in [('source_square',RuleSquareRef('source')),('pre_expiry_token',RuleSquareRef('aux_slot_square',slot_name='source_token'))])
 c=compile_semantic_ruleset(_semantic_ruleset((_king_type(),A),actions,n=4,rows=tuple(tuple(board[i:i+4]) for i in range(0,16,4))))
 for carrier in ('compat','pure'):
  stopped();assert time.monotonic()-started<120
  compiled=c if carrier=='compat' else CompiledSemanticRuleset(ir=c.ir,support=c.support)
  engine=semantic_engine_for(compiled);root=GameSession(compiled).state.position
  ids={name:i for i,name in enumerate(sorted(slot.name for slot in slots))};owner=-1 if scope=='global' else 0
  aux=dict(root.aux_state);aux[(ids['source_token'],owner)]=(2,2);aux[(ids['output_token'],owner)]=(3,1)
  if scope=='per_owner':
   aux[(ids['source_token'],1)]=(3,0);aux[(ids['output_token'],1)]=(2,0)
  pos=replace(root,aux_state=tuple(sorted(aux.items())));before=repr(pos)
  selected=[(a,b) for a,b in engine.iter_legal_action_bindings(pos) if b.pattern.name in ('source_square','pre_expiry_token')]
  assert len(selected)==2;p.prepare(compiled)
  assert p.plans[selected[0][1].pattern.pattern_id][1] is p.plans[selected[1][1].pattern.pattern_id][1]
  hits=[]
  for pid,(pattern,fn) in list(p.plans.items()):
   def wrapped(*args,_pid=pid,_fn=fn,**kw):hits.append(_pid);return _fn(*args,**kw)
   p.plans[pid]=(pattern,wrapped)
  for action,binding in selected:
   cases=['normal','missing_pre_token'] if binding.pattern.name=='pre_expiry_token' else ['normal']
   for case in cases:
    current=pos
    if case!='normal':
     missing=dict(pos.aux_state);missing[(ids['source_token'],owner)]=None
     current=replace(pos,aux_state=tuple(sorted(missing.items())))
    parent=repr(current);results=[];callbacks=[]
    for fn in (p.baseline,p.candidate):
     events=[];prior=len(hits)
     try:
      child=fn(engine,current,action,binding,lambda:events.append(len(events)+1))
      result={'status':'child','child':repr(child),'aux':repr(child.aux_state)}
      values=dict(child.aux_state)
      assert child.board[5] is None and child.board[9]==board[5]
      assert values[(ids['source_token'],owner)] is None
      assert values[(ids['output_token'],owner)]==((1,1) if binding.pattern.name=='source_square' else (2,2))
      if scope=='per_owner':assert values[(ids['source_token'],1)] is None and values[(ids['output_token'],1)] is None
     except RuntimeError as exc:
      result={'status':'rejection','exception_type':type(exc).__name__,'message':str(exc)}
     assert repr(current)==parent
     if fn is p.candidate:assert hits[prior:]==[binding.pattern.pattern_id]
     results.append(result);callbacks.append(events)
    assert results[0]==results[1] and callbacks[0]==callbacks[1]
    assert results[0]['status']==('child' if case=='normal' else 'rejection')
    rows.append(dict(scope=scope,carrier=carrier,action=binding.pattern.name,case=case,
     result=results[0],callbacks=callbacks[0],shared_function_identity=True,
     actual_compiled_hit=binding.pattern.pattern_id,full_parent_unchanged=True))
  assert repr(pos)==before
out=dict(complete=True,scope='8normal+4direct missing-token pairs under2scope/2carrier public fixtures',
 shared_source_sha256=hashlib.sha256((B.parent/'task025/compiled_effect_shared.py').read_bytes()).hexdigest(),
 rows=rows,decision='Finite shared-template operands retain pre-action square lookup and global/per-owner expiry. Private prototype remains DEFER for cost; no full-domain or legal-membership claim for negative direct calls.',
 limits='Public initial-state/legality setup invokes semantic checks. No search,C-provider,timing,allocation-failure or all callback-prefix sweep.')
(B/'deferred_square.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('deferred square12pairs pass:8normal4direct negative; pre-action lookup and both expiry scopes; shared hits')
