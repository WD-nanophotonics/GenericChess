"""One fixed-root causal TT-depth diagnostic; no product edits or new games.

The exact-depth intervention preserves best-action hints but makes deeper
entries inadmissible for numerical return/PV reconstruction. It is a diagnostic
policy, NOT a proposed production fix. Original failed control stays failed.
"""
import argparse,hashlib,json,time
from pathlib import Path
from datetime import datetime,timezone
from scripts.leaper_pvs_quality_pilot import make_session,CallerDeadline
from scripts.research_record import record_value,write_record
from tools.local_agent.common import read_json
from tools.local_agent import session
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable,TTEntry,score_from_tt
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.session.session import GameSession

def stamp():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def keyhash(k):return hashlib.sha256(repr(k).encode()).hexdigest()

class TraceTable(TranspositionTable):
    def __init__(self,trace,stack,exact_only=False):
        super().__init__();self.trace=trace;self.stack=stack;self.exact_only=exact_only
    def probe(self,key):
        entry=super().probe(key)
        if entry is None:return None
        frame=self.stack[-1] if self.stack else {}
        deeper=entry.depth>frame.get('depth',entry.depth)
        event=dict(kind='probe',frame=dict(frame),key_sha256=keyhash(key),key_bank=key[1] if isinstance(key,tuple) and key[0]=='main-check-extension/v1' else None,entry_depth=entry.depth,bound=entry.bound.name,stored_score=entry.score,deeper=deeper,downgraded=bool(deeper and self.exact_only))
        self.trace.append(event)
        if deeper and self.exact_only:
            return TTEntry(entry.key,frame['depth']-1,entry.score,entry.bound,entry.best_action,entry.generation)
        return entry
    def clone(self,trace,stack,exact_only=False):
        target=TraceTable(trace,stack,exact_only)
        target._generation=self._generation
        target._data={k:TTEntry(e.key,e.depth,e.score,e.bound,e.best_action,e.generation) for k,e in self._data.items()}
        return target
    def digest(self):
        rows=sorted((keyhash(k),e.depth,e.score,e.bound.name,str(e.best_action),e.generation) for k,e in self._data.items())
        return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def run(prepared,plan_path,out):
    assert not out.exists();plan=read_json(plan_path)
    for p,h in plan['sources'].items():assert sha(p)==h
    assert sha(prepared/'inputs.json')==plan['input_sha256']
    row=next(r for r in json.loads((prepared/'inputs.json').read_bytes())['rows'] if r['id']==plan['root_id']);c,s=make_session(row)
    player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_one_check_extension=True),use_native_semantic_legality=True,use_native_semantic_check=True,use_native_semantic_availability=True)
    provider=player._native_legality_provider;out.mkdir();write_record(out/'frozen.json',dict(plan=plan,sources={p:Path(p).read_text(encoding='utf8') for p in plan['sources']}))
    stack=[];events=[];results=[];nodeid=0;original=S.negamax;originalpv=S._tt_principal_line;tick=time.perf_counter()
    def observed(state,depth,alpha,beta,ply,ctx,prev_action=None,node_key=None,pv_node=True,remaining_extensions=None):
        nonlocal nodeid
        nodeid+=1;frame=dict(kind='main',call_id=nodeid,parent_id=stack[-1].get('call_id') if stack else None,depth=depth,ply=ply,entry_bank=1 if remaining_extensions is None else remaining_extensions,alpha=alpha,beta=beta)
        stack.append(frame)
        try:return original(state,depth,alpha,beta,ply,ctx,prev_action,node_key,pv_node,remaining_extensions)
        finally:stack.pop()
    def observedpv(ctx,depth,ply,score,entry=None,remaining_extensions=None):
        frame=dict(kind='PV',call_id=stack[-1].get('call_id') if stack else None,depth=depth,ply=ply,entry_bank=1 if remaining_extensions is None else remaining_extensions)
        stack.append(frame)
        try:
            answer=originalpv(ctx,depth,ply,score,entry,remaining_extensions)
            if answer is not None:
                events.append(dict(kind='PV_adopted',frame=dict(frame),entry_depth=entry.depth if entry is not None else None,score=score,PV_length=len(answer),deeper=entry is not None and entry.depth>depth))
            return answer
        finally:stack.pop()
    S.negamax=observed;S._tt_principal_line=observedpv
    def query(label,e,table,tt=True):
        events.clear();begin=stamp();t=time.perf_counter();before=s.to_record()
        ctx=S._Context(c,player._evaluator,table,SearchStatistics(),S._Budget(SearchLimits(max_nodes=500000,max_time_seconds=20,quiescence_max_depth=4,quiescence_hard_max_depth=8),CallerDeadline(t+20)),SearchTuning(use_one_check_extension=True,require_full_pv=True),tt,True,4,8,None,runtime=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses,legal_binding_provider=provider,availability_provider=provider.has_legal_action,check_provider=provider.in_check))
        x=dict(label=label,entry_bank=e,table_before=table.digest(),status='UNKNOWN')
        try:
            got=S.negamax(ctx.runtime.state,3,-S.INF,S.INF,0,ctx,remaining_extensions=e)
            pv=GameSession.replay(c,before)
            for a in got.pv:pv.submit(a)
            x.update(status='RETURNED',score=got.score,pv=record_value(got.pv),best_action=record_value(got.best_action))
        except S.SearchAborted as exc:x['reason']=str(exc)
        ctx.runtime.assert_balanced();assert s.to_record()==before
        x.update(started_at=begin,ended_at=stamp(),seconds=time.perf_counter()-t,statistics=record_value(ctx.stats),table_after=table.digest(),probe_events=len(events),deeper_probes=sum(y['kind']=='probe' and y['deeper'] for y in events),downgraded=sum(y['kind']=='probe' and y['downgraded'] for y in events),deeper_PV_adoptions=sum(y['kind']=='PV_adopted' and y['deeper'] for y in events))
        write_record(out/(label+'-events.json'),events);results.append(x);write_record(out/'queries.json',results);session.record_work(begin,x['ended_at'],'validation',str(out/'queries.json')+':'+label);print(json.dumps({k:x[k] for k in ('label','status','score','seconds','deeper_probes','downgraded','deeper_PV_adoptions') if k in x}),flush=True)
    try:
        cold0=TraceTable(events,stack);cold1=TraceTable(events,stack)
        query('cold0',0,cold0);query('cold1',1,cold1)
        normal=cold1.clone(events,stack);exact=cold1.clone(events,stack,True);assert normal.digest()==exact.digest()
        write_record(out/'clone-control.json',dict(normal_initial=normal.digest(),exact_initial=exact.digest(),same_entries_and_hints=True,difference='Only numerical/PV admissibility of entries deeper than current requested horizon;production unchanged'))
        for label,e,table,use in [('hot0-normal',0,normal,True),('hot0-exactdepth',0,exact,True),('noTT0',0,TraceTable(events,stack),False),('hot0-samebank',0,cold0.clone(events,stack),True)]:
            if time.perf_counter()-tick+22>=plan['batch_seconds'] or (datetime.fromisoformat(plan['whole_deadline_utc'])-datetime.now(timezone.utc)).total_seconds()<plan['delivery_reserve_seconds']+22:break
            query(label,e,table,use)
    finally:S.negamax=original;S._tt_principal_line=originalpv
    write_record(out/'summary.json',dict(queries=results,interpretation='Controlled fixed-root depth-admissibility diagnostic,NOT product fix or altered original audit. Deeper TT reuse can change fixed-horizon estimates. A restored value supports that mechanism only;not all-bank safety or WDL proof.',seconds=time.perf_counter()-tick))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.prepared,a.plan,a.output)
