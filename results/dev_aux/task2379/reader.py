"""Opt-in same-call fresh file observations via unbuffered FileIO.

One open/readall/close per path on EVERY poll, same path order/content decoder/
truthiness/fail-closed diagnostics. No held descriptors/mtime/TTL/poll-skipping.
Atomic path replacement is observed on next call; no PRIMARY/source mutation.
"""
from io import FileIO
import json
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task109.adapter import PersistentStop

class FreshFileIOStopReader(EvidenceStopReader):
 def __call__(self):
  for path in self.paths:
   raw=None
   try:
    with FileIO(path,'r') as source:raw=source.readall()
    self.reads+=1;self.bytes_read+=len(raw)
    previous=self._cache.get(path)
    if previous is None or previous[0]!=raw:
     value=json.loads(raw)
     stopped=bool(value.get('user_paused')or value.get('stopped'))
     self._cache[path]=(raw,stopped);self.parses+=1
    else:stopped=previous[1]
   except(OSError,ValueError,TypeError,AttributeError)as error:self.failed(path,raw,error)
   if stopped:raise PersistentStop('persistent user stop')
