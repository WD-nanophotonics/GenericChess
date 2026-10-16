"""Pre-price quiet-root freeze; scoped finite RN action-guide experiment."""
from results.dev_aux.task2220.study import Guide,GuidedPlayer,key,sha
from pathlib import Path
from dataclasses import replace
from copy import copy
import json,hashlib,time
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import orbit,actor_state
from scripts.generic_royal_actor import RoyalActor
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2228')
def freeze():
 assert not(OUT/'inputs.json').exists()
 began=time.perf_counter();stop=EvidenceStopReader(Path.cwd());rs=deserialize_ruleset(Path('results/dev_aux/task2214/rules.json').read_text());actor=RoyalActor(4)
 old={r['group']for r in json.loads(Path('results/dev_aux/task2220/inputs.json').read_text())['roots']};candidates={};seen=0
 for line in Path('results/dev_aux/task2214/states.jsonl').open():
  seen+=1
  if seen%2048==0:stop();assert time.perf_counter()-began<180
  r=json.loads(line);raw=r['board']
  if r['inventory']!='KKRrn' or raw[-1]!=0 or r['status']!='ongoing':continue
  if actor.attacked(tuple(raw),actor.king(tuple(raw),0),1):continue
  if any(raw[(int(a[3])-1)*4+ord(a[2])-97]!='.'for a,ch in r['children']):continue
  group=min(key(x)for x in orbit(tuple(raw)))
  if group in old:continue
  digest=hashlib.sha256(('RN77quiet:'+group).encode()).hexdigest()
  if group not in candidates or key(raw)<key(candidates[group]['board']):candidates[group]=dict(r,group=group,order_sha=digest)
 roots=[];checked=0
 for r in sorted(candidates.values(),key=lambda x:x['order_sha']):
  stop();raw=r['board'];board=tuple(None if x=='.'else Piece(int(x.islower()),x.upper(),x.upper())for x in raw[:-1]);definition=replace(rs,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)),initial_setup_options=());s=GameSession(compile_ruleset_for_execution(definition));assert actor_state(s.state)==tuple(raw);checked+=1
  terminal=False
  for action in s.legal_actions():
   child=copy(s);child.submit(action)
   if child.result.status is not SessionStatus.ONGOING:terminal=True;break
  if terminal:continue
  family=len(roots);name=OUT/f'root-{family}.json';name.write_text(serialize_ruleset(definition),encoding='utf-8');roots.append(dict(family=family,split='DEV',group=r['group'],order_sha=r['order_sha'],board=raw,rules=str(name),rules_sha=sha(name),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),legal_actions=len(s.legal_actions())))
  if len(roots)==16:break
 assert len(roots)==16
 (OUT/'inputs.json').write_text(json.dumps(dict(roots=roots,candidate_groups=len(candidates),checked_no_oneply_terminal=checked,excluded_old_groups=len(old),selection='NEW D4/colororbits, fiveactors K+R vs K+R+N, bothinitialanchorssafe, mover hasNOlegalcapture, nooneplyterminal; shaorder RN77quiet beforeanypricequery. Entirecensussemanticallyexposed; newprice-unqueriedlayouts, notunseenrule.',seconds=time.perf_counter()-began),indent=2))
 (OUT/'plan.json').write_text(json.dumps(dict(normal_depth=2,normal_seconds=.1,source_sha=sha(OUT/'study.py'),inputs_sha=sha(OUT/'inputs.json')),indent=2))
 (OUT/'completion.json').write_text(json.dumps(dict(status='COMPLETE',operation='structuralfreezeonly',games=0,seconds=time.perf_counter()-began)))
 print('FROZEN16NEWQUIETROOTS_NO_PRICE_QUERIES',len(candidates),time.perf_counter()-began)
if __name__=='__main__':freeze()
