import sys,json,time,hashlib,os
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G
O=R/'results/dev_aux/task396';O.mkdir(exist_ok=True);old=json.loads((R/'results/dev_aux/task364/declaration.json').read_text(encoding='utf-8'));roots=[f for f in old['roots'] if f['phase']=='train'];timings=[];decl=dict(profiles=old['profiles'],roots=roots,nodes=1024,cap=24,executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest(),source_reference='task369frozen16actualgames384go',scope='measure exact existing protocolready/positionstate/go/serialization/flush/fsync; sameprice/history/goal/PVvalidator, no journalpolicy change',newrun_expected='under30seconds,600secondfuse; soleproducer after387complete');(O/'declaration.json').write_text(json.dumps(decl,indent=2),encoding='utf-8')
class Traced(A.Engine):
 def search(self,initial,history,nodes=1024):
  start=time.perf_counter();self.send('isready');ready=self.until(lambda x:x=='readyok');ready_at=time.perf_counter();self.position(initial,history);self.send('auxstate');state=self.until(lambda x:x.startswith('info string auxstate '))[-1];state_at=time.perf_counter();t=time.monotonic();cmd=f'go nodes {nodes}';self.send(cmd);out=self.until(lambda x:x.startswith('bestmove '));go_at=time.perf_counter();r=dict(initial_sfen=initial,history=list(history),weights=self.w,nodes_limit=nodes,cold_isready=ready,state=state,command=cmd,lines=out,bestmove=out[-1].split()[1],seconds=time.monotonic()-t);serialize_start=time.perf_counter();text=json.dumps(r,ensure_ascii=False)+'\n';serialized=time.perf_counter();self.journal.write(text);written=time.perf_counter();self.journal.flush();flushed=time.perf_counter();os.fsync(self.journal.fileno());synced=time.perf_counter();timings.append(dict(call=len(timings),weights=list(self.w),history_plies=len(history),ready=ready_at-start,position_state=state_at-ready_at,go=go_at-state_at,serialize=serialized-serialize_start,write=written-serialized,flush=flushed-written,fsync=synced-flushed,search_outer=synced-start));return r
calls={name:{'calls':0,'seconds':0.0} for name in ['stop','terminal','full_root','validate_search','quantity']}
def trace_call(owner,name):
 original=getattr(owner,name)
 def wrapped(*args,**kwargs):
  begin=time.perf_counter()
  try:return original(*args,**kwargs)
  finally:calls[name]['calls']+=1;calls[name]['seconds']+=time.perf_counter()-begin
 setattr(owner,name,wrapped)
for name in ['stop','terminal','full_root','quantity']:trace_call(G,name)
trace_call(A,'validate_search')
rows=[];t0=time.monotonic()
with (O/'queries.jsonl').open('w',encoding='utf-8') as qj,(O/'games.jsonl').open('w',encoding='utf-8') as gj:
 eu=Traced(old['profiles'][0]['weights'],qj)
 try:
  for p in old['profiles']:
   ec=Traced(p['weights'],qj)
   try:
    for f in roots:
     for c in (0,1):
      before=len(timings);g=G.game(ec,eu,p['weights'],f,c,gj,deadline=t0+600);rows.append(dict(weights=p['weights'],seed=f['seed'],color=c,gamewall=g['seconds'],go=len(g['queries']),query_start=before,query_stop=len(timings)))
   finally:ec.close()
 finally:eu.close()
fields=['ready','position_state','go','serialize','write','flush','fsync','search_outer'];sums={k:sum(r[k] for r in timings) for k in fields};result=dict(seconds=time.monotonic()-t0,games=len(rows),go=len(timings),gamewall_sum=sum(r['gamewall'] for r in rows),component_sums=sums,controller_function_timings=calls,controller_timing_scope='nested full_root/terminal counters overlap, do not sumthem as exclusive',rows=rows,timings=timings,scope='protocolcomponent wallnotCPU; instrumentation/ordinaryload limits; exactbehaviour audit separate, no exclusivewall ornoisefreeclaim');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['rows','timings']}))