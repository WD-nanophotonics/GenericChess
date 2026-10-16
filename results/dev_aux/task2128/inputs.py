"""Structural input draw only; no label/proof/fitness selector."""
from pathlib import Path
from dataclasses import replace
import json,random,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from scripts.generic_session_native_material import _load_transport
OUT=Path('results/dev_aux/task2128')
def run():
 if(OUT/'inputs.json').exists():raise RuntimeError('inputdrawalreadyfixed')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());rng=random.Random(p['seed']);actor=RoyalActor(3);seen=set();roots=[];tries=0;base=deserialize_ruleset(Path('results/dev_aux/task2093/rules.json').read_text(encoding='utf-8'));stop=_load_transport().stop_check
 while len(roots)<16 and tries<p['attempt_cap']and time.perf_counter()-start<30:
  stop(Path.cwd());tries+=1;raw=['.']*9
  for sq,ch in zip(rng.sample(range(9),6),'KkBNbn'):raw[sq]=ch
  raw=tuple(raw)+(0,)
  if raw in seen or any(actor.attacked(raw,actor.king(raw,s),1-s)or len(actor.moves(raw[:-1]+(s,)))<2 for s in(0,1)):continue
  board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in raw[:-1]);rule=replace(base,initial_position=tuple(tuple(board[y:y+3])for y in range(0,9,3)),initial_setup_options=());c=compile_ruleset_for_execution(rule);assert actor_state(GameSession(c).state)==raw;path=OUT/f'rules-{len(roots)}.json';path.write_text(serialize_ruleset(rule),encoding='utf-8');roots.append(dict(family=len(roots),root=list(raw),rules=str(path),fingerprint=c.ruleset_fingerprint));seen.update(orbit(raw))
 assert len(roots)==16
 out=dict(status='FROZEN16_STRUCTURAL_INPUTS_NO_GAME_OR_FIT',roots=roots,attempts=tries,seconds=time.perf_counter()-start,source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),prior_population_exposed=True,no_WDL_or_price_filter=True)
 (OUT/'inputs.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k!='roots'}))
if __name__=='__main__':run()
