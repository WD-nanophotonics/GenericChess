"""One finite Native frontier observer; unchanged search and transition."""
import ast,functools,hashlib,importlib.util,io,json,subprocess,sys,time,zipfile
from dataclasses import replace
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core import search_runtime as rt
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.terminal import terminal_result
from generic_chess.learning.shogi_rules import sfen_to_gc_state,gc_action_to_usi
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native import semantic as native_semantic
from scripts.search_backend_comparison import CASES,VALUES,CoreBoard,minimal_ab
from scripts.reserve_refresh_diagnostic import stopped
REV='ee48d0a55c7bda3d702f45ce2dc4162cc3bbc0ac';started=time.monotonic()
def blob(name):return subprocess.check_output(['git','show',REV+':'+name])
index=json.loads(blob('docs/research/data/availability_core_20261011.json'));raw=blob(index['archive']['path'])
assert hashlib.sha256(raw).hexdigest()==index['archive']['sha256'];z=zipfile.ZipFile(io.BytesIO(raw))
data=json.loads(z.read('.local_agent/availability-core-20261011/residual-bridge.json'))
reference=next(r for r in data['rows'] if r['root']=='shogi-drop' and r['arm']=='hybrid-memo' and r['order']==0)
weighted_path=ROOT/'.local_agent/weighted-backend-20261011/bridge.py'
assert weighted_path.read_bytes().replace(b'\r\n',b'\n')==z.read('.local_agent/weighted-backend-20261011/bridge.py').replace(b'\r\n',b'\n')
spec=importlib.util.spec_from_file_location('own_frozen_weighted',weighted_path);w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
token_path=ROOT/'.local_agent/availability-core-20261011/typed_token_probe.py';src=token_path.read_text(encoding='utf-8')
selected=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ('typed','cached','token','install')]
env=dict(rt=rt,functools=functools,original=rt._component_token);exec(compile(ast.Module(body=selected,type_ignores=[]),'<frozen token functions>','exec'),env)
case=next(x for x in CASES if x['id']=='shogi-drop');c=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'));e=w.weighted(c,VALUES['shogi'])
class DirectSFENCore(CoreBoard):
 def __init__(self,provider):
  self.game=case['game'];self.compiled=c;self.label=gc_action_to_usi;self.checkpoint=None;self.material=e
  assert case['setup']!='start' and case['setup'].split()[-1]=='1' and case['moves']==''
  state=sfen_to_gc_state(c,case['setup']);key=position_identity_key(state.position,c)
  state=replace(state,ply_count=0,history=(HistoryRecord(key,-1,'',False),))
  state=replace(state,terminal_status=terminal_result(state,c))
  self.initial=state;self.witnesses=(state.position,)
  self.runtime=rt.SearchPathRuntime.from_state(state,c,history_witnesses=self.witnesses,legal_binding_provider=provider)
rows=[]
try:
 for measured in (False,True):
  stopped();assert time.monotonic()-started<120
  provider=NativeSemanticLegalityProvider.try_create(c,strict=True);assert provider is not None
  counts={};times={}
  def wrap(name,fn):
   def call(*args,**kw):
    t=time.perf_counter()
    try:return fn(*args,**kw)
    finally:counts[name]=counts.get(name,0)+1;times[name]=times.get(name,0)+(time.perf_counter()-t)
   return call
  decode=provider._decode_action;binding=provider.engine._make_binding_from_action;kernel=native_semantic.transient_legal_actions
  if measured:
   provider._decode_action=wrap('decode',decode)
   provider.engine._make_binding_from_action=wrap('binding',binding)
   native_semantic.transient_legal_actions=wrap('native_call_and_return',kernel)
  env['cached'].cache_clear();env['install'](True)
  try:
   board=DirectSFENCore(provider);result=minimal_ab(board,2,seconds=10,node_limit=100000,trace=False)
   assert board.restored()
   for f in ('move','score','reason','completed_depth','work'):assert result[f]==reference[f],(f,result[f],reference[f])
   k=result['runtime_counters']
   assert (k['legal_provider_calls'],k['legal_provider_actions'],k['legal_provider_fallbacks'],k['legal_provider_operational_failures'])==(164,20000,0,0)
   if measured:assert counts==dict(decode=20000,binding=20000,native_call_and_return=164),counts
   rows.append(dict(measured=measured,result=result,observer_calls=counts,observer_seconds=times,typed_memo=env['cached'].cache_info()._asdict(),root_restored=True))
  finally:
   env['install'](False);provider._decode_action=decode;provider.engine._make_binding_from_action=binding;native_semantic.transient_legal_actions=kernel
 assert rows[0]['result']['work']==rows[1]['result']['work']
finally:env['install'](False)
out=dict(complete=True,source_revision=REV,archive_sha256=index['archive']['sha256'],rows=rows,
 limits='One plain/profile pair. Profile helper timers nested within provider; instrumentation changes durations. Native-call interval includes Python wrapper/C execution/return, not pure C kernel. Direct literal-SFEN constructor adaptation documented;no cshogi/specialized rerun or performance/generalization/default claim.')
(B/'drop_observer.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('same971node D2 pair pass;profile20000decode+binding/164nativecalls,fullrootrestored')
print(json.dumps(rows[1]['observer_seconds']))
