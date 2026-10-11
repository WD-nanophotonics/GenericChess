"""Advisor-selected eager-source boundary, two positive arms and one bad sentinel."""
import ast,heapq,json,sys
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core.semantic_executor import SemanticEngine as S
from generic_chess.session.session import GameSession
import generic_chess.core.semantic_executor as m
from scripts.reserve_refresh_diagnostic import stopped
ns=dict(vars(m));ns['heapq']=heapq
exec(compile((B.parent/'task033/candidate_function.py').read_text(encoding='utf-8'),'<frozen merge candidate>','exec'),ns)
candidate=ns['is_square_attacked'];original=S.is_square_attacked;saved_guards=S._guards_hold
compiled=compile_ruleset_for_execution(build_builtin_ruleset('western_chess'));engine=S(compiled);pos=GameSession(compiled).state.position
existing=json.loads((B.parent/'task033/rank_merge.json').read_text(encoding='utf-8'))
selected=None
for row in existing['rows']:
 if row['game']!='western_chess' or row['phase']!='initial' or not row['result'] or row['binding_events']!=1:continue
 groups=compiled._incoming_attack_sources[(str(row['owner']),row['target'])]
 sources=list(groups);tail=pos.board[sources[-1]]
 if tail is None or tail.owner!=row['owner']:
  selected=(row,groups,sources);break
assert selected is not None
row,groups,sources=selected;owner=row['owner'];target=row['target']
active=[]
for square,typed in groups.items():
 piece=pos.board[square]
 if piece is not None and piece.owner==owner:active.extend(typed.get(piece.current_type_id,()))
active.sort(key=lambda x:x[0]);assert active
# Deliberately wrong diagnostic: consumes rows before the remaining source polls.
def interleaved_bad(self,position,square,by_owner,checkpoint=None):
 if checkpoint:checkpoint()
 for source,typed in groups.items():
  if checkpoint:checkpoint()
  piece=position.board[source]
  if piece is None or piece.owner!=by_owner:continue
  for rank,record in typed.get(piece.current_type_id,()):
   pattern,tid,source,gid,path=record
   if checkpoint:checkpoint()
   binding=self._make_binding(pattern,gid,tid,piece,source,square,None,path,position)
   if self._path_holds(pattern.path,position,binding,by_owner,checkpoint=checkpoint) and self._guards_hold(pattern,position,binding,by_owner,checkpoint=checkpoint):return True
 return False
def run(fn,stop=None):
 stopped();trace=[];callbacks=0;guard_calls=0;fault=InterruptedError('one final-source boundary');before=repr(pos)
 def guards(self,*args,**kw):
  nonlocal guard_calls
  guard_calls+=1;trace.append(('guard',guard_calls));return saved_guards(self,*args,**kw)
 def checkpoint():
  nonlocal callbacks
  callbacks+=1;trace.append(('checkpoint',callbacks))
  if callbacks==stop:raise fault
 try:
  S._guards_hold=guards
  try:value=fn(engine,pos,target,owner,checkpoint=checkpoint);raised=False
  except InterruptedError as exc:assert exc is fault;value=None;raised=True
 finally:S._guards_hold=saved_guards
 assert repr(pos)==before
 return {'result':value,'callbacks':callbacks,'guards':guard_calls,'raised_exact_original_exception':raised,'trace':trace,'full_parent_unchanged':True}
normal=[run(fn) for fn in (original,candidate)];assert normal[0]==normal[1] and normal[0]['result'] is True and normal[0]['guards']==1
stop=1+len(sources)
faults=[run(fn,stop) for fn in (original,candidate)]
assert faults[0]==faults[1] and faults[0]['raised_exact_original_exception'] and faults[0]['guards']==0 and faults[0]['callbacks']==stop
bad=run(interleaved_bad,stop)
assert not bad['raised_exact_original_exception'] and bad['result'] is True and bad['guards']>0
# Separate structural invalid-metadata diagnostic; key avoids comparing row objects.
opaque1,opaque2=object(),object();ties=[[(0,opaque1)],[(0,opaque2)]]
explicit=list(heapq.merge(*ties,key=lambda entry:entry[0]));assert explicit==[(0,opaque1),(0,opaque2)]
try:list(heapq.merge(*ties))
except TypeError:unsafe_tie_rejected=True
else:raise AssertionError('row objects were accidentally comparable')
out={'complete':True,'advisor_request_id':'GC-SLACK-20261011-151326-cb77bb8c',
 'declared_eager_scan_control':{'owner':owner,'target':target,'source_order':sources,
 'last_source':sources[-1],'last_source_owner':None if pos.board[sources[-1]] is None else pos.board[sources[-1]].owner,
 'earliest_selected_rank':active[0][0],'normal':normal,'cancel_at_final_source_checkpoint':stop,'faults':faults},
 'deliberately_bad_interleaved_sentinel':bad,'invalid_duplicate_rank_structural_sentinel':{'unkeyed_TypeError':unsafe_tie_rejected,'explicit_rank_key_stable':True},
 'decision':'Adopt eager full source scan and per-key unique ranks; frozen candidate passes targeted boundary, bad interleaving is detected. Invalid tie is outside compiled premise; prefer explicit rank key in future prototype but no product edit or new580query rerun.',
 'limits':'Callback-count cancellation only; real wall deadlines/MemoryError timing differ; Dot source review not independent execution.'}
(B/'eager_source_boundary.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('Normal2/fault2 controls pass at owner/target',owner,target,'last source checkpoint',stop,'bad interleaving detected; invalid tie scoped')
