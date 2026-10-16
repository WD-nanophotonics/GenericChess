"""All D4 orientations of the fixed16 quiet families; no outcome selection."""
from results.dev_aux.task2220.study import Guide,GuidedPlayer,sha,key
from pathlib import Path
from dataclasses import replace
import json,hashlib
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.pieces import Piece
from scripts.generic_proof_rnb_bridge import orbit,actor_state
OUT=Path('results/dev_aux/task2234')
def freeze():
 assert not(OUT/'inputs.json').exists();rs=deserialize_ruleset(Path('results/dev_aux/task2214/rules.json').read_text());parents=json.loads(Path('results/dev_aux/task2228/inputs.json').read_text())['roots'];roots=[]
 for parent in parents:
  variants=sorted([raw for raw in orbit(tuple(parent['board']))if raw[-1]==0],key=key);assert len(variants)==8
  for orientation,raw in enumerate(variants):
   board=tuple(None if x=='.'else Piece(int(x.islower()),x.upper(),x.upper())for x in raw[:-1]);definition=replace(rs,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)),initial_setup_options=());s=GameSession(compile_ruleset_for_execution(definition));assert actor_state(s.state)==raw
   family=len(roots);name=OUT/f'root-{family}.json';name.write_text(serialize_ruleset(definition));roots.append(dict(family=family,parent_family=parent['family'],orientation=orientation,split='DEV',group=parent['group'],board=raw,rules=str(name),rules_sha=sha(name),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),legal_actions=len(s.legal_actions())))
 (OUT/'inputs.json').write_text(json.dumps(dict(roots=roots,selection='ALL8D4orientations ofALL16frozenquietfamilies, includingoriginalorientation;128layoutsbutONLY16familyblocks, allprice-exposedfamilyresource/tieordercontrol, notnewholdout. No outcome-basedorientation/rootselection.'),indent=2))
 (OUT/'plan.json').write_text(json.dumps(dict(normal_depth=2,normal_seconds=.5,inputs_sha=sha(OUT/'inputs.json'),source_sha=sha(OUT/'study.py')),indent=2));(OUT/'completion.json').write_text(json.dumps(dict(status='COMPLETE',operation='D4structuralfreezeonly',roots=128,games=0)));print('FROZEN128D4_LAYOUTS16FAMILIES')
if __name__=='__main__':freeze()
