"""Late independent reproducer of frozen2100/2105 INPUTS, zero fitness.

Reconstructed from executed sampling algorithm, not claimed a pre-draw pin.
Compare every board, rule serialization, fingerprint and structural draw count.
"""
from pathlib import Path
from dataclasses import replace
import json,random,time
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.pieces import Piece
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from scripts.generic_royal_actor import RoyalActor
OUT=Path('results/dev_aux/task2112')
def run():
 start=time.perf_counter();seen=set();positions=0;compilecache={}
 for folder in('results/dev_aux/task2055','results/dev_aux/task2063'):
  plan=json.loads(Path(folder+'/run-plan.json').read_text(encoding='utf-8'))
  for line in Path(folder+'/games.jsonl').read_text(encoding='utf-8').splitlines():
   g=json.loads(line);rules=plan['rules']if'rules'in plan else plan['roots'][g['family']]['rules']
   if rules not in compilecache:compilecache[rules]=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text(encoding='utf-8')))
   rec=deserialize_game_record(json.dumps(g['record']));raw=actor_state(GameSession(compilecache[rules],rec.initial_setup_key).state);positions+=1
   if sum(ch!='.'for ch in raw[:-1])==5 and not any(ch.upper()=='R'for ch in raw[:-1]):seen.update(orbit(raw))
   for a in rec.actions:
    i=a.from_square.file+4*a.from_square.rank;j=a.to_square.file+4*a.to_square.rank;rr=list(raw);assert rr[i]!='.'and int(rr[i].islower())==raw[-1];rr[j]=rr[i];rr[i]='.';rr[-1]=1-rr[-1];raw=tuple(rr);positions+=1
    if sum(ch!='.'for ch in raw[:-1])==5 and not any(ch.upper()=='R'for ch in raw[:-1]):seen.update(orbit(raw))
 expected=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text(encoding='utf-8'));frozen=json.loads(Path('results/dev_aux/task2100/study-freeze.json').read_text(encoding='utf-8'));rng=random.Random(frozen['seed']);actor=RoyalActor(4);base=deserialize_ruleset(Path('results/dev_aux/task2097/rules.json').read_text(encoding='utf-8'));accepted=0;attempts=0
 while accepted<48:
  attempts+=1;owner=rng.randrange(2);sq=rng.sample(range(16),5);raw=['.']*16
  for at,ch in zip(sq,('K','k','B'if owner==0 else'b','N'if owner==0 else'n','b'if owner==0 else'B')):raw[at]=ch
  raw=tuple(raw)+(0,)
  if raw in seen or any(actor.attacked(raw,actor.king(raw,side),1-side)for side in(0,1))or any(len(actor.moves(raw[:-1]+(side,)))<2 for side in(0,1)):continue
  row=expected['roots'][accepted];assert list(raw)==row['root'];board=[None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in raw[:-1]];rule=replace(base,initial_position=tuple(tuple(board[i:i+4])for i in range(0,16,4)),initial_setup_options=());c=compile_ruleset_for_execution(rule);assert c.ruleset_fingerprint==row['fingerprint']and serialize_ruleset(rule)==Path(row['rules']).read_text(encoding='utf-8');seen.update(orbit(raw));accepted+=1
 assert attempts==expected['attempts']==163 and positions==expected['prior_positions']==17605
 result=dict(status='PASS_ALL48_FROZEN_INPUTS_REPRODUCED',accepted=accepted,attempts=attempts,prior_physical_boards=positions,fitness_calls=0,seconds=time.perf_counter()-start,scope='Lateindependentreproducer/exactboards+rules+fingerprints, notpre-drawsourcepin. NoCoregame/PN/teacherlabel/rewardfilter. Timingmetadata nondeterministic, notclaimedbyte-identicalinputJSON.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
