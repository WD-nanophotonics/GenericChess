from pathlib import Path
import sys;sys.path.insert(0,str(Path.cwd()))
import json,hashlib,time,random
from dataclasses import replace
from generic_chess.rules.serialization import deserialize_ruleset,serialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_proof_rnb_bridge import actor_state,orbit
from scripts.generic_royal_actor import RoyalActor
out=Path('results/dev_aux/task2087');out.mkdir(exist_ok=False)
p=dict(status='FROZEN_BEFORE_LABEL_BLIND_INPUT_DRAW',seed=20261016712087,question='Prospectively qualify scopedrank/negativeprovider versusoriginalPN on newactual-position-unexposedroots before another expensivepolicytest.',compositions=['BN','NN','BB'],families_per_composition=8,inputs='Uniformorderedking/extrasquares, bothowners, side0; bothkingssafe andeachside>=2legalmoves. No price/teacherlabel/rank/proof/WDL filtering. ExcludeD4/colororbitofEVERYactualposition inclosed2055and2063records. Separatecompiler-admissibleperroot rules.',future_queries='24roots xinitial/first2publiclegalplies x2targets xoriginal/compositeprovider=192total; terminalprefixesretained, no adaptivefilling. Allpositivecertificatesexistingverifier; UNKNOWNnotDRAW. Source/implementationmustpinbeforequeries.',future_budget='ONE600secincludesqualification/teacherload/96PNreferencequeries, perquery1024/1.5s/depth64 verifier16384/.5; expected180s, noextension. Fullteacherbuildcost separately charged50.27s.',now='LateINPUT_ONLY after70capsules sealed;0Native/PN/certificate/rewardgames. DirectGit addendum, notinsideclosedstudyreplay oroldcaps.',sampling_seconds_cap=90,attempt_cap=100000)
(out/'study-freeze.json').write_text(json.dumps(p,indent=2),encoding='utf-8');seen=set();start=time.perf_counter();count=0
for folder in('results/dev_aux/task2055','results/dev_aux/task2063'):
 plan=json.loads(Path(folder+'/run-plan.json').read_text());games=[json.loads(x)for x in Path(folder+'/games.jsonl').read_text().splitlines()]
 for g in games:
  rules=plan['rules']if'rules'in plan else plan['roots'][g['family']]['rules'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(rules).read_text()));record=deserialize_game_record(json.dumps(g['record']));s=GameSession(c,record.initial_setup_key);seen.update(orbit(actor_state(s.state)));count+=1
  for action in record.actions:s.submit(action);seen.update(orbit(actor_state(s.state)));count+=1
rng=random.Random(p['seed']);actor=RoyalActor(4);roots=[];attempts=0;rs=deserialize_ruleset(Path('results/dev_aux/task2054/rules.json').read_text())
for mode in p['compositions']:
 accepted=0
 while accepted<8 and attempts<p['attempt_cap']and time.perf_counter()-start<90:
  attempts+=1;owner=rng.randrange(2);raw=['.']*16;sq=rng.sample(range(16),4);raw[sq[0]]='K';raw[sq[1]]='k'
  for square,tid in zip(sq[2:],mode):raw[square]=tid.lower()if owner else tid
  raw=tuple(raw)+(0,)
  if any(actor.attacked(raw,actor.king(raw,side),1-side)for side in(0,1))or any(len(actor.moves(raw[:-1]+(side,)))<2 for side in(0,1))or raw in seen:continue
  board=[None if x=='.'else Piece(int(x.islower()),x.upper(),x.upper())for x in raw[:-1]];rule=replace(rs,initial_position=tuple(tuple(board[k:k+4])for k in range(0,16,4)),initial_setup_options=());c=compile_ruleset_for_execution(rule);assert actor_state(GameSession(c).state)==raw;path=out/f'rules-{len(roots)}.json';path.write_text(serialize_ruleset(rule),encoding='utf-8');roots.append(dict(family=len(roots),composition=mode,root=list(raw),rules=str(path),fingerprint=c.ruleset_fingerprint));seen.update(orbit(raw));accepted+=1
assert len(roots)==24
result=dict(status='COMPLETE_24_INPUT_ONLY_0_FITNESS',roots=roots,attempts=attempts,excluded_actual_positions=count,seconds=time.perf_counter()-start,new_Native=0,new_PN=0,new_certificate_calls=0,new_reward_games=0,scope=p['now']);(out/'inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items()if k!='roots'}))
