from pathlib import Path
import json,time,os,statistics
R=Path.cwd();O=R/'results/dev_aux/task1450';O.mkdir(exist_ok=False);tmp=R/'.local_agent/io_cost46-corrected';tmp.mkdir(exist_ok=False)
src=R/'results/dev_aux/task1437/queries.jsonl'
examples=[]
with src.open(newline='') as f:
 for i,line in enumerate(f):
  if i<128:examples.append(line)
  else:break
assert len(examples)==128
rows=[]
for repeat in range(4):
 modes=['each','boundary'] if repeat%2==0 else ['boundary','each']
 for mode in modes:
  p=tmp/f'{repeat}-{mode}.jsonl';start=time.monotonic()
  with p.open('x',encoding='utf-8',newline='') as f:
   for line in examples:
    f.write(line);f.flush()
    if mode=='each':os.fsync(f.fileno())
   os.fsync(f.fileno())
  elapsed=time.monotonic()-start;assert p.read_bytes()==(''.join(examples)).encode()
  rows.append(dict(repeat=repeat,mode=mode,seconds=elapsed,bytes=p.stat().st_size,query_records=128,fsync_calls=129 if mode=='each' else 1))
summary={mode:statistics.median(v['seconds'] for v in rows if v['mode']==mode) for mode in ['each','boundary']}
out=dict(status='PAIRED_OWN_IO_CHECKPOINT_COST_128_ACTUAL_QUERY_RECORDS',rows=rows,median_seconds=summary,scope='Exactsame128actualquerystrings onownignoredtempdir;4counterbalancedorders, ordinaryconcurrentmachine. Bufferedflush everyquery vsfsync eachquery orgameboundary; no producer/no new search/science. Completedrawsaved, preserveall8files. Thisiscomponentcost, not endtoend8xfaster or permissiontoloseevidence.',decision='Onlyprototype boundaryfsync ifcomponentcostlarge; retainonfailureandend gamefirstqueriesfsyncthencompletedgamefsync, completevsincomplete durability explicitly.')
(O/'result.json').write_text(json.dumps(out,indent=2));print(out)

