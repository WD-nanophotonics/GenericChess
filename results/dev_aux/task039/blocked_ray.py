"""Public blocked-ray witness for guard/prefix attribution, finite and non-time."""
import hashlib,heapq,itertools,json,sys,time
from collections import Counter
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleTypeRef,RuleInvariant,RuleAuxState,RuleSlotGuard,RuleReplaceSelector,RulePathConstraint
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset,_king_type
from scripts.reserve_refresh_diagnostic import stopped
import generic_chess.core.semantic_executor as m
ns=dict(vars(m));ns['heapq']=heapq
exec(compile((B.parent/'task033/candidate_function.py').read_text(),'<frozen private merge>','exec'),ns)
candidate=ns['is_square_attacked'];original=S.is_square_attacked
saved=dict(binding=S._make_binding,path=S._path_holds,guard=S._guards_hold)
A=PieceType('A','A',(RayAtom((0,1)),));BT=PieceType('B','B',(LeapAtom((1,0)),))
slot=RuleAuxState('permit','bool','global','persistent',0)
effects=(RuleActionEffect('remove',square_ref=RuleSquareRef('target'),piece_owner='opponent',piece_type_ref=RuleTypeRef('any'),disposition='remove_from_game'),RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')))
actions=tuple(RuleSemanticAction(name='ray_capture_'+str(i),type_ids=('A',),
 geometry=RuleGeometrySpec(kind='ray',direction=(0,1)),target_relation='enemy',
 composition='replace_legacy' if i==0 else 'augment',
 replace_selector=RuleReplaceSelector(('A',),'board','enemy','ray',True) if i==0 else None,
 path_constraints=(RulePathConstraint('path_clear'),),aux_state=(slot,),
 slot_guards=(RuleSlotGuard('permit',value=0 if i<3 else 1),),effects=effects,
 invariants=(RuleInvariant('own_anchor_safe'),)) for i in range(6))
board=[None]*16;board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K')
board[5]=Piece(0,'A','A');board[9]=Piece(0,'A','A');board[13]=Piece(1,'B','B')
c=compile_semantic_ruleset(_semantic_ruleset((_king_type(),A,BT),actions,n=4,rows=tuple(tuple(board[i:i+4]) for i in range(0,16,4))))
trace=None
def binding(self,*args,**kw):
 value=saved['binding'](self,*args,**kw)
 if trace is not None:trace.append(('binding',args[0].pattern_id,args[4],args[5],tuple(args[7])))
 return value
def path(self,*args,**kw):
 value=saved['path'](self,*args,**kw)
 if trace is not None:trace.append(('path',value))
 return value
def guard(self,*args,**kw):
 value=saved['guard'](self,*args,**kw)
 if trace is not None:trace.append(('guard',value))
 return value
def observe(fn,engine,pos,stop=None):
 global trace
 trace=[];seen=0;fault=InterruptedError('one blocked-path checkpoint');raised=False
 def checkpoint():
  nonlocal seen
  seen+=1;trace.append(('checkpoint',seen))
  if seen==stop:raise fault
 try:value=fn(engine,pos,13,0,checkpoint=checkpoint)
 except InterruptedError as exc:assert exc is fault;raised=True;value=None
 result=value,seen,list(trace),raised;trace=None;return result
class Counted:
 def __init__(self,g,counts):self.it=iter(g);self.counts=counts
 def __iter__(self):return self
 def __next__(self):
  x=next(self.it);self.counts['retrieved']+=1;return x
started=time.monotonic();rows=[]
try:
 S._make_binding=binding;S._path_holds=path;S._guards_hold=guard
 for carrier in ('compat','pure'):
  compiled=c if carrier=='compat' else CompiledSemanticRuleset(ir=c.ir,support=c.support)
  engine=S(compiled);root=GameSession(compiled).state.position
  sid=next(x.slot_id for x in compiled.ir.aux_slots if x.value_kind=='bool')
  for permit in (0,1):
   stopped();assert time.monotonic()-started<120
   pos=replace(root,aux_state=(((sid,-1),permit),));before=repr(pos)
   a=observe(original,engine,pos);b=observe(candidate,engine,pos)
   assert a==b and a[0] and repr(pos)==before
   groups=[]
   for source,typed in compiled._incoming_attack_sources[('0',13)].items():
    piece=pos.board[source]
    if piece is not None and piece.owner==0:
     g=typed.get(piece.current_type_id,())
     if g:groups.append([rank for rank,row in g])
   n=sum(map(len,groups));k=len(groups);p=sum(x[0]=='binding' for x in a[2]);guards=sum(x[0]=='guard' for x in a[2])
   blocked=sum(x==('path',False) for x in a[2])
   assert (n,k,p,guards,blocked)==(12,2,2 if permit==0 else 8,1 if permit==0 else 4,1 if permit==0 else 4)
   counts=Counter();prefix=list(itertools.islice(heapq.merge(*(Counted(g,counts) for g in groups)),p))
   later={rank:i+1<len(g) for g in groups for i,rank in enumerate(g)}
   expected=k+sum(later[rank] for rank in prefix[:-1])
   assert counts['retrieved']==expected==(3 if permit==0 else 9)
   # Last checkpoint before first blocked-path return lies within that path.
   end=next(i for i,x in enumerate(a[2]) if x==('path',False))
   stop=next(x[1] for x in reversed(a[2][:end]) if x[0]=='checkpoint')
   fa=observe(original,engine,pos,stop);fb=observe(candidate,engine,pos,stop)
   assert fa==fb and fa[3] and fa[1]==stop and repr(pos)==before
   rows.append(dict(carrier=carrier,permit=permit,selected_rows=n,groups=groups,
    inspected_rows=p,guards=guards,blocked_path_rows=blocked,structural_retrieved=expected,
    exact_trace=a[2],fault_checkpoint=stop,exact_fault_trace=fa[2],full_parent_unchanged=True))
finally:
 S._make_binding=saved['binding'];S._path_holds=saved['path'];S._guards_hold=saved['guard']
out=dict(complete=True,scope='4fixed public blocked-ray query pairs;8exact path-checkpoint fault arms;numeric iterator work on retained actual rank groups',
 candidate_raw_sha256=hashlib.sha256((B.parent/'task033/candidate_function.py').read_bytes()).hexdigest(),
 rows=rows,decision='Record inspected bindings separately from guards and preserve group rank layout. Supported two-source path blocking makes guards1/4 differ from prefix2/8 and retrieves3/9 of12 selected rows. No caller usefulness or deployment follows.',
 limits='No search, C provider, wall-time, allocation failure or whole generated-domain proof. GameSession initialization invokes ordinary semantic checks; only target13 owner0 is independently paired here.')
(B/'blocked_ray.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('blocked-ray4pairs/8fault arms pass; guards1/4 vs inspected2/8; retrieved3/9 of12')
