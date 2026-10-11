"""Public explicit current-type child dispatch witness, no-time."""
import hashlib,heapq,json,sys,time
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSemanticAction,RuleGeometrySpec,RuleActionEffect,RuleSquareRef,RuleTypeRef,RuleInvariant
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.session.session import GameSession
from rule_semantics_ir_fixtures import _semantic_ruleset,_king_type
from scripts.reserve_refresh_diagnostic import stopped
from results.dev_aux.task046.iterator_counter import CountingHeap
proxy=CountingHeap()
import generic_chess.core.semantic_executor as m
source=(B.parent/'task033/candidate_function.py').read_text()
ns=dict(vars(m));ns['heapq']=proxy;exec(compile(source,'<frozen private merge>','exec'),ns)
candidate=ns['is_square_attacked'];original=S.is_square_attacked
badns=dict(vars(m));badns['heapq']=heapq
badsource=source.replace('typed.get(piece.current_type_id, ())','typed.get(piece.base_type_id, ())')
assert badsource!=source
exec(compile(badsource,'<deliberately wrong base selector>','exec'),badns)
bad=badns['is_square_attacked']
saved=dict(binding=S._make_binding,path=S._path_holds,guard=S._guards_hold);trace=None
def binding(self,*args,**kw):
 value=saved['binding'](self,*args,**kw)
 if trace is not None:trace.append(('binding',args[0].pattern_id,args[1],args[2],args[4],args[5],tuple(args[7])))
 return value
def path(self,*args,**kw):
 value=saved['path'](self,*args,**kw)
 if trace is not None:trace.append(('path',value))
 return value
def guard(self,*args,**kw):
 value=saved['guard'](self,*args,**kw)
 if trace is not None:trace.append(('guard',value))
 return value
def observe(fn,engine,pos,target,stop=None):
 global trace
 proxy.reset();trace=[];seen=0;fault=InterruptedError('public current-type checkpoint');raised=False
 def checkpoint():
  nonlocal seen
  seen+=1;trace.append(('checkpoint',seen))
  if seen==stop:raise fault
 try:value=fn(engine,pos,target,0,checkpoint=checkpoint)
 except InterruptedError as exc:assert exc is fault;raised=True;value=None
 result=value,seen,list(trace),raised;trace=None;return result
A=PieceType('A','A',(LeapAtom((0,1)),));BT=PieceType('B','B',(LeapAtom((1,0)),));C=PieceType('C','C',(LeapAtom((1,0)),))
board=[None]*16;board[0]=Piece(0,'K','K');board[15]=Piece(1,'K','K')
board[5]=Piece(0,'A','A');board[10]=Piece(1,'C','C');board[13]=Piece(1,'C','C')
action=RuleSemanticAction(name='change_type',type_ids=('A',),geometry=RuleGeometrySpec(kind='leap',offset=(0,1)),
 target_relation='empty',composition='augment',
 effects=(RuleActionEffect('move',from_ref=RuleSquareRef('source'),to_ref=RuleSquareRef('target')),
 RuleActionEffect('set_current_type',square_ref=RuleSquareRef('target'),type_ref=RuleTypeRef('explicit','B'))),
 invariants=(RuleInvariant('own_anchor_safe'),))
compiled=compile_semantic_ruleset(_semantic_ruleset((_king_type(),A,BT,C),(action,),n=4,
 rows=tuple(tuple(board[i:i+4]) for i in range(0,16,4))))
records=[];discriminators=[];started=time.monotonic()
try:
 S._make_binding=binding;S._path_holds=path;S._guards_hold=guard
 for carrier in ('compat','pure'):
  c=compiled if carrier=='compat' else CompiledSemanticRuleset(ir=compiled.ir,support=compiled.support)
  engine=S(c);parent=GameSession(c).state.position;before=repr(parent)
  pid=next(p.pattern_id for p in c.ir.patterns if p.name=='change_type')
  moves=[a for a in engine.legal_actions(parent) if a.pattern_id==pid and a.source==5 and a.target==9]
  assert len(moves)==1
  child=engine.apply(parent,moves[0])
  assert repr(parent)==before and child.side_to_move==1 and child.board[5] is None
  assert child.board[9]==Piece(0,'A','B',True)
  for state,pos in [('parent',parent),('child',child)]:
   stable=repr(pos)
   for target in (10,13):
    stopped();assert time.monotonic()-started<120
    x=observe(original,engine,pos,target);y=observe(candidate,engine,pos,target)
    actual_merge=dict(proxy.last)
    assert x==y and x[0]==(state=='child' and target==10) and repr(pos)==stable
    selected=[]
    for sq,typed in c._incoming_attack_sources[('0',target)].items():
     piece=pos.board[sq]
     if piece is not None and piece.owner==0:
      selected.extend(dict(rank=rank,source=row[2],type=row[1],pattern=row[0].pattern_id,
       geometry=row[3],path=list(row[4])) for rank,row in typed.get(piece.current_type_id,()))
    G=len(actual_merge['group_lengths']);n=sum(actual_merge['group_lengths'])
    if not x[0]:
     assert actual_merge['reads']==n and actual_merge['attempts']==G+n
    else:
     inspected=sum(r[0]=='binding' for r in x[2])
     assert actual_merge['attempts']==G+inspected-1
    assert actual_merge['eof_attempts']==actual_merge['attempts']-actual_merge['reads']
    if state=='child':
     assert any(r['source']==9 and r['type']=='B' for r in selected)==(target==10)
     assert not any(r['source']==9 and r['type']=='A' for r in selected)
    faults=[]
    if state=='child' and target==10:
     wrong=observe(bad,engine,pos,target)
     assert wrong[0] is False and x[0] is True and repr(pos)==stable
     discriminators.append(dict(carrier=carrier,target=target,correct=True,wrong_base_selector=False,
      wrong_trace=wrong[2],full_child_unchanged=True))
     for stop in range(1,x[1]+1):
      fa=observe(original,engine,pos,target,stop);fb=observe(candidate,engine,pos,target,stop)
      assert fa==fb and fa[3] and fa[1]==stop and repr(pos)==stable
      faults.append(dict(stop=stop,trace=fa[2],same_exception_object_each_arm=True))
    records.append(dict(carrier=carrier,state=state,target=target,result=x[0],selected_rows=selected,
     normal_trace=x[2],actual_merge_work=actual_merge,faults=faults,full_state_unchanged=True,
     scope='public set_current_type effect, not inherited promotion masks'))
finally:
 S._make_binding=saved['binding'];S._path_holds=saved['path'];S._guards_hold=saved['guard']
out=dict(complete=True,candidate_raw_sha256=hashlib.sha256((B.parent/'task033/candidate_function.py').read_bytes()).hexdigest(),
 records=records,discriminators=discriminators,normal_pairs=len(records),
 fault_pairs=sum(len(r['faults']) for r in records),
 limits='Public initialization/legal membership/apply invokes semantic checks. No search, Native, timing, automatic promotion-mask or full-domain/OOM claim.')
(B/'current_type_child.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('current type8normal pairs,',out['fault_pairs'],'fault pairs,2bad base selectors caught')

