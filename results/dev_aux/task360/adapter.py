import os,subprocess,threading,queue,time,json,hashlib,random,sys
from pathlib import Path
import shogi
R=Path.cwd();EXE=R/'.local_agent/yaneura25/yaneura-material1-aux.exe'
# Only the engine adapter module uses SFEN transport. Every move and goal is independently replayed.
class Engine:
 def __init__(self,w,journal=None):
  self.w=list(w); self.journal=journal; self.q=queue.Queue();self.transcript=[]
  env=os.environ.copy();env['DEV_AUX_SHOGI_VALUES']=' '.join(map(str,w[1:15]));self.p=subprocess.Popen([str(EXE)],cwd=EXE.parent,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
  def reader():
   for line in self.p.stdout:self.q.put(line.rstrip('\r\n'))
   self.q.put(None)
  self.reader=threading.Thread(target=reader,daemon=True);self.reader.start();self.send('usi');self.until(lambda x:x=='usiok')
  opts={'Threads':'1','USI_Hash':'16','BookFile':'no_book','GenerateAllLegalMoves':'true','EnteringKingRule':'NoEnteringKing','DrawValueBlack':'0','DrawValueWhite':'0','PvInterval':'0','MultiPV':'1','USI_Ponder':'false'}
  for k,v in opts.items():self.send(f'setoption name {k} value {v}')
  self.send('isready');self.until(lambda x:x=='readyok');self.send('auxprices');self.prices=self.until(lambda x:x.startswith('info string auxprice 31 '))
 def send(self,s):self.transcript.append({'in':s});self.p.stdin.write(s+'\n');self.p.stdin.flush()
 def until(self,pred,timeout=15):
  end=time.monotonic()+timeout;out=[]
  while True:
   x=self.q.get(timeout=max(.001,end-time.monotonic()))
   if x is None:raise RuntimeError(f'engine exit {self.p.poll()}')
   out.append(x);self.transcript.append({'out':x})
   if pred(x):return out
 def position(self,initial,history):self.send('position sfen '+initial+(' moves '+' '.join(history) if history else ''))
 def state(self,initial,history):
  self.position(initial,history);self.send('auxstate');out=self.until(lambda x:x.startswith('info string auxstate '));return out[-1]
 def search(self,initial,history,nodes=1024):
  self.send('isready');ready=self.until(lambda x:x=='readyok');self.position(initial,history);self.send('auxstate');state=self.until(lambda x:x.startswith('info string auxstate '))[-1];t=time.monotonic();cmd=f'go nodes {nodes}';self.send(cmd);out=self.until(lambda x:x.startswith('bestmove '));r={'initial_sfen':initial,'history':list(history),'weights':self.w,'nodes_limit':nodes,'cold_isready':ready,'state':state,'command':cmd,'lines':out,'bestmove':out[-1].split()[1],'seconds':time.monotonic()-t}
  if self.journal:
   self.journal.write(json.dumps(r,ensure_ascii=False)+'\n');self.journal.flush();os.fsync(self.journal.fileno())
  return r
 def close(self):
  if self.p.poll() is None:self.send('quit');self.p.wait(timeout=10)
# Yaneura engine piece IDs differ from python-shogi G/B/R IDs.
MAP={1:1,2:2,3:3,4:4,5:7,6:5,7:6,8:8,9:9,10:10,11:11,12:12,13:13,14:14}
def material(b,w):
 value=sum((1 if p.color==shogi.BLACK else -1)*w[MAP[p.piece_type]] for sq in range(81) if (p:=b.piece_at(sq)) is not None)
 for c in (shogi.BLACK,shogi.WHITE):
  value+=sum((1 if c==shogi.BLACK else -1)*n*w[MAP[p]] for p,n in b.pieces_in_hand[c].items())
 return value

def replay(initial,h):
 b=shogi.Board(initial)
 for s in h:
  m=shogi.Move.from_usi(s);assert m in b.legal_moves,(b.sfen(),s);b.push(m)
 return b

def validate_state(line,b,w):
 a=line.split(' ',7);cached,full,turn=map(int,a[3:6]);repetition=a[6];sfen=a[7];expect=material(b,w);assert cached==full==expect,(line,expect);assert turn==(expect if b.turn==shogi.BLACK else -expect);assert sfen.split()[:3]==b.sfen().split()[:3];return {'cached':cached,'full':full,'turn_value':turn,'repetition':repetition,'sfen':sfen}

def validate_search(r):
 b=replay(r['initial_sfen'],r['history']);validate_state(r['state'],b,r['weights']);m=shogi.Move.from_usi(r['bestmove']);assert m in b.legal_moves
 for line in r['lines']:
  if ' pv ' in line:
   q=replay(r['initial_sfen'],r['history'])
   for u in line.split(' pv ',1)[1].split():
    m=shogi.Move.from_usi(u);assert m in q.legal_moves,(line,u,q.sfen());q.push(m)
 return True