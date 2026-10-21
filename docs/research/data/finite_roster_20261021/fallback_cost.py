"""Measure mandatory cancelled fallback against existing first-legal primitive."""
from dataclasses import replace
from pathlib import Path
import json, random, statistics, time
from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from generic_chess.core.movegen import iter_legal_actions
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.cancellation import CancellationToken

OUT=Path(__file__).resolve().parent/'fallback-cost';OUT.mkdir(exist_ok=True)
PLAN={'question':'Does complete mandatory fallback enumeration create material pre-cancelled latency in the live AlphaBeta caller, and is existing first-legal streaming a plausible lower-cost option?',
 'settings':list(zip(range(731701,731707),(6,6,8,8,10,10))),
 'roots':'uniform repr-sorted legal trajectory Random(seed), sample actual prefixes0,8,16,24; terminal prefixes retained, no refill',
 'repeats':3,'paths':['public_pre_cancelled_native','public_pre_cancelled_Core','runtime_complete_Core','public_first_legal_Core'],
 'caps':'120seconds total; no search expansion because token pre-cancelled; every root retains full history',
 'decision':'Consider a separately reviewed fallback optimization only if existing public Core cancellation median exceeds5ms on at least half of usable rules and Core first-legal median is below half that public cost on those rules. Native results independently reported. A changed deterministic fallback choice is a compatibility cost, not free equivalence.',
 'limits':'Cost feasibility only, no product change, utility/strength/incomplete-domain claim. Full-frontier bulk and first-legal are different functions; first-legal alone does not implement the public terminal/declaration contract.'}
(OUT/'plan.json').write_text(json.dumps(PLAN,indent=2)+'\n',encoding='utf-8')
start=time.perf_counter();roots=[];results=[];definitions=[];failures=[]
for seed,n in PLAN['settings']:
 if time.perf_counter()-start>=120:break
 generated=generate_game(GeneratorConfig(seed=seed,board_size=n,setup_preset='bilateral_random',allow_hybrid=True))
 c=compile_ruleset_for_execution(generated.ruleset);definitions.append({'seed':seed,'definition':ruleset_to_dict(generated.ruleset)})
 s=GameSession(c);rng=random.Random(seed)
 players={mode:AlphaBetaPlayer(c,use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=mode) for mode in (True,False)}
 token=CancellationToken();token.cancel()
 for requested in (0,8,16,24):
  while s.state.ply_count<requested and s.result.status is SessionStatus.ONGOING:
   s.submit(rng.choice(sorted(s.legal_actions(),key=repr)))
  rec=serialize_game_record(s.to_record()); key={'seed':seed,'board':n,'requested_prefix':requested,'actual_ply':s.state.ply_count,'status':s.result.status.value}
  roots.append({**key,'record':json.loads(rec)})
  if s.result.status is not SessionStatus.ONGOING: continue
  all_actions=s.legal_actions();before=s.state
  for rep in range(3):
   methods=list(PLAN['paths']);methods=methods[rep:]+methods[:rep]
   for method in methods:
    if time.perf_counter()-start>=120:continue
    t=time.perf_counter();extra={}
    if method.startswith('public_pre'):
     native=method.endswith('native');d=players[native].choose_action(s,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=1),cancel_token=token)
     elapsed=time.perf_counter()-t;action=d.action
     assert d.termination_reason=='cancelled' and d.nodes+d.qnodes==0 and d.completed_depth==0
     extra={'reason':d.termination_reason,'generated':d.legal_actions_generated,'generation_seconds':d.legal_generation_seconds,'provider_calls':d.native_legality_calls,'provider_fallbacks':d.native_legality_fallbacks}
    elif method=='runtime_complete_Core':
     rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses)
     actions=rt.legal_actions();action=sorted(actions,key=str)[0];elapsed=time.perf_counter()-t
     assert set(actions)==set(all_actions)
    else:
     action=next(iter_legal_actions(s.state,c),None);elapsed=time.perf_counter()-t
    assert action in all_actions and s.state==before
    results.append({**key,'rep':rep,'method':method,'seconds':elapsed,'action':repr(action),'legal_actions':len(all_actions),**extra})
 byrule={}
 for method in PLAN['paths']:
  values=[x['seconds'] for x in results if x['seed']==seed and x['method']==method]
  byrule[method]=statistics.median(values) if values else None
 # Append summaries per rule while retaining all requested root slots.
 failures.append({'seed':seed,'board':n,'median_seconds':byrule})
eligible=[x for x in failures if all(v is not None for v in x['median_seconds'].values())]
passing=[x for x in eligible if x['median_seconds']['public_pre_cancelled_Core']>.005 and x['median_seconds']['public_first_legal_Core']<.5*x['median_seconds']['public_pre_cancelled_Core']]
summary={'planned_roots':24,'observed_roots':len(roots),'ongoing_roots':sum(r['status']=='ongoing' for r in roots),'queries':len(results),'elapsed_seconds':time.perf_counter()-start,'rules':failures,'cost_gate':len(passing)>=len(eligible)/2 if eligible else False,'passing_rules':len(passing),'eligible_rules':len(eligible),'missing_planned_roots':24-len(roots)}
(OUT/'result.json').write_text(json.dumps({'plan':PLAN,'summary':summary,'rules':definitions,'roots':roots,'queries':results},indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2))
