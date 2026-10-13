import json,sys,hashlib,collections
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task493';sys.path.insert(0,str(R/'results/dev_aux/task390'));from analyze import features
p=R/'results/dev_aux/task492/result.json';d=json.loads(p.read_text(encoding='utf-8'));assert d['status']=='PASS_QUALIFIED_CONTROL' and not d['mismatches'];MAP={'P':1,'L':2,'N':3,'S':4,'B':5,'R':6,'G':7,'K':8}
def cells(sfen):
 ans={}
 for ri,row in enumerate(sfen.split()[0].split('/')):
  col=0;prom=False
  for ch in row:
   if ch=='+':prom=True;continue
   if ch.isdigit():col+=int(ch);continue
   ans[str(9-col)+chr(97+ri)]=MAP[ch.upper()]+(8 if prom else 0);col+=1;prom=False
  assert col==9
 return ans
checks=[]
for x in d['pairs']:
 assert x['same_first_context'];a=x['base'];b=x['full'];assert a is not None and b is not None;w=x['weights'];board=cells(a['sfen']);victim=board.get(a['move'][2:4],0);bp=w[victim];p0=C.Board(a['sfen']);m=p0.move_from_usi(a['move']);assert p0.is_legal(m);v0,_=features(p0.sfen());sign=1 if p0.turn==0 else -1;p0.push(m);v1,_=features(p0.sfen());gain=sign*sum(w[i]*(v1[i]-v0[i]) for i in range(16));assert a['full']==a['old']-bp+gain;cross=(a['old']<=a['alpha'])!=(a['full']<=a['alpha']);assert cross==a['threshold_crossing'];accum=(a['old']<=a['alpha']) and (a['full']<=a['alpha']) and max(a['best'],a['old'])!=max(a['best'],a['full']);assert cross or (a['phase']=='q' and accum);assert a['mode']==0 and b['mode']==1
 for e in [a,b]:
  selected=e['full'] if e['mode'] else e['old'];assert ('futility_prune' in e['outcomes'])==(selected<=e['alpha']);assert len(e['outcomes'])==1
  if e['returns']:
   assert e['outcomes']==['recursive_enter'] and len(e['returns'])==1;ret=e['returns'][0];expected='UNKNOWN_STOPPED' if ret['stopped'] else 'upper_fail_low' if ret['value']<=ret['alpha'] else 'lower_fail_high' if ret['value']>=ret['beta'] else 'inside_window_selective';assert expected==ret['window_bucket']
 checks.append(dict(pair=x['index'],phase=a['phase'],victim_type=victim,captured_board_price=bp,native_immediate_gain=gain,old_proxy=a['old'],full_proxy=a['full'],threshold_crossing=cross,accumulator_effect=accum,base_outcomes=a['outcomes'],full_outcomes=b['outcomes'],full_returns=b['returns']))
entries=0
for ack in d['price_acks']:
 w=ack['weights'];seen=[]
 for line in ack['prices']:
  if not line.startswith('info string auxprice '):continue
  pc,val,sgn,cap,prom=map(int,line.split()[3:]);pt=pc%16;base=pt-8 if pt in range(9,15) else pt;assert val==w[pt] and sgn==(w[pt] if pc<16 else -w[pt]) and cap==(0 if pt in (0,8,15) else w[pt]+w[base]) and prom==(w[base+8]-w[base] if base in range(1,7) else 0);seen.append(pc);entries+=1
 assert sorted(seen)==list(range(32))
out=dict(status='PASS_NATIVE_FIRST_CONTEXT',pairs=len(checks),checks=checks,fulltable_entries=entries,source='results/dev_aux/task492/result.json',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),phase_counts=dict(collections.Counter(x['phase'] for x in checks)),full_return_window_buckets=dict(collections.Counter(z['window_bucket'] for x in checks for z in x['full_returns'])),new_go=0,scope='ALL32firstcausalcontexts, nativelegal/literalmaterial/proxy/boolprune/qaccumulator/actualoutcomes/returnwindowtags and4096tables verified. Sourceonlychangesarithmetic at2expressions; samefullroot coldinputs/singleworker yieldscommonprefix beforefirststateeffect. No laterlogline pairing orarbitrarybranchcontext restoration. Selectiveinside-window != certifiedexact fulltree; stoppedunknown remains.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k!='checks'})
