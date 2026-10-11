"""Independent finite constructor acceptance of frozen read-only working repair."""
import ast,collections,datetime,hashlib,json,subprocess,sys,time
from dataclasses import replace,fields
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tests/product')]
from generic_chess.core import search_runtime as r
from generic_chess.core.transition import apply_action
from test_native_history import _cycle_ruleset,_session_at_ply
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime
PIN='558b497ba9ab4bd5464274571923959e628cbc03'
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
(Path(__file__).parent/'frozen_working_resolve.py').write_text(excerpt)
ns=dict(vars(r));exec(compile(ast.Module(body=[resolve,push],type_ignores=[]),'frozen-working-candidate','exec'),ns)
saved_push=T.push;saved_resolve=T._resolve_opaque_history_key;saved_ctor=r._Occurrence
T.push=ns['push'];T._resolve_opaque_history_key=ns['_resolve_opaque_history_key']
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
    for context in ('complete','opaque','nested','ordinary_new'):
        for collision in (False,True):
            stopped();assert time.monotonic()-started<120
            nested=context=='nested';opaque=context in ('opaque','nested')
            session=_session_at_ply(compiled,0 if context=='ordinary_new' else (2 if nested else 3))
            public=session.state;root=replace(public,history=()) if opaque else public
            kwargs={} if opaque else {'history_witnesses':session._search_witnesses}
            if collision:kwargs['hash_override']=r.RuntimeHash(0,0)
            rt=T.from_state(root,compiled,**kwargs)
            if nested:
                outer=rt.legal_actions()[0];rt.push(outer);public=apply_action(public,outer,compiled)
            action=rt.legal_actions()[0];expected=apply_action(public,action,compiled)
            target=r._runtime_position_identity(expected.position,compiled)
            before=state(rt);baseline_integrity=integrity(rt);assert all(baseline_integrity.values())
            fault=MemoryError('DEV_AUX exact candidate constructor fault');hits=0;caller_names=[];caught=None
            def allocate(identity,count):
                global hits
                caller=sys._getframe(1).f_code.co_name;caller_names.append(caller)
                selected=(caller=='_resolve_opaque_history_key') if context!='ordinary_new' else (caller=='_occurrence_add')
                if selected and identity==target:
                    hits+=1
                    if hits==1:raise fault
                return saved_ctor(identity,count)
            r._Occurrence=allocate
            try:
                try:rt.push(action)
                except BaseException as exc:caught=exc
            finally:r._Occurrence=saved_ctor
            if context=='complete':
                assert hits==0 and caught is None
                assert rt.position==expected.position and rt.terminal_status==expected.terminal_status
                rt.pop()
            else:assert hits==1 and caught is fault
            after=state(rt);restored={k:after[k]==v for k,v in before.items()}
            assert restored['counts'] and all(v for k,v in restored.items() if k!='bucket_keys')
            if opaque:assert all(restored.values())
            after_integrity=integrity(rt);assert all(after_integrity.values())
            # Injection disabled; retry on precisely the same Runtime.
            rt.push(action);retry_public=(rt.position==expected.position and rt.terminal_status==expected.terminal_status)
            retry_integrity=integrity(rt);assert retry_public and all(retry_integrity.values())
            rt.pop();after_retry=state(rt)
            assert after_retry['counts']==before['counts'] and all(v for k,v in {k:after_retry[k]==v for k,v in before.items()}.items() if k!='bucket_keys')
            if opaque:assert after_retry==before
            rows.append({'context':context,'collision':collision,'constructor_hit_count':hits,
                'constructor_callers':caller_names,'original_exception_object_preserved':caught is fault if hits else None,
                'exception_type':None if caught is None else type(caught).__name__,
                'exception_context_type':None if caught is None or caught.__context__ is None else type(caught.__context__).__name__,
                'exception_cause_type':None if caught is None or caught.__cause__ is None else type(caught.__cause__).__name__,
                'restored_after_fault_or_control_pop':restored,'snapshot_actual_after_fault':after_integrity,
                'same_runtime_retry_public_parity':retry_public,'retry_snapshot_actual':retry_integrity,
                'restored_after_retry_pop_counts':True,'frame_depth_after_retry_pop':len(rt._frames)})
            if nested:rt.pop()
            rt.assert_balanced()
            print(context,collision,'hits',hits,'restored',restored,'retry',retry_public,flush=True)
finally:T.push=saved_push;T._resolve_opaque_history_key=saved_resolve;r._Occurrence=saved_ctor
out={'complete':True,'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'published_comparison_pin':PIN,'working_runtime_sha256':hashlib.sha256(working).hexdigest(),
    'frozen_resolve_sha256':hashlib.sha256(excerpt.encode()).hexdigest(),
    'working_module_only_changes_resolve_relative_to_published_ast':True,
    'primary_working_source_not_immutable_publication':True,
    'scope':'eight changed-premise candidate-only constructor/retry cells; no primary test execution, timing or all-allocation guarantee',
    'rows':rows}
(Path(__file__).parent/'candidate_constructor.json').write_text(json.dumps(out,indent=2)+'\n')
