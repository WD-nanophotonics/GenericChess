"""Single concrete occurrence-constructor fault in incomplete opaque migration."""
import ast,collections,datetime,hashlib,json,subprocess,sys,time
from dataclasses import replace,fields
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT),str(ROOT/'tests'),str(ROOT/'tests/product')]
from generic_chess.core import search_runtime as r
from generic_chess.core.transition import apply_action
from test_native_history import _cycle_ruleset,_session_at_ply
from scripts.reserve_refresh_diagnostic import stopped
T=r.SearchPathRuntime;original_push=T.push;original_occurrence=r._Occurrence
PIN='558b497ba9ab4bd5464274571923959e628cbc03'
blob=subprocess.check_output(['git','show',PIN+':generic_chess/core/search_runtime.py'],cwd=ROOT)
tree=ast.parse(blob);cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='SearchPathRuntime')
node=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='push')
ns=dict(vars(r));exec(compile(ast.Module(body=[node],type_ignores=[]),'published-push','exec'),ns);published_push=ns['push']
compiled=_cycle_ruleset();rows=[];start=time.monotonic()
def actual(rt):
    return frozenset(collections.Counter((h,e.identity,int(e.count)) for h,bucket in rt._occurrences.items() for e in bucket).items())
def snapshot(rt):
    return dict(position=rt.position,ply=rt.ply_count,status=rt.terminal_status,
        identity=rt.current_identity,hash=rt.runtime_hash,snapshot=rt._snapshot,
        history=tuple(rt.history),history_context=rt._history_context,
        counts=actual(rt),bucket_keys=frozenset(rt._occurrences),
        opaque_keys=frozenset(rt._opaque_imported_keys),aliases=frozenset(rt._history_aliases.items()),
        frames=tuple(tuple((f.name,tuple(getattr(frame,f.name).items()) if f.name=='bindings' else getattr(frame,f.name)) for f in fields(frame)) for frame in rt._frames),cache=rt._legal_cache,bindings=tuple(rt._bindings.items()))
def chain(exc):
    if exc is None:return []
    out=[];seen=set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc));out.append({'type':type(exc).__name__,'message':str(exc)});exc=exc.__context__
    return out
try:
    for arm,fn in [('original',original_push),('published',published_push)]:
        T.push=fn
        for context in ('complete','opaque','opaque_collision','nested','nested_collision','ordinary_new'):
            stopped();assert time.monotonic()-start<120
            nested=context.startswith('nested')
            session=_session_at_ply(compiled,0 if context=='ordinary_new' else (2 if nested else 3))
            public=session.state
            opaque=context not in ('complete','ordinary_new')
            state=replace(public,history=()) if opaque else public
            kwargs={} if opaque else {'history_witnesses':session._search_witnesses}
            if context.endswith('collision'):kwargs['hash_override']=r.RuntimeHash(0,0)
            rt=T.from_state(state,compiled,**kwargs)
            if nested:
                outer=rt.legal_actions()[0];rt.push(outer);public=apply_action(public,outer,compiled)
            action=rt.legal_actions()[0];expected=apply_action(public,action,compiled);before=snapshot(rt)
            captured={};calls=0;hit=False
            def occurrence(identity,count):
                global calls,hit
                calls+=1
                frame=rt._frames[-1] if rt._frames else None
                bridge=frame is not None and frame.bridge_key is not None
                selected=(bridge if context!='ordinary_new' else (frame is not None and not bridge))
                if not hit and selected and isinstance(identity,r.RuntimePositionIdentity):
                    hit=True
                    captured.update(bridge=bridge,child_added=frame.child_occurrence_added,
                        frame_depth=len(rt._frames),old_count=frame.bridge_old_count,
                        old_key_present=frame.bridge_key in rt._opaque_imported_keys if bridge else None,
                        old_entry_removed=(not any(isinstance(e.identity,r._ImportedIdentity) and e.identity.external_key==frame.bridge_key for b in rt._occurrences.values() for e in b)) if bridge else None)
                    raise MemoryError('DEV_AUX one occurrence constructor allocation failure')
                return original_occurrence(identity,count)
            r._Occurrence=occurrence;exc=None
            try:
                try:rt.push(action)
                except BaseException as err:exc=err
            finally:r._Occurrence=original_occurrence
            after=snapshot(rt);checks={k:after[k]==v for k,v in before.items()}
            if context=='complete':
                assert not hit and exc is None
                assert rt.position==expected.position and rt.terminal_status==expected.terminal_status
                rt.pop();after=snapshot(rt);checks={k:after[k]==v for k,v in before.items()}
                assert all(checks.values())
            elif context=='ordinary_new':
                assert hit and isinstance(exc,MemoryError) and checks['counts']
                assert not checks['bucket_keys']
            else:
                assert hit and isinstance(exc,AssertionError) and isinstance(exc.__context__,MemoryError)
                assert not checks['counts'] and checks['position'] and checks['snapshot']
                assert len(rt._frames)==(1 if nested else 0)
            rows.append({'arm':arm,'context':context,'constructor_calls':calls,'fault_reached':hit,
                'fault_state':captured,'exception_chain':chain(exc),'restored_fields':checks,
                'actual_entries_before':sum(n for item,n in before['counts']),
                'actual_entries_after':sum(n for item,n in after['counts']),
                'total_occurrence_count_before':sum(item[2]*n for item,n in before['counts']),
                'total_occurrence_count_after':sum(item[2]*n for item,n in after['counts']),
                'frame_depth_after':len(rt._frames),'empty_buckets_after':sum(not b for b in rt._occurrences.values())})
            print(arm,context,hit,chain(exc),checks,flush=True)
finally:T.push=original_push;r._Occurrence=original_occurrence
out={'complete':True,'baseline':'b4108a68a7ee06327be39cb3a222939644085a52','published_push_pin':PIN,
    'published_runtime_blob_sha256':hashlib.sha256(blob).hexdigest(),
    'scope':'12 frozen single-constructor fault/control cells; no Native, timing or natural failure claim; damaged bridge runtimes discarded',
    'rows':rows}
(Path(__file__).parent/'bridge_constructor.json').write_text(json.dumps(out,indent=2)+'\n')
