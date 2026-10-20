"""Windows fresh read cooperating with atomic rename/delete sharing.

Read-only GENERIC_READ, OPEN_EXISTING, normal attributes. Compatible sharing
permits other handles' read/write/delete access; never overrides ACLs/exclusive
sharing, retries failures, caches stop content or keeps a handle across polls.
"""
from pathlib import Path
from io import FileIO
import ctypes,os,sys,json
from ctypes import wintypes
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
from results.dev_aux.task109.adapter import PersistentStop
if sys.platform!='win32':raise NotImplementedError('Windows read-sharing prototype only')
import msvcrt
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
create=kernel.CreateFileW;create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE];create.restype=wintypes.HANDLE
close=kernel.CloseHandle;close.argtypes=[wintypes.HANDLE];close.restype=wintypes.BOOL
INVALID=ctypes.c_void_p(-1).value

def open_shared(path,*,access=0x80000000,share=7):
 handle=create(str(path),access,share,None,3,0x80,None)
 if handle==INVALID:raise ctypes.WinError(ctypes.get_last_error())
 return handle

def read_fresh(path):
 handle=open_shared(path)
 try:fd=msvcrt.open_osfhandle(handle,os.O_RDONLY|os.O_BINARY|os.O_NOINHERIT)
 except BaseException:close(handle);raise
 source=None
 try:
  source=FileIO(fd,'r',closefd=True)
  return source.readall()
 finally:
  if source is None:os.close(fd)
  else:source.close()

class SharedDeleteStopReader(EvidenceStopReader):
 def __call__(self):
  for path in self.paths:
   raw=None
   try:
    raw=read_fresh(path);self.reads+=1;self.bytes_read+=len(raw)
    previous=self._cache.get(path)
    if previous is None or previous[0]!=raw:
     value=json.loads(raw);stopped=bool(value.get('user_paused')or value.get('stopped'));self._cache[path]=(raw,stopped);self.parses+=1
    else:stopped=previous[1]
   except(OSError,ValueError,TypeError,AttributeError)as error:self.failed(path,raw,error)
   if stopped:raise PersistentStop('persistent user stop')
