"""Independent three previously unobserved effect kinds, exact compiled-path witness."""
import ast,hashlib,importlib.util,json,sys,time
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleAuxState,RuleSquareRef,RuleTypeRef,RuleInvariant
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset,_king_type
from scripts.reserve_refresh_diagnostic import stopped
B=Path(__file__).parent
spec=importlib.util.spec_from_file_location('own_frozen_effect',B/'frozen_effect_probe.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
ref=lambda k,**kw:RuleSquareRef(k,**kw)
actor=PieceType('A','A',(LeapAtom((0,1)),))
target=PieceType('B','B',(LeapAtom((1,0)),))
board=[None]*16
board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K')
board[1]=Piece(0,'A','A');board[2]=Piece(0,'B','B')
effects=(RuleActionEffect('move',from_ref=ref('source'),to_ref=ref('target')),
 RuleActionEffect('shift',from_ref=ref('fixed',square=(2,0)),to_ref=ref('fixed',square=(2,1)),piece_owner='self'),
 RuleActionEffect('set_current_type',square_ref=ref('target'),type_ref=RuleTypeRef('explicit',type_id='B')),
 RuleActionEffect('set_bool',slot_name='temporary',value=1))
action=RuleSemanticAction(name='independent_compound',type_ids=('A',),geometry=RuleGeometrySpec(kind='leap',offset=(0,1)),target_relation='empty',composition='augment',effects=effects,
 aux_state=(RuleAuxState(name='temporary',value_kind='bool',scope='global',lifetime='expire_next_turn',initial=0),),
 invariants=(RuleInvariant('own_anchor_safe'),))
rules=_semantic_ruleset((_king_type(),actor,target),(action,),n=4,rows=tuple(tuple(board[i:i+4]) for i in range(0,16,4)))
compiled=compile_semantic_ruleset(rules)
out=dict(complete=False,baseline='b4108a68a7ee06327be39cb3a222939644085a52',prototype_sha256=hashlib.sha256((B/'frozen_effect_probe.py').read_bytes()).hexdigest(),scope='one new compound public DSL; two carriers; compiled execution witnessed; no timing or full-domain claim',rows=[])
start=time.monotonic()
for name,c in [('compat',compiled),('pure',CompiledSemanticRuleset(ir=compiled.ir,support=compiled.support))]:
 stopped();assert time.monotonic()-start<120
 engine=semantic_engine_for(c);pos=GameSession(c).state.position
 bindings=list(engine.iter_legal_action_bindings(pos))
 selected=[(a,b) for a,b in bindings if tuple(e.kind for e in b.pattern.effects)==tuple(e.kind for e in effects)]
 assert len(selected)==1,len(selected)
 a,b=selected[0];p.prepare(c)
 calls=[]
 for pid,(pattern,fn) in list(p.plans.items()):
  def wrapped(*args,_pid=pid,_fn=fn,**kw):
   calls.append(_pid);return _fn(*args,**kw)
  p.plans[pid]=(pattern,wrapped)
 counts=[];children=[]
 for fn in (p.baseline,p.candidate):
  seen=[]
  child=fn(engine,pos,a,b,lambda:seen.append(len(seen)+1))
  children.append(child);counts.append(len(seen))
 assert children[0]==children[1] and counts[0]==counts[1]
 assert calls==[b.pattern.pattern_id],calls
 child=children[0]
 assert child.board[1] is None and child.board[2] is None
 assert child.board[5].base_type_id=='A' and child.board[5].current_type_id=='B'
 assert child.board[6]==board[2] and child.side_to_move==1
 assert any(v==1 for k,v in child.aux_state)
 invalid=replace(pos,board=tuple(None if i==2 else v for i,v in enumerate(pos.board)))
 errors=[];invalid_counts=[]
 for fn in (p.baseline,p.candidate):
  seen=[]
  try:fn(engine,invalid,a,b,lambda:seen.append(len(seen)+1))
  except RuntimeError as exc:errors.append((type(exc).__name__,str(exc)));invalid_counts.append(len(seen))
  else:raise AssertionError('missing shift actor accepted')
 assert errors[0]==errors[1] and invalid_counts[0]==invalid_counts[1]
 fault_cells=0
 for stop in range(1,counts[0]+1):
  for fn in (p.baseline,p.candidate):
   fault=RuntimeError('one finite callback');seen=[]
   def checkpoint():
    seen.append(len(seen)+1)
    if len(seen)==stop:raise fault
   try:fn(engine,pos,a,b,checkpoint)
   except RuntimeError as exc:assert exc is fault and len(seen)==stop
   else:raise AssertionError('callback lost')
   assert pos.board==tuple(board);fault_cells+=1
 replies=list(engine.iter_legal_action_bindings(child));assert replies
 reply,rb=replies[0];before=len(calls)
 next_positions=[fn(engine,child,reply,rb) for fn in (p.baseline,p.candidate)]
 assert next_positions[0]==next_positions[1] and all(v==0 for k,v in next_positions[0].aux_state)
 assert len(calls)==before+1
 out['rows'].append(dict(carrier=name,effects=[e.kind for e in b.pattern.effects],valid_callbacks=counts,missing_actor_callbacks=invalid_counts,missing_actor_exception=errors[0],callback_fault_cells=fault_cells,compiled_function_calls=len(calls),compound_child=repr(child),reply_child=repr(next_positions[0]),parent_unchanged=True,compiled_path_witnessed=True,temporary_slot_expired=True))
out['complete']=True
(B/'effect_composition.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
