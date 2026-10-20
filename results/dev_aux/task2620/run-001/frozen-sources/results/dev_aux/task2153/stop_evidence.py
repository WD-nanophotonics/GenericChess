"""Fail closed with exact private evidence if a fresh stop observation is invalid.

No retry, freshness/mtime cache, polling delay, flag rewrite or stop bypass.
Equivalent normal path to2131; only diagnostic failure type changes so broad
prover ValueError handlers cannot hide a stop-I/O/JSON failure as unsupported.
"""
from pathlib import Path
import json,hashlib,uuid,datetime
from results.dev_aux.task2131.stop_reader import ParsedStopReader
from results.dev_aux.task109.adapter import PersistentStop

class StopObservationFailure(RuntimeError):
 pass

class EvidenceStopReader(ParsedStopReader):
 def __init__(self,root):
  super().__init__(root)
  self.root=Path(root).resolve()
  self.errors_dir=self.root/'.local_agent'/'stop-observation-errors'
 def failed(self,path,raw,error):
  # Exact bytes belong only in the caller's ignored private layer.
  self.errors_dir.mkdir(parents=True,exist_ok=True)
  event=uuid.uuid4().hex
  if raw is not None:
   with(self.errors_dir/(event+'.raw')).open('xb')as f:f.write(raw)
  owner='DEV_AUX'if path.parent.parent.resolve()==self.root else'PRIMARY_READ_ONLY'
  meta=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),owner=owner,file=path.name,error_type=type(error).__name__,error_message=str(error),raw_bytes=None if raw is None else len(raw),raw_sha256=None if raw is None else hashlib.sha256(raw).hexdigest(),raw_file=None if raw is None else event+'.raw',action='FAIL_CLOSED_NO_RETRY_OR_FLAG_WRITE')
  with(self.errors_dir/(event+'.json')).open('x',encoding='utf-8')as f:json.dump(meta,f,indent=2)
  raise StopObservationFailure('Invalid fresh stop observation; private evidence '+event)from error
 def __call__(self):
  for path in self.paths:
   raw=None
   try:
    raw=path.read_bytes();self.reads+=1;self.bytes_read+=len(raw)
    previous=self._cache.get(path)
    if previous is None or previous[0]!=raw:
     value=json.loads(raw)
     stopped=bool(value.get('user_paused')or value.get('stopped'))
     self._cache[path]=(raw,stopped);self.parses+=1
    else:stopped=previous[1]
   except(OSError,ValueError,TypeError,AttributeError)as error:self.failed(path,raw,error)
   if stopped:raise PersistentStop('persistent user stop')
