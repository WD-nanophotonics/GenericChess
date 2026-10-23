"""Independent reverse-error arithmetic and actual terminal replay, no search."""
import sys,json,gzip,math,time,argparse,hashlib
from pathlib import Path
from collections import Counter,defaultdict
sys.path.insert(0,str(Path.cwd()))
from scripts.leaper_design import compile_rule,ruleset_from_dict,GameSession,record_value
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv

def verify(packet):
 t=time.perf_counter();d=json.loads(gzip.decompress(packet.read_bytes()));assert(d['eta'],d['lam'],d['scale'])==(.05,.95,10)
 cs={w['world']:compile_rule(ruleset_from_dict(w['rule']))for w in d['inputs']['worlds']};worlds={w['world']:w for w in d['inputs']['worlds']};opens={(o['world'],o['prefix']):o for o in d['fit_openings']};groups=defaultdict(list);seen=set();counts=Counter();finals={}
 for e in d['episodes']:
  key=(e['world'],e['prefix'],e['role'],e['init']);assert key not in seen;seen.add(key)
  base=worlds[e['world']]['priors'][e['init']];ts=e['targets'];ts=[dict(value=z[0],pv_phi=z[1],pv_terminal=z[2])for z in ts]if ts and isinstance(ts[0],list)else ts
  record=d['records'][e['record']]if'record'in e else e['final_record'];rkey=json.dumps(record,sort_keys=True)
  if rkey not in finals:finals[rkey]=GameSession.replay(cs[e['world']],deserialize_game_record(json.dumps(record)))
  s=finals[rkey];v=FixedScaleSessionEnv(s,unit_type='A').terminal();assert v==e['outcome_player0']and v in(-1,0,1)
  o=opens[e['world'],e['prefix']];assert record['actions'][:len(o['record']['actions'])]==o['record']['actions']and e['opening_id']==o['id']
  predictions=[];gradients=[]
  for z in ts:
   value=z['value'];pred=math.tanh(value/10);predictions.append(pred)
   if z['pv_terminal']:
    assert value in(-1000000.,0,1000000.);gradients.append([0.]*6)
   else:
    phi=z['pv_phi'];assert len(phi)==6 and phi[3:]==[0,0,0]
    assert math.isclose(sum(a*b for a,b in zip(phi,base)),value,abs_tol=1e-12)
    gradients.append([0.]+[a*(1-pred*pred)/10 for a in phi[1:]])
   counts['targets']+=1
  errors=[(predictions[i+1]if i+1<len(ts)else v)-pred for i,pred in enumerate(predictions)];ret=[0.]*len(ts);acc=0.
  for i in reversed(range(len(ts))):acc=errors[i]+.95*acc;ret[i]=acc
  delta=[sum(.05*g[j]*r for g,r in zip(gradients,ret))for j in range(6)]
  assert max(abs(a-b)for a,b in zip(delta,e['delta']))<2e-14
  groups[e['world'],e['init']].append(e['delta']);counts['episodes']+=1
 for end in d['endpoints']:
  ds=groups[end['world'],end['init']];assert len(ds)==16
  mean=[sum(x[j]for x in ds)/16 for j in range(6)]
  assert mean==end['mean_delta']
  weights=[a+b for a,b in zip(end['base'],mean)]
  assert weights==end['shadow_endpoint']==worlds[end['world']]['priors'][end['init']+'_TD'];counts['endpoints']+=1
 assert dict(counts)==dict(targets=9803,episodes=256,endpoints=16)
 return dict(status='PASS',seconds=time.perf_counter()-t,counts=counts,distinct_final_records=len(finals),scope='Every published target arithmetic and actual source terminal replay;not omitted PV re-execution,online learning,independent engine or CPU certification.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('packet',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.packet);a.output.write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
