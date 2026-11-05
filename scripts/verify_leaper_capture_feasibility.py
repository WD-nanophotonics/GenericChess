"""Read saved frontiers/child replies/microtimings;zero Core/Player execution."""
from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,statistics
from scripts.research_record import write_record

def key(x):return json.dumps(x,sort_keys=True,separators=(',',':'))
def verify(base,out):
 b=Path(base);f=json.loads((b/'frozen.json').read_text());assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['input_sha256']
 rows=json.loads((b/'inputs.json').read_text())['rows'];front=[json.loads(p.read_text()) for p in sorted(b.glob('frontier-*.json'))];caps=[json.loads(p.read_text()) for p in sorted(b.glob('capture-[0-9][0-9][0-9].json'))]
 assert len(front)==len(rows)==85 and len(caps)==23
 by_input=defaultdict(list)
 for c in caps:
  original=json.loads((b/f"capture-child-{c['slot']:03}.json").read_text());assert (original['input'],original['action'],original['child_result'])==(c['input'],c['action'],c['actual_child_result']);by_input[c['input']].append(c)
 groups=defaultdict(lambda:[0.,0.,0]);changed=[];royal=[];single=empty=0
 for row in front:
  capture=by_input[row['input']];assert len(capture)==row['eligible_captures']
  old,new=row['baseline_order'],row['candidate_order'];assert Counter(map(key,old))==Counter(map(key,new))
  relevant={key(x['action']):x for x in capture};slots=[i for i,x in enumerate(old) if key(x) in relevant]
  for i in range(len(old)):
   if i not in slots:assert old[i]==new[i]
  expected=sorted((old[i] for i in slots),key=lambda a:relevant[key(a)]['model_score'],reverse=True)
  assert [new[i] for i in slots]==expected
  changed_now=any(old[i]!=new[i] for i in slots);assert changed_now==row['capture_order_changed']
  if changed_now:changed.append(row['input'])
  measurements=row['measurements'];assert Counter(x['method'] for x in measurements)=={'baseline':32,'geometric':32}
  for name in ('baseline','geometric'):
   assert abs(sum(x['seconds'] for x in measurements if x['method']==name)-row[name+'_seconds_32'])<1e-12
  group='zero' if not capture else 'one' if len(capture)==1 else 'two_or_more'
  groups[group][0]+=row['baseline_seconds_32'];groups[group][1]+=row['geometric_seconds_32'];groups[group][2]+=1
  empty+=not capture;single+=len(capture)==1
  for c in capture:
   mover=row['actual_prices'][c['action']['actor_type_id']];numerator=c['baseline_priority']+mover//10;assert numerator%10==0;victim=numerator//10
   if c['legal_royal_reply_values']:
    material_after_legal_royal_reply=victim-mover
    royal.append(dict(slot=c['slot'],input=c['input'],root=rows[c['input']]['root'],prefix=rows[c['input']]['prefix'],action=c['action'],victim_value=victim,mover_value=mover,model_score=c['model_score'],material_after_legal_royal_reply=material_after_legal_royal_reply,model_exceeds_that_reply=c['model_score']>material_after_legal_royal_reply))
 totals=[sum(v[i] for v in groups.values()) for i in (0,1)];n=sum(v[2] for v in groups.values())
 r=dict(status='PASS_SAVED_FRONTIER_ACCEPTANCE',states=len(rows),capture_children=len(caps),changed_frontiers=changed,changed_families=sorted({rows[i]['family'] for i in changed}),zero_capture_frontiers=empty,one_capture_frontiers=single,cost_groups={k:dict(frontiers=v[2],baseline_seconds_32=v[0],geometric_seconds_32=v[1],component_ratio=v[1]/v[0] if v[0] else None) for k,v in groups.items()},incremental_microseconds_per_frontier=(totals[1]-totals[0])/32/n*1e6,royal_cases=royal,optimistic_royal_cases=sum(x['model_exceeds_that_reply'] for x in royal),newCore=0,newPlayer=0,newPN=0,limits='legalreplyfactsproducerCoreattributed;materialexchangeproxyisnotWDL/actualoptimalactionbound;componentmicrocostnotwholePlayer;twochangedfrontiersonefamilyinsufficientqualityevidence')
 write_record(out,r);return r
if __name__=='__main__':
 import sys;r=verify(sys.argv[1],sys.argv[2]);print(json.dumps({k:v for k,v in r.items() if k!='royal_cases'}))
