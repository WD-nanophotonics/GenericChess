"""Bounded research-only frontier/GC intervals; no kernel or GC-setting changes."""
from __future__ import annotations

import gc
import heapq
import math
import threading
import time
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider


def overlap_union(start, end, intervals):
    """Length of union intersected with one wall interval, never a sum of buckets."""
    clipped=sorted((max(start,a),min(end,b)) for a,b in intervals if a<end and start<b)
    total=0.0;left=right=None
    for a,b in clipped:
        if a>=b:continue
        if right is None:left,right=a,b
        elif a>right:total+=right-left;left,right=a,b
        else:right=max(right,b)
    return total+(0 if right is None else right-left)


class FrontierObserver:
    """Inclusive Python provider spans plus complete bounded GC intervals.

    Only the eight longest frontier spans and deadline crossings retain details.
    All calls retain entry/exit counts and inclusive totals. GC event overflow,
    unmatched boundaries, clock errors or cleanup faults invalidate observation.
    No positions, actions, runtime owners or Native payloads are retained.
    """
    def __init__(self, deadline=None, *, clock=time.perf_counter, gc_cap=2048):
        self.deadline=deadline;self.clock=clock;self.gc_cap=gc_cap
        self.entries=self.exits=self.exceptions=0
        self.total_seconds=0.0;self.longest=[];self.crossings=[]
        self.gc_events=[];self.gc_pending={};self.gc_count=0;self.gc_dropped=0
        self.boundary_errors=self.observer_errors=0
        self.gc_registered=False;self.uncovered_frontiers=0
        self.error_types=[];self.current_frontier=None
        self._entered=False;self._original=None;self._wrapper=None;self._callback=None
        self.restored=False;self.callbacks_restored=False;self.cleanup_error=None

    def _error(self, name):
        self.observer_errors+=1
        if len(self.error_types)<8:self.error_types.append(name)

    def _now(self):
        try:return self.clock()
        except Exception as exc:
            self._error(type(exc).__name__);return float('nan')

    def _gc_event(self, phase, info):
        try:
            now=self._now();tid=threading.get_ident();generation=info.get('generation',-1);key=(tid,generation)
            if phase=='start':
                if key in self.gc_pending:self.boundary_errors+=1
                self.gc_pending[key]=(now,self.current_frontier)
            elif phase=='stop':
                self.gc_count+=1;begin=self.gc_pending.pop(key,None)
                if begin is None:self.boundary_errors+=1;return
                start,owner=begin
                if not (math.isfinite(start) and math.isfinite(now) and start<=now):self.boundary_errors+=1;return
                event=(start,now,generation,tid,owner,info.get('collected',0),info.get('uncollectable',0))
                if len(self.gc_events)<self.gc_cap:self.gc_events.append(event)
                else:self.gc_dropped+=1
            else:self.boundary_errors+=1
        except Exception as exc:self._error(type(exc).__name__)

    def _note(self, serial, start, end, thread, outcome):
        self.exits+=1;self.exceptions+=outcome!='returned'
        if not (math.isfinite(start) and math.isfinite(end) and start<=end):
            self._error('nonmonotonic_frontier_clock');return
        duration=end-start;self.total_seconds+=duration
        value=(duration,serial,start,end,thread,outcome)
        if len(self.longest)<8:heapq.heappush(self.longest,value)
        elif duration>self.longest[0][0]:heapq.heapreplace(self.longest,value)
        if self.deadline is not None and start<=self.deadline<end:
            if len(self.crossings)<8:self.crossings.append(value)
            else:self._error('deadline_crossing_overflow')

    def __enter__(self):
        if self._entered:raise RuntimeError('observer scopes are single-use')
        original=NativeSemanticLegalityProvider.__call__
        if getattr(original,'_research_frontier_observer',False):raise RuntimeError('nested observer scope unsupported')
        self._entered=True;self._original=original;self.owner_thread=threading.get_ident()
        self.preexisting_callbacks=tuple(gc.callbacks);self.gc_settings=(gc.isenabled(),gc.get_threshold(),gc.get_debug())
        self.started=self._now();rec=self
        def wrapped(provider, position, ply_count, checkpoint=None):
            rec.entries+=1;serial=rec.entries;start=rec._now();thread=threading.get_ident()
            covered=rec.gc_registered
            previous=rec.current_frontier;rec.current_frontier=serial;outcome='returned'
            try:
                return original(provider,position,ply_count,checkpoint=checkpoint)
            except BaseException as exc:
                outcome=type(exc).__name__;raise
            finally:
                end=rec._now();rec.current_frontier=previous
                try:
                    if not covered:rec.uncovered_frontiers+=1
                    rec._note(serial,start,end,thread,outcome)
                except Exception as exc:rec._error(type(exc).__name__)
        wrapped._research_frontier_observer=True
        self._wrapper=wrapped;self._callback=self._gc_event
        NativeSemanticLegalityProvider.__call__=wrapped
        try:
            gc.callbacks.append(self._callback);self.gc_registered=True;self.gc_registered_at=self._now()
        except BaseException:
            NativeSemanticLegalityProvider.__call__=original;self._wrapper=None;self._callback=None;raise
        return self

    def __exit__(self, exc_type, exc, traceback):
        callback=self._callback
        self.gc_removed_at=self._now();self.gc_registered=False
        try:
            if NativeSemanticLegalityProvider.__call__ is self._wrapper:
                NativeSemanticLegalityProvider.__call__=self._original;self.restored=True
            else:self.cleanup_error='foreign_method_replacement';self._error(self.cleanup_error)
        finally:
            for i,entry in enumerate(gc.callbacks):
                if entry is callback:del gc.callbacks[i];break
            self.callbacks_restored=(not any(entry is callback for entry in gc.callbacks)
                and all(any(entry is old for entry in gc.callbacks) for old in self.preexisting_callbacks))
            self.settings_unchanged=self.gc_settings==(gc.isenabled(),gc.get_threshold(),gc.get_debug())
            self.ended=self._now();self._callback=None;self._wrapper=None
        # Never replace an original exception with a recorder/cleanup exception.
        return False

    def snapshot(self):
        origin=self.started
        def offset(value):
            number=value-origin
            return number if math.isfinite(number) else None
        gc_events=[dict(start=offset(a),end=offset(b),generation=g,thread=t,frontier_owner=o,collected=c,uncollectable=u)
                   for a,b,g,t,o,c,u in self.gc_events]
        def span(value):
            duration,serial,start,end,thread,outcome=value
            return dict(id=serial,start=offset(start),end=offset(end),duration=duration,thread=thread,outcome=outcome,
                gc_overlap_seconds=overlap_union(start,end,[(g[0],g[1]) for g in self.gc_events]),
                same_thread_gc_overlap_seconds=overlap_union(start,end,[(g[0],g[1]) for g in self.gc_events if g[3]==thread]))
        valid=(math.isfinite(self.started) and math.isfinite(self.ended) and self.started<=self.ended
               and self.restored and self.callbacks_restored and self.settings_unchanged and self.entries==self.exits
               and not(self.observer_errors or self.boundary_errors or self.gc_pending or self.gc_dropped or self.uncovered_frontiers))
        return dict(valid=valid,entries=self.entries,exits=self.exits,exception_exits=self.exceptions,
            inclusive_frontier_seconds=self.total_seconds,longest=[span(v) for v in sorted(self.longest,reverse=True)],
            deadline_crossings=[span(v) for v in self.crossings],deadline_offset=None if self.deadline is None else offset(self.deadline),
            GC=gc_events,GC_registered_scope=[offset(self.gc_registered_at),offset(self.gc_removed_at)],GC_uncovered_frontiers=self.uncovered_frontiers,GC_completed=self.gc_count,GC_dropped=self.gc_dropped,GC_open_boundaries=len(self.gc_pending),
            boundary_errors=self.boundary_errors,observer_errors=self.observer_errors,error_types=self.error_types,
            original_function_restored=self.restored,own_callback_removed=self.callbacks_restored,GC_settings_unchanged=self.settings_unchanged,
            preexisting_GC_callback_count=len(self.preexisting_callbacks),scope_thread=self.owner_thread,
            retention='top8frontiers+<=8deadlinecrossings;allGCintervalsupto2048;otherfrontiercallsaggregateonly',
            limits='frontierincludespacking/kernel/decode/Python/GC/observer/scheduling;GCoverlapisunionintersection,notexclusivekernelorsum;observermayperturbGCschedule;scopeboundary/overflowinvalid')
