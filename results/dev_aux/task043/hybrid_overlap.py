"""Declared legacy hybrid query witness, finite work, no caller timing."""
import hashlib,heapq,itertools,json,sys,time
from collections import Counter
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom,RayAtom
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset,_king_type
from scripts.reserve_refresh_diagnostic import stopped
from results.dev_aux.task046.iterator_counter import CountingHeap
proxy=CountingHeap()
import generic_chess.core.semantic_executor as m
ns=dict(vars(m));ns['heapq']=proxy
exec(compile((B.parent/'task033/candidate_function.py').read_text(),'<frozen merge>','exec'),ns)
candidate=ns['is_square_attacked'];original=S.is_square_attacked
saved=dict(binding=S._make_binding,path=S._path_holds,guard=S._guards_hold)
trace=None
def binding(self,*args,**kw):
 value=saved['binding'](self,*args,**kw)
 if trace is not None:trace.append(('binding',args[0].pattern_id,args[1],args[4],args[5],tuple(args[7])))
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
 proxy.reset();trace=[];seen=0;fault=InterruptedError('declared hybrid callback');raised=False
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
started=time.monotonic();records=[]
try:
 S._make_binding=binding;S._path_holds=path;S._guards_hold=guard
 for order,atoms in [('leap_ray',(LeapAtom((0,2)),RayAtom((0,1)))),('ray_leap',(RayAtom((0,1)),LeapAtom((0,2))))]:
  A=PieceType('A','A',atoms);BT=PieceType('B','B',(LeapAtom((1,0)),))
  board=[None]*16;board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K')
  board[5]=Piece(0,'A','A');board[13]=Piece(1,'B','B')
  c=compile_legacy_ruleset_for_semantic_execution(_semantic_ruleset((_king_type(),A,BT),(),n=4,rows=tuple(tuple(board[i:i+4]) for i in range(0,16,4))))
  for carrier in ('compat','pure'):
   compiled=c if carrier=='compat' else CompiledSemanticRuleset(ir=c.ir,support=c.support)
   engine=S(compiled);root=GameSession(compiled).state.position
   for blocked in (False,True):
    stopped();assert time.monotonic()-started<120
    cells=list(root.board);cells[9]=Piece(0,'B','B') if blocked else None
    pos=replace(root,board=tuple(cells));before=repr(pos)
    a=observe(original,engine,pos);b=observe(candidate,engine,pos)
    actual_merge=dict(proxy.last)
    assert a==b and a[0] and repr(pos)==before
    groups=[];details=[]
    for source,typed in compiled._incoming_attack_sources[('0',13)].items():
     piece=pos.board[source]
     if piece is not None and piece.owner==0:
      g=typed.get(piece.current_type_id,())
      groups.append([rank for rank,row in g])
      if g:
       details.extend(dict(rank=rank,pattern=row[0].pattern_id,source=row[2],
        geometry=row[3],kind=compiled.ir.geometry[row[3]].kind,path=list(row[4])) for rank,row in g)
    n=sum(map(len,groups));k=sum(bool(g) for g in groups)
    assert (n,k)==(2,1) and {x['kind'] for x in details}=={'ray','leap'}
    assert {tuple(x['path']) for x in details}=={(),(9,)}
    first=sorted(details,key=lambda x:x['rank'])[0]['kind']
    inspected=sum(x[0]=='binding' for x in a[2]);guards=sum(x[0]=='guard' for x in a[2])
    bad_paths=sum(x==('path',False) for x in a[2])
    expected=2 if blocked and first=='ray' else 1
    assert (inspected,guards,bad_paths)==(expected,1,expected-1)
    counts=Counter();prefix=list(itertools.islice(heapq.merge(*(Counted(g,counts) for g in groups)),inspected))
    later={rank:i+1<len(g) for g in groups for i,rank in enumerate(g)}
    predicted=k+sum(later[rank] for rank in prefix[:-1])
    assert counts['retrieved']==predicted==inspected
    assert actual_merge['group_lengths']==list(map(len,groups))
    assert actual_merge['reads']==predicted
    assert actual_merge['attempts']==len(groups)+inspected-1
    assert actual_merge['eof_attempts']==actual_merge['attempts']-predicted
    faults=[]
    for stop in range(1,a[1]+1):
     stopped();assert time.monotonic()-started<120
     fa=observe(original,engine,pos,stop);fb=observe(candidate,engine,pos,stop)
     assert fa==fb and fa[3] and fa[1]==stop and repr(pos)==before
     faults.append(dict(stop=stop,trace=fa[2],same_exception_object_each_arm=True))
    records.append(dict(order=order,carrier=carrier,blocked=blocked,
     selected_rows=n,groups=groups,rows=details,first_geometry=first,
     inspected_bindings=inspected,guard_evaluations=guards,blocked_paths=bad_paths,
     successful_iterator_reads=predicted,actual_merge_work=actual_merge,
     compiled_class=type(compiled).__name__,retained_legacy_handle=compiled._legacy_compiled is not None,normal_trace=a[2],faults=faults,
     full_parent_unchanged=True))
finally:
 S._make_binding=saved['binding'];S._path_holds=saved['path'];S._guards_hold=saved['guard']
out=dict(complete=True,product_base='b4108a68a7ee06327be39cb3a222939644085a52',
 iterator_counter_raw_sha256=hashlib.sha256((B.parent/'task046/iterator_counter.py').read_bytes()).hexdigest(),
 candidate_raw_sha256=hashlib.sha256((B.parent/'task033/candidate_function.py').read_bytes()).hexdigest(),
 records=records,normal_pairs=len(records),fault_pairs=sum(len(r['faults']) for r in records),
 decision='Actual public legacy hybrid retains n2/k1 duplicate endpoints with distinct path. Atom order/blocker changes inspected rows, not guards. Private merge finite agreement only; default singleton DEFER and caller cost remain unchanged.',
 limits='GameSession setup uses semantic checks. No search, Native, backend speed, deadlines, allocation failure, generated distribution or global equivalence claim.')
(B/'hybrid_overlap.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('hybrid normal',len(records),'fault pairs',out['fault_pairs'],'finite agreement; n2/k1')
