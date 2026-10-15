"""Independent exact price-profile ACK/clear/options/actualgo scope audit."""
from pathlib import Path
from collections import Counter
import json,hashlib,sys
OUT=Path('results/dev_aux/task1878')
def read(p):return json.loads(Path(p).read_text())
def audit(folder):
 root=Path(folder);plan=read(root/'run-plan.json');done=read(root/'completion.json');assert done['status']=='COMPLETE';events=[json.loads(x) for x in (root/'run/transport.jsonl').read_text().splitlines()];profile=None;options={};counts=Counter();native=[];clear=False;profiles=[]
 for e in events:
  kind=e['event']
  if kind=='OPTION':
   options[e['name']]=e['value'];assert not any('No such option' in l or 'Unknown command' in l for l in e['raw'])
  elif kind=='PROFILE':
   r,n,b,p=e['values'];profile=e['values'];clear=False;counts['exact_profile_ACK']+=1;profiles.append(e)
   expected=f'info string DEV_AUX leafRNBP {r} {n} {b} {p} nativeP {p} nativeR {r} nativeN {n} nativeB {b} captureP {p} captureR {r} captureN {n} captureB {b}'
   assert expected in e['ack'] and 'readyok' in e['ack']
   assert any(x.startswith('info string variant ') and ' files 4 ranks 4 ' in x for x in e['raw'])
  elif kind=='CLEAR':assert e['values']==profile and 'readyok' in e['raw'];clear=True;counts['coldclear']+=1
  elif kind=='INTENT':
   assert clear and e['R']==profile;fields=e['command'].split();assert fields[:2]==['go','nodes'];assert fields[3]=='movetime' and 1<=int(fields[4])<=100
   native.append(e);clear=False
 assert len(native)==counts['exact_profile_ACK']==counts['coldclear']==done['native_go']
 assert options['Threads']==1 and options['Hash']==16 and options['Use NNUE']=='false' and options['SyzygyPath']=='<empty>'
 binary=Path(plan['native_plan']['binary']);digest=hashlib.sha256(binary.read_bytes()).hexdigest();assert plan['native_plan']['files'][str(binary)]==digest
 return dict(status='PASS_ALL_EXACT_PROFILE_AND_FIXED_OPTION_BINDINGS',folder=root.as_posix(),queries=len(native),counts=dict(counts),options=options,binary_sha=digest,scope='Every INTENT preceded by exact aligned leaf/native/capture tableACK andcoldclear; allrequestednodes/fullhistory already independentlybound by gameauditor. Normalmovetime1..100ms, actualreportednodeovershoot retained. SingleThread1Hash16NNUEfalse, no originalStockfish/NNUE or allrulesNative claim.')
if __name__=='__main__':
 folder=sys.argv[1];result=audit(folder);name=Path(folder).name+'-profiles.json'
 with (OUT/name).open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
