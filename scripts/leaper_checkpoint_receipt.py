"""Research-only original-checkpoint receipts; no clocks, GC hooks or extra polls."""
import hashlib
import inspect
import threading
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as Provider

SOURCE_SHA256='bbd0266099075be4cfea5b02e0167265e8437f85bbe346b243f03a89c2715c0b'


class CheckpointReceiptProvider:
    """Explicit callable proxy; only the pinned provider's poll order is interpreted.

    This exposes a current attempt separately from last successful timing data.
    It does not time a stage, identify where time was spent, or qualify overhead.
    No supplied checkpoint means no checkpoint observation and no added poll.
    A supplied callback can itself be a no-op (Core uses one for fallback).
    Require receipt_summary.valid before interpreting either receipt; the last
    failed receipt can be older than a later successful call. Cancellation
    outside this callable is not observed as a failed provider attempt.
    """
    def __init__(self, delegate):
        if type(delegate) is not Provider:raise TypeError('exactNativeproviderrequired')
        original=Provider.__call__
        if hashlib.sha256(inspect.getsource(original).encode('utf-8')).hexdigest()!=SOURCE_SHA256:
            raise ValueError('checkpoint-sourcechanged;reviewordinalcontractbeforeuse')
        self._delegate=delegate;self._original=original
        self._owner=threading.get_ident();self._entries=self._exits=0
        self._active=0;self._last=None;self._last_failed=None;self._current=None
        self._nested=self._foreign=self._record_errors=0

    def __getattr__(self,name):return getattr(self._delegate,name)

    @property
    def last_attempt_receipt(self):
        if self._active:return dict(id=self._current,status='in_progress',scope_valid=False)
        return None if self._last is None else dict(self._last)

    @property
    def last_failed_attempt_receipt(self):
        """Last raised attempt, which may precede a successful legal fallback.

        The id must be compared with last_attempt_receipt: this is historical
        failure evidence, never the exit status of the latest provider call.
        """
        return None if self._last_failed is None else dict(self._last_failed)

    @property
    def receipt_summary(self):
        return dict(entries=self._entries,exits=self._exits,active=self._active,
            nested_calls=self._nested,foreign_thread_calls=self._foreign,record_errors=self._record_errors,
            valid=not(self._nested or self._foreign or self._record_errors or self._active) and self._entries==self._exits,
            source_sha256=SOURCE_SHA256,limits='logicalpollboundaryonly;noelapsedtime/kernelcost/GCcausality;overheadUNMEASURED')

    def __call__(self,position,ply_count,checkpoint=None):
        self._entries+=1;serial=self._entries;self._last=None;self._current=serial
        self._nested+=self._active>0;self._foreign+=threading.get_ident()!=self._owner;self._active+=1
        ordinal=passed=0;failed=None;status='returned';error=None
        def poll():
            nonlocal ordinal,passed,failed
            ordinal+=1
            try:value=checkpoint()
            except BaseException:
                failed=ordinal;raise
            passed=ordinal;return value
        try:
            # Special-method target is the pinned CLASS function, not an
            # instance __call__ attribute that Python's callable path ignores.
            return self._original(self._delegate,position,ply_count,checkpoint=None if checkpoint is None else poll)
        except BaseException as exc:
            status='raised';error=type(exc).__name__;raise
        finally:
            self._active-=1;self._exits+=1
            try:
                if checkpoint is None:
                    stage='no_checkpoint_observation';kernel=True if status=='returned' else None
                elif status=='returned':stage='returned';kernel=True
                elif failed==1:stage='entry_checkpoint';kernel=False
                elif failed==2:stage='packed_before_kernel_checkpoint';kernel=False
                elif failed==3:stage='kernel_returned_before_decode_checkpoint';kernel=True
                elif failed is not None:stage='decode_chunk_or_final_checkpoint';kernel=True
                else:stage='between_checkpoints';kernel=False if passed<2 else True if passed>=3 else None
                self._last=dict(id=serial,status=status,exception_type=error,
                    checkpoint_observed=checkpoint is not None,checkpoint_count=ordinal if checkpoint is not None else None,
                    last_passed_checkpoint=passed if checkpoint is not None else None,
                    failed_checkpoint=failed,exit_boundary=stage,kernel_returned_known=kernel,
                    scope_valid=not(self._nested or self._foreign or self._record_errors),
                    limits='exitboundarynotblockingcause;>=4ambiguous;oldlast_call_metricsmaybelastsuccess')
                if status=='raised':self._last_failed=dict(self._last)
            except Exception:
                self._record_errors+=1;self._last=None
