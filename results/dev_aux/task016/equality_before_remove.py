"""Distinct comparator allocation fault before old occurrence removal."""
import ast,collections,datetime,dis,hashlib,json,subprocess,sys,time
from dataclasses import replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tests/product')]
from generic_chess.core import search_runtime as r
from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import apply_action
from test_native_history import _cycle_ruleset,_session_at_ply
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime;PIN='558b497ba9ab4bd5464274571923959e628cbc03'
blob=subprocess.check_output(['git','show',PIN+':generic_chess/core/search_runtime.py'],cwd=ROOT)
tree=ast.parse(blob);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
old_resolve=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_resolve_opaque_history_key')
push=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='push')
frozen=(ROOT/'results/dev_aux/task015/frozen_working_resolve.py').read_bytes()
new_resolve=ast.parse(frozen).body[0]
ns=dict(vars(r));exec(compile(ast.Module(body=[push],type_ignores=[]),'published-push','exec'),ns)
saved_push=T.push;saved_resolve=T._resolve_opaque_history_key;saved_eq=r._Occurrence.__eq__
instructions=[{'op':i.opname,'arg':i.argval} for i in dis.get_instructions(saved_eq)]
assert sum(i['op']=='BUILD_TUPLE' for i in instructions)>=2
def actual(rt):
    return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,b in rt._occurrences.items() for e in b).items())
def rootstate(rt):
    return (rt.position,rt.ply_count,rt.terminal_status,rt.current_identity,rt.runtime_hash,
        rt._snapshot,tuple(rt.history),rt._history_context,frozenset(rt._opaque_imported_keys),
        frozenset(rt._history_aliases.items()),len(rt._frames),rt._legal_cache,tuple(rt._bindings.items()))
def key_count(rt,key):
    return sum(int(e.count) for b in rt._occurrences.values() for e in b if isinstance(e.identity,r._ImportedIdentity) and e.identity.external_key==key)
def integrity(rt):
    rebuilt=rt._snapshot_from_occurrences()
    return {'items':rt._snapshot.items()==rebuilt.items(),'digest':rt._snapshot.digest==rebuilt.digest}
compiled=_cycle_ruleset();session=_session_at_ply(compiled,3);public=session.state
action=session.legal_actions()[0];expected=apply_action(public,action,compiled)
key=position_identity_key(expected.position,compiled)
reordered=tuple((k,n) for k,n in public.repetition_counts if k!=key)+tuple((k,n) for k,n in public.repetition_counts if k==key)
assert dict(reordered)==dict(public.repetition_counts) and reordered[-1][0]==key
root=replace(public,history=(),repetition_counts=reordered);rows=[];start=time.monotonic()
try:
    T.push=ns['push']
    for arm,node in [('published',old_resolve),('target_first_working',new_resolve)]:
        local=dict(vars(r));exec(compile(ast.Module(body=[node],type_ignores=[]),'frozen-resolve','exec'),local)
        T._resolve_opaque_history_key=local['_resolve_opaque_history_key']
        for inject in (False,True):
            stopped();assert time.monotonic()-start<120
            rt=T.from_state(root,compiled,hash_override=r.RuntimeHash(0,0));rt.legal_actions()
            before=actual(rt);before_root=rootstate(rt);before_count=key_count(rt,key)
            fault=MemoryError('DEV_AUX one occurrence equality tuple allocation failure')
            reached=0;thrown=0;caught=None
            def eq(self,other):
                global reached,thrown
                caller=sys._getframe(1).f_code.co_name
                selected=(caller=='_resolve_opaque_history_key' and self is not other and isinstance(other.identity,r._ImportedIdentity) and other.identity.external_key==key)
                if selected:
                    reached+=1
                    if inject and not thrown:thrown+=1;raise fault
                return saved_eq(self,other)
            r._Occurrence.__eq__=eq
            try:
                try:rt.push(action)
                except BaseException as exc:caught=exc
            finally:r._Occurrence.__eq__=saved_eq
            assert reached>=1
            if not inject:
                assert caught is None and thrown==0
                assert rt.position==expected.position and rt.terminal_status==expected.terminal_status
                rt.pop();assert actual(rt)==before and rootstate(rt)==before_root
            else:
                assert thrown==1
                if arm=='published':assert isinstance(caught,AssertionError) and caught.__context__ is fault
                else:assert caught is fault
            rows.append({'arm':arm,'injected':inject,'eligible_comparisons':reached,'fault_hit_count':thrown,
                'exception_type':None if caught is None else type(caught).__name__,
                'exception_message':None if caught is None else str(caught),
                'escaping_original_exception_object':caught is fault if inject else None,
                'original_fault_is_exception_context':caught.__context__ is fault if caught is not None else None,
                'actual_counts_restored':actual(rt)==before,'root_fields_restored':rootstate(rt)==before_root,
                'imported_target_count_before':before_count,'imported_target_count_after':key_count(rt,key),
                'snapshot_actual_consistency':integrity(rt)})
            print(rows[-1],flush=True)
finally:T.push=saved_push;T._resolve_opaque_history_key=saved_resolve;r._Occurrence.__eq__=saved_eq
out={'complete':True,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'published_pin':PIN,'target_first_frozen_resolve_sha256':hashlib.sha256(frozen).hexdigest(),
    'public_repetition_mapping_preserved_by_order_permutation':True,
    'occurrence_eq_disassembly':instructions,'scope':'four declared exact comparator allocation controls, not global OOM/UI/TT or constructor repair rejection','rows':rows}
(Path(__file__).parent/'equality_before_remove.json').write_text(json.dumps(out,indent=2)+'\n')
