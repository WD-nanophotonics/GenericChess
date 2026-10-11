"""Two frozen static evaluator points, no searches or timing benchmark."""
import hashlib,importlib.util,json,sys,time
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.attacks import pseudo_attacks
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from scripts.chess_development import root_from_fen
from scripts.search_backend_comparison import CASES,VALUES,Material
from generic_chess.native.semantic import pack_current_position,dynamic_features,evaluate
from generic_chess.native.compiler import NativeUnsupportedRuleError
started=time.monotonic();binary=ROOT/'generic_chess/_native_core.cp312-win_amd64.pyd';binary_hash=hashlib.sha256(binary.read_bytes()).hexdigest();assert binary_hash=='2f97cfb8816bc963163207095bf40ac990169284cd0cfb2e7b545f0a6bf07bf1'
wpath=ROOT/'.local_agent/weighted-backend-20261011/bridge.py';s=importlib.util.spec_from_file_location('weighted',wpath);w=importlib.util.module_from_spec(s);s.loader.exec_module(w)
rows=[]
for root in ('shogi-drop','chess-tactic'):
 assert time.monotonic()-started<30
 case=next(v for v in CASES if v['id']==root);assert case['moves']=='' and case['setup']!='start'
 game=case['game'];compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi' if game=='shogi' else 'western_chess'))
 state=sfen_to_gc_state(compiled,case['setup']) if game=='shogi' else root_from_fen(case['setup'],compiled)
 provider=NativeSemanticLegalityProvider.try_create(compiled,strict=True);assert provider is not None
 native=provider.native_rules;packed=pack_current_position(native,state.position,ply_count=state.ply_count)
 features=dynamic_features(native,packed);values=tuple(VALUES[game][tid] for tid in native.type_ids)
 native_score=evaluate(native,packed,board_values=values,hand_values=values,dynamic_values=(2,3,5))
 material=Material(game).evaluate(state);core_score=w.weighted(compiled,VALUES[game]).evaluate(state)
 attacks=tuple(len(pseudo_attacks(state.position,owner,compiled)) for owner in (0,1))
 try:native.require_terminal_policy_support();terminal=dict(supported=True)
 except NativeUnsupportedRuleError as ex:terminal=dict(supported=False,error_type=type(ex).__name__,message=str(ex))
 row=dict(root=root,setup=case['setup'],material=material,core_weighted=core_score,native_copied_coefficients=native_score,difference=native_score-core_score,pseudo_attack_counts=attacks,native_features=features,native_type_ids=native.type_ids,native_report=dict(payload_version=native.report.semantic_payload_version,executable=native.native_executable),terminal_gate=terminal)
 rows.append(row);print(json.dumps(row))
assert any(r['difference']!=0 for r in rows)
out=dict(complete=True,binary_sha256=binary_hash,product_revision='b4108a68a7ee06327be39cb3a222939644085a52',rows=rows,limits='Two exposed imported static roots; no search, timing, terminal adjudication or full history transport claim. Mismatch disproves coefficient-copy correspondence only. No evaluator is preferred or fitted.')
(B/'evaluator_correspondence.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
