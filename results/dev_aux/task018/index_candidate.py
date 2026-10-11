"""Frozen revised index-before-mutation candidate, exact comparison fault."""
import ast,collections,datetime,hashlib,json,subprocess,sys,time
from dataclasses import replace,fields
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tests/product')]
from generic_chess.core import search_runtime as r
from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import apply_action
from test_native_history import _cycle_ruleset,_session_at_ply
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime;PIN='558b497ba9ab4bd5464274571923959e628cbc03'
PRIMARY=Path(r'C:\Users\wdai\Documents\ChatGPT\GenericChess 2')
published=subprocess.check_output(['git','show',PIN+':generic_chess/core/search_runtime.py'],cwd=ROOT)
working=(PRIMARY/'generic_chess/core/search_runtime.py').read_bytes()
left=ast.parse(published);right=ast.parse(working)
getcls=lambda t:next(n for n in t.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
lc=getcls(left);rc=getcls(right)
resolve=next(n for n in rc.body if isinstance(n,ast.FunctionDef) and n.name=='_resolve_opaque_history_key')
lc.body=[resolve if isinstance(n,ast.FunctionDef) and n.name==resolve.name else n for n in lc.body]
assert ast.dump(left,include_attributes=False)==ast.dump(right,include_attributes=False)
push=next(n for n in rc.body if isinstance(n,ast.FunctionDef) and n.name=='push')
excerpt=ast.unparse(resolve)+'\n'
assert 'old_index = old_bucket.index(old_entry)' in excerpt and 'del old_bucket[old_index]' in excerpt
(Path(__file__).parent/'frozen_working_resolve.py').write_text(excerpt)
ns=dict(vars(r));exec(compile(ast.Module(body=[resolve,push],type_ignores=[]),'frozen-index-candidate','exec'),ns)
saved_push=T.push;saved_resolve=T._resolve_opaque_history_key;saved_eq=r._Occurrence.__eq__
def counts(rt):
    return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,bucket in rt._occurrences.items() for e in bucket).items())
def state(rt):
    return dict(position=rt.position,ply=rt.ply_count,status=rt.terminal_status,
        identity=rt.current_identity,hash=rt.runtime_hash,snapshot=rt._snapshot,
        history=tuple(rt.history),history_context=rt._history_context,
        counts=counts(rt),bucket_keys=frozenset(rt._occurrences),
        opaque_keys=frozenset(rt._opaque_imported_keys),aliases=frozenset(rt._history_aliases.items()),
        frames=tuple(tuple((f.name,tuple(getattr(frame,f.name).items()) if f.name=='bindings' else getattr(frame,f.name)) for f in fields(frame)) for frame in rt._frames),
        cache=rt._legal_cache,bindings=tuple(rt._bindings.items()))
def integrity(rt):
    rebuilt=rt._snapshot_from_occurrences()
    return dict(items=rt._snapshot.items()==rebuilt.items(),digest=rt._snapshot.digest==rebuilt.digest)
rows=[];started=time.monotonic();compiled=_cycle_ruleset()
try:
    T.push=ns['push'];T._resolve_opaque_history_key=ns['_resolve_opaque_history_key']
    for nested in (False,True):
        session=_session_at_ply(compiled,2 if nested else 3);public=session.state
        if nested:
            outer=session.legal_actions()[0]
            target_public=apply_action(public,outer,compiled);action=legal_target=next(iter(__import__('generic_chess.core.transition',fromlist=['legal_actions']).legal_actions(target_public,compiled)))
        else:target_public=public;action=session.legal_actions()[0]
        expected=apply_action(target_public,action,compiled);key=position_identity_key(expected.position,compiled)
        reordered=tuple((k,n) for k,n in public.repetition_counts if k!=key)+tuple((k,n) for k,n in public.repetition_counts if k==key)
        assert dict(reordered)==dict(public.repetition_counts) and reordered[-1][0]==key
        root=replace(public,history=(),repetition_counts=reordered)
        for collision in (False,True):
            for inject in (False,True):
                stopped();assert time.monotonic()-started<120
                rt=T.from_state(root,compiled,hash_override=r.RuntimeHash(0,0) if collision else None)
                if nested:rt.push(outer)
                rt.legal_actions();before=state(rt);assert all(integrity(rt).values())
                fault=MemoryError('DEV_AUX exact prelocated-index comparison fault');hits=0;eligible=0;caught=None;stage=None
                def eq(self,other):
                    global hits,eligible,stage
                    caller=sys._getframe(1).f_code.co_name
                    selected=(caller=='_resolve_opaque_history_key' and self is not other and isinstance(other.identity,r._ImportedIdentity) and other.identity.external_key==key)
                    if selected:
                        eligible+=1
                        if inject and not hits:
                            hits+=1
                            frame=rt._frames[-1]
                            stage={'bridge_journal_active':frame.bridge_key is not None,'child_occurrence_added':frame.child_occurrence_added}
                            raise fault
                    return saved_eq(self,other)
                r._Occurrence.__eq__=eq
                try:
                    try:rt.push(action)
                    except BaseException as exc:caught=exc
                finally:r._Occurrence.__eq__=saved_eq
                if inject and collision:
                    assert hits==1 and caught is fault and stage=={'bridge_journal_active':False,'child_occurrence_added':False}
                else:
                    assert hits==0 and caught is None
                    assert rt.position==expected.position and rt.terminal_status==expected.terminal_status
                    rt.pop()
                assert state(rt)==before and all(integrity(rt).values())
                rt.push(action);retry_public=rt.position==expected.position and rt.terminal_status==expected.terminal_status
                assert retry_public and all(integrity(rt).values());rt.pop();assert state(rt)==before
                rows.append({'nested':nested,'collision':collision,'injected':inject,'eligible_comparisons':eligible,
                    'fault_hits':hits,'fault_stage':stage,'original_exception_object_preserved':caught is fault if hits else None,
                    'exception_context_type':None if caught is None or caught.__context__ is None else type(caught.__context__).__name__,
                    'exception_cause_type':None if caught is None or caught.__cause__ is None else type(caught.__cause__).__name__,
                    'all_root_fields_counts_buckets_aliases_frames_restored':True,'snapshot_actual_consistent':True,
                    'same_runtime_retry_public_parity':retry_public,'same_runtime_retry_pop_restored':True})
                if nested:rt.pop()
                rt.assert_balanced();print(rows[-1],flush=True)
finally:T.push=saved_push;T._resolve_opaque_history_key=saved_resolve;r._Occurrence.__eq__=saved_eq
out={'complete':True,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'published_comparison_pin':PIN,'working_runtime_sha256':hashlib.sha256(working).hexdigest(),
    'frozen_resolve_sha256':hashlib.sha256(excerpt.encode()).hexdigest(),
    'working_module_only_changes_resolve_relative_to_published_ast':True,'working_source_not_immutable_publication':True,
    'scope':'eight revised candidate-only exact comparison/retry cells; not primary tests, global OOM or timing',
    'rows':rows}
(Path(__file__).parent/'index_candidate.json').write_text(json.dumps(out,indent=2)+'\n')
