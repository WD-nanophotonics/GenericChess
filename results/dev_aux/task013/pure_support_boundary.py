"""Finite direct provider controls for pure semantic support carriers."""
import ast,datetime,hashlib,json,subprocess,sys,time
from pathlib import Path
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.rules.ir import CompiledSemanticRuleset
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as P
import generic_chess.ai.alphabeta.native_legality as pm
from generic_chess.core.search_runtime import SearchPathRuntime as R
from generic_chess.core.transition import legal_actions
from generic_chess.session.session import GameSession
from scripts.reserve_refresh_diagnostic import stopped
PIN='558b497ba9ab4bd5464274571923959e628cbc03'
blob=subprocess.check_output(['git','show',PIN+':generic_chess/ai/alphabeta/native_legality.py'],cwd=ROOT)
tree=ast.parse(blob);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativeSemanticLegalityProvider')
node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='supports_position')
ns=dict(vars(pm));exec(compile(ast.Module(body=[node],type_ignores=[]),'immutable-published-support-gate','exec'),ns)
original=P.supports_position;candidate=ns['supports_position'];rows=[];start=time.monotonic()
def actual(rt):
    from collections import Counter
    return frozenset(Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
try:
    for game in ('western_chess','standard_shogi'):
        for boundary in ('default','max1'):
            rules=build_builtin_ruleset(game)
            if boundary=='max1':rules=replace(rules,max_ply=1)
            compat=compile_ruleset_for_execution(rules)
            pure=CompiledSemanticRuleset(ir=compat.ir,support=compat.support)
            for carrier,compiled in (('compat',compat),('pure',pure)):
                session=GameSession(compiled);expected=set(legal_actions(session.state,compiled))
                for changed in (False,True):
                    P.supports_position=candidate if changed else original
                    for strict in (False,True):
                        stopped();assert time.monotonic()-start<120
                        provider=P.try_create(compiled,strict=strict);assert provider is not None
                        rt=R.from_state(session.state,compiled,history_witnesses=session._search_witnesses,legal_binding_provider=provider)
                        before=(rt.position,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),actual(rt))
                        raised=None;actions=None;capability=None
                        try:capability=provider.supports_position(rt.position,rt.ply_count)
                        except AttributeError:capability='AttributeError'
                        try:actions=rt.legal_actions()
                        except AttributeError as exc:raised=type(exc).__name__
                        assert (rt.position,rt.current_identity,rt.runtime_hash,rt._snapshot,tuple(rt.history),actual(rt))==before
                        if actions is not None:assert set(actions)==expected
                        missing=(carrier=='pure' and not changed)
                        excluded=(game=='standard_shogi' and boundary=='max1')
                        assert (raised is not None)==(missing and strict)
                        if missing:
                            assert capability=='AttributeError' and rt.legal_provider_calls==0
                            assert rt.legal_provider_operational_failures==(0 if strict else 1)
                            assert rt._legal_provider_active is strict
                        else:
                            assert capability is (not excluded)
                            assert rt.legal_provider_calls==(0 if excluded else 1)
                            assert rt.legal_provider_fallbacks==int(excluded)
                            assert rt.legal_provider_operational_failures==0 and rt._legal_provider_active
                        rows.append({'game':game,'boundary':boundary,'carrier':carrier,'published_method':changed,'strict':strict,'capability':capability,'exception':raised,'legal_actions':None if actions is None else len(actions),'public_core_actions':len(expected),'accepted_frontiers':rt.legal_provider_calls,'fallbacks':rt.legal_provider_fallbacks,'operational_failures':rt.legal_provider_operational_failures,'provider_active':rt._legal_provider_active,'actual_counts_root_restored':True})
finally:P.supports_position=original
out={'complete':True,'baseline':'b4108a68a7ee06327be39cb3a222939644085a52','published_method_pin':PIN,'published_provider_blob_sha256':hashlib.sha256(blob).hexdigest(),'scope':'32 finite pure/compat direct frontier controls; no timing/search/evaluator or all-generated-domain claim','rows':rows}
(Path(__file__).parent/'pure_support_boundary.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
