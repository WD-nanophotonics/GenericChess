"""Public multirow guarded-capture premise, distinct from builtin singleton result."""
import ast,hashlib,heapq,json,sys,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleTypeRef,RuleInvariant,RuleAuxState,RuleSlotGuard,RuleReplaceSelector
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset,_king_type
from scripts.reserve_refresh_diagnostic import stopped
import generic_chess.core.semantic_executor as m
ns=dict(vars(m));ns['heapq']=heapq
exec(compile((B.parent/'task033/candidate_function.py').read_text(encoding='utf-8'),'<frozen rank merge>','exec'),ns)
candidate=ns['is_square_attacked'];original=S.is_square_attacked;guard_original=S._guards_hold
A=PieceType('A','A',(LeapAtom((0,1)),));Btype=PieceType('B','B',(LeapAtom((1,0)),))
slot=RuleAuxState('permit','bool','global','persistent',0)
effects=(RuleActionEffect('remove',square_ref=RuleSquareRef('target'),piece_owner='opponent',piece_type_ref=RuleTypeRef('any'),disposition='remove_from_game'),RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')))
actions=[]
for i in range(6):
 actions.append(RuleSemanticAction(name='ordered_capture_'+str(i),type_ids=('A',),geometry=RuleGeometrySpec(kind='leap',offset=(0,1)),target_relation='enemy',
 composition='replace_legacy' if i==0 else 'augment',replace_selector=RuleReplaceSelector(('A',),'board','enemy','leap',True) if i==0 else None,
 aux_state=(slot,),slot_guards=(RuleSlotGuard('permit',value=0 if i<3 else 1),),effects=effects,invariants=(RuleInvariant('own_anchor_safe'),)))
board=[None]*16;board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K');board[1]=Piece(0,'A','A');board[5]=Piece(1,'B','B');board[14]=Piece(1,'A','A');board[10]=Piece(0,'B','B')
rules=_semantic_ruleset((_king_type(),A,Btype),tuple(actions),n=4,rows=tuple(tuple(board[i:i+4]) for i in range(0,16,4)))
compiled=compile_semantic_ruleset(rules)
rows=[];faults=[];started=time.monotonic();trace=None
def guards(self,*args,**kw):
 value=guard_original(self,*args,**kw)
 if trace is not None:trace.append(('guard',args[0].pattern_id,value))
 return value
def observe(fn,engine,pos,target,owner,stop=None):
 global trace
 trace=[];seen=0;fault=InterruptedError('one multirow callback');raised=False
 def checkpoint():
  nonlocal seen
  seen+=1;trace.append(('checkpoint',seen))
  if seen==stop:raise fault
 try:value=fn(engine,pos,target,owner,checkpoint=checkpoint)
 except InterruptedError as exc:assert exc is fault;raised=True;value=None
 result=value,seen,list(trace),raised;trace=None;return result
try:
 S._guards_hold=guards
 for carrier in ('compat','pure'):
  c=compiled if carrier=='compat' else CompiledSemanticRuleset(ir=compiled.ir,support=compiled.support);engine=S(c);root=GameSession(c).state.position
  sid=next(x.slot_id for x in c.ir.aux_slots if x.value_kind=='bool')
  for permit in (0,1):
   stopped();assert time.monotonic()-started<120
   pos=replace(root,aux_state=(((sid,-1),permit),));before=repr(pos)
   for owner in (0,1):
    for target in range(16):
     old=observe(original,engine,pos,target,owner);new=observe(candidate,engine,pos,target,owner)
     assert old==new and repr(pos)==before
     selected=[]
     for square,typed in c._incoming_attack_sources[(str(owner),target)].items():
      piece=pos.board[square]
      if piece is not None and piece.owner==owner:
       entries=typed.get(piece.current_type_id,())
       if entries:selected.append(entries)
     n=sum(map(len,selected));k=len(selected);consumed=sum(x[0]=='guard' for x in old[2])
     if target==(5 if owner==0 else 10):
      assert old[0] and n==6 and k==1 and consumed==(1 if permit==0 else 4)
      for stop in range(1,old[1]+1):
       a=observe(original,engine,pos,target,owner,stop);b=observe(candidate,engine,pos,target,owner,stop)
       assert a==b and a[3] and a[1]==stop and repr(pos)==before
      faults.append({'carrier':carrier,'permit':permit,'owner':owner,'target':target,'all_prefixes':old[1],'fault_arms':2*old[1]})
     rows.append({'carrier':carrier,'permit':permit,'owner':owner,'target':target,'result':old[0],'callbacks':old[1],
      'selected_rows':n,'selected_groups':k,'consumed_guard_rows':consumed,'exact_trace_sha256':hashlib.sha256(repr(old[2]).encode()).hexdigest(),'full_parent_unchanged':True})
finally:S._guards_hold=guard_original
out={'complete':True,'scope':'128pairs, public6conditional capture programs under current original compiler; compat/pure and slot0/1;8selected target cases all callback prefixes','rows':rows,'faults':faults,
 'changed_premise':'One actor contributes6ordered guard-bearing rows to one target; per-key rank ordering and full source polls retained. Distinct from builtin singleton inputs.',
 'decision':'Finite multirow structure/semantics established, not a useful caller workload or gain. Keep private and DEFER performance/deployment; do not transfer singleton negative to all generated rules or claim this handcrafted fixture covers generated domain.',
 'limits':'No C provider, search, wall deadline, allocation-failure or full generated-domain proof;120sec between-case guard only.'}
(B/'multirow_contract.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('public multirow128pairs pass; selected6rows1group consumes1/4; fault arms',sum(r['fault_arms'] for r in faults))
