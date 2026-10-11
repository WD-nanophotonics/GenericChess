"""Python Native marshaling is visible, distinct from opaque C execution."""
import ast,collections,hashlib,json,sys,time
from pathlib import Path
from types import SimpleNamespace
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as P
import generic_chess.core.semantic_executor as m
from scripts.reserve_refresh_diagnostic import stopped
profile_path=Path('C:/Users/wdai/Documents/ChatGPT/GenericChess 2/.local_agent/physical-publication-20261011/residual-profile.json')
frozen=B/'frozen_residual_profile.json'
data=frozen.read_bytes() if frozen.exists() else profile_path.read_bytes()
if not frozen.exists():frozen.write_bytes(data)
profile=json.loads(data)
assert profile['complete'] and len(profile['rows'])==1
plain=json.loads((B.parent/'task027/physical-profile.json').read_text(encoding='utf-8'))['rows'][0]
def clean(v):
 if isinstance(v,dict):return {k:clean(x) for k,x in v.items() if 'seconds' not in k and not k.startswith('time_')}
 if isinstance(v,list):return [clean(x) for x in v]
 return v
assert clean(plain['decision'])==clean(profile['rows'][0]['decision'])
assert clean(plain['stats'])==clean(profile['rows'][0]['stats'])
wanted=[]
for name,suffix in (('_state_only_payload','native_legality.py'),('pack_position','native/semantic.py'),('transient_legal_actions','native/semantic.py')):
 found=[v for v in profile['functions'] if v['name']==name and v['file'].replace('\\','/').endswith(suffix)]
 assert len(found)==1 and found[0]['calls']==3179
 wanted.append({'name':name,'file_suffix':suffix,'calls':found[0]['calls'],
  'self_seconds':found[0]['self_seconds'],'cumulative_seconds':found[0]['cumulative_seconds']})
saved_init=m._WorkingPosition.__init__;saved_freeze=m._WorkingPosition.to_position;saved_trans=m.SemanticEngine._transition
cells=[]
for game in ('western_chess','standard_shogi'):
 stopped();compiled=compile_ruleset_for_execution(build_builtin_ruleset(game));pos=GameSession(compiled).state.position
 ids=tuple(sorted(compiled.support.type_metadata));stub=SimpleNamespace(type_ids=ids,type_map={tid:i for i,tid in enumerate(ids)})
 counts=collections.Counter()
 def init(*a,**kw):counts['copy']+=1;return saved_init(*a,**kw)
 def freeze(*a,**kw):counts['freeze']+=1;return saved_freeze(*a,**kw)
 def transition(*a,**kw):counts['transition']+=1;return saved_trans(*a,**kw)
 before=repr(pos)
 try:
  m._WorkingPosition.__init__=init;m._WorkingPosition.to_position=freeze;m.SemanticEngine._transition=transition
  payload=P._state_only_payload(stub,pos,0)
 finally:m._WorkingPosition.__init__=saved_init;m._WorkingPosition.to_position=saved_freeze;m.SemanticEngine._transition=saved_trans
 assert not counts and repr(pos)==before
 assert isinstance(payload['board'],list) and len(payload['board'])==len(pos.board)
 assert payload['board'] is not pos.board and payload['hands'] is not pos.hands
 assert all(isinstance(v,list) and len(v)==4 for v in payload['board'] if v is not None)
 assert len(payload['hands'])==2 and all(len(v)==len(ids) for v in payload['hands'])
 cells.append({'game':game,'board_slots_encoded':len(pos.board),'occupied_lists_encoded':sum(v is not None for v in pos.board),
  'hand_vectors':2,'hand_vector_length':len(ids),'core_method_counts':dict(counts),'full_parent_unchanged':True,
  'scope':'exact unbound Python method with declared type mapping stub; no provider selection or C kernel invoked'})
out={'complete':True,'profile_input_sha256':hashlib.sha256(data).hexdigest(),'supplied_profile_calls':wanted,'finite_payload_cells':cells,
 'decision':'Python board/hand/aux transport allocation is outside WorkingPosition clocks, and is visible without enumerating opaque C internals. Supplied residual profile already measures its3179calls, so no evidence here overturns DEFER; keep transport distinct from Core immutable publication.',
 'limits':'Profile cumulative times overlap and are instrumented; pack_position includes C pack cost. Direct payload calls are not new actual Native route callers. No speedup or pure Python total from cumulative sum.'}
(B/'native_transport_scope.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
