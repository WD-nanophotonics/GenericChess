"""Bounded candidate-specific cost and material-channel feasibility, no W/L analysis."""
from __future__ import annotations
import datetime,hashlib,json,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from results.dev_aux.task2392.reader import SharedDeleteStopReader
from results.dev_aux.task2492.learning import AlphaBeta
from results.dev_aux.task2511.generic import NonScoringTerminal
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv,unchanged_model,unchanged_learner
from results.dev_aux.task2625.freeze_study import initial_vector
from tools.local_agent.environment import require_identity

OUT=ROOT/'results/dev_aux/task2626/trajectory-feasibility'
POOL=ROOT/'results/dev_aux/task2626/root-pools.json'
AUDIT=ROOT/'results/dev_aux/task2626/root-pools-audit-v2.json'
RULE='results/dev_aux/task2433/rules-0.json'
SEEDS=(1977,8173,27182,31415)
NODE_CAP=80_000
PER_ARM=NODE_CAP//len(SEEDS)
QUERY_NODES=512
DEPTH=2
H=128
HARD_SECONDS=180.0

def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,value):
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False);f.write('\n')
def promoted_count(position):return sum(1 for p in position.board if p is not None and (p.promoted or p.current_type_id!=p.base_type_id))

def main():
 require_identity()
 if OUT.exists():raise FileExistsError('trajectory feasibility is one-shot; preserve existing evidence')
 pool_raw=POOL.read_bytes();audit_raw=AUDIT.read_bytes();pool=json.loads(pool_raw);audit=json.loads(audit_raw)
 accepted_audits={
  'PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_FEATURE_AND_SPLIT_AUDIT',
  'PASS_SOURCE_HASH_FULL_HISTORY_REPLAY_MECHANISM_FEATURE_AND_SPLIT_AUDIT',
 }
 audit_pool_sha=audit.get('root_pools_sha256',audit.get('pool_sha256'))
 if audit.get('status') not in accepted_audits or audit_pool_sha!=sha(pool_raw):raise ValueError('root pool full-history audit not passed/pinned')
 rule_path=ROOT/RULE;rule_raw=rule_path.read_bytes();compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(rule_raw)))
 candidates=pool['training_roots']
 if len(candidates)<len(SEEDS):raise ValueError('insufficient frozen feasibility roots')
 source_paths=[RULE,'results/dev_aux/task2621/fixed_scale.py','results/dev_aux/task2492/learning.py',
  'results/dev_aux/task2492/episode.py','results/dev_aux/task2625/train.py',
  'results/dev_aux/task2625/freeze_study.py','generic_chess/session/session.py',
  'generic_chess/session/serialization.py','results/dev_aux/task2392/reader.py']
 pins={p:sha((ROOT/p).read_bytes()) for p in source_paths}
 OUT.mkdir(parents=True)
 write(OUT/'registration.json',{'state':'BOUNDED_FEASIBILITY_ONLY_NOT_TRAINING_REGISTRATION',
  'question':'Does the unchanged task2625 TDLeaf procedure exercise P-to-R current-type channels from the fixed candidate roots and what are candidate-specific cost rates?',
  'candidate_rule_sha256':sha(rule_raw),'pool_sha256':sha(pool_raw),'pool_audit_sha256':sha(audit_raw),
  'source_sha256':pins,'seeds':list(SEEDS),'per_seed_node_cap':PER_ARM,'total_node_cap':NODE_CAP,
  'nodes_per_query':QUERY_NODES,'depth':DEPTH,'H':H,'hard_seconds':HARD_SECONDS,
  'feature_observations':['complete GameSession record before/after every chosen action','board CURRENT and hand BASE material channel vectors','P base to R current transition count'],
  'outcomes':'Not used for selection, model targets, or strength; episodes finish censored with no terminal reward.'})
 stop=SharedDeleteStopReader(ROOT);stop();began=time.perf_counter();counts=Counter();arm_rows=[]
 with (OUT/'queries.jsonl').open('x',encoding='utf-8') as qout:
  for ix,seed in enumerate(SEEDS):
   model=None;foe=None;td=None;used=0;queries=0;promotions=0;hand_R_turns=0;active_P_turns=0;unlock_actions=0;candidate_unlock_actions=0;episodes=0
   initial_record=None;weights_initial=None
   dimension=len(candidates[0]['channels']);weights_initial=initial_vector(seed,dimension)
   model=unchanged_model(weights_initial);foe=unchanged_model([1.0]*dimension);td=unchanged_learner()
   while used<PER_ARM and time.perf_counter()-began<HARD_SECONDS:
    root=candidates[(ix+episodes)%len(candidates)]
    env=FixedScaleSessionEnv(GameSession.replay(compiled,deserialize_game_record(json.dumps(root['record']))))
    before_episode=env.record();node_at_start=used;episode_q=0
    for ply in range(H):
     stop()
     if time.perf_counter()-began>=HARD_SECONDS or used>=PER_ARM:break
     try:terminal=env.terminal()
     except NonScoringTerminal:break
     if terminal is not None:break
     actor=env.player();learner_turn=actor==episodes%2;current=model if learner_turn else foe
     record_before=env.record();state_before=env.session.state;features_before=list(env.features())
     limit=min(QUERY_NODES,PER_ARM-used)
     receipt=AlphaBeta(DEPTH,0).search(env,current,nodes=limit,seconds=min(2.,HARD_SECONDS-(time.perf_counter()-began)),
       seed=197700000+seed*1000+episodes*128+ply,cancel=stop)
     if env.record()!=record_before or env.session.state!=state_before:raise AssertionError('search mutated source history')
     used+=receipt.nodes;queries+=1;episode_q+=1
     chosen_pattern=getattr(receipt.action,'pattern_id','') if receipt.action is not None else ''
     is_hand_R_unlock=receipt.complete and chosen_pattern.endswith('_hand_R_unlocks_rook_quiet')
     unlock_actions+=int(is_hand_R_unlock);candidate_unlock_actions+=int(is_hand_R_unlock and learner_turn)
     if receipt.complete:
      if learner_turn:td.observe(model,receipt)
      env.push(receipt.action)
     features_after=list(env.features());new_prom=promoted_count(env.session.state.position)
     old_prom=promoted_count(state_before.position)
     promotions+=max(0,new_prom-old_prom)
     pos=state_before.position;rh=sum(n for hnd in pos.hands for base,n in hnd.counts if base=='R')
     pp=sum(1 for p in pos.board if p is not None and p.base_type_id=='P' and p.current_type_id=='P')
     hand_R_turns+=int(rh>0);active_P_turns+=int(pp>0)
     row={'seed':seed,'episode':episodes,'root_family':root['family'],'learner_color':episodes%2,
       'ply':ply,'actor':actor,'learner_turn':learner_turn,'record_before':record_before,
       'record_after':env.record(),'features_before':features_before,'features_after':features_after,
       'chosen_action':str(receipt.action) if receipt.complete and receipt.action is not None else None,
       'chosen_pattern_id':chosen_pattern if receipt.complete and chosen_pattern else None,
       'hand_R_unlock_action':is_hand_R_unlock,
       'complete':receipt.complete,'nodes':receipt.nodes,'seconds':receipt.seconds,
       'promotion_event_delta':max(0,new_prom-old_prom),'search_reason':receipt.reason}
     qout.write(json.dumps(row,separators=(',',':'),sort_keys=True,allow_nan=False)+'\n');qout.flush()
     if not receipt.complete:break
     env.replay()
    # No actual terminal result is read or applied to the learner. This is a
    # right-censored mechanism/cost probe, not a training endpoint.
    td.finish(model,None);episodes+=1
    if used<=node_at_start:break
   arm_rows.append({'seed':seed,'initial_weights':weights_initial,'final_weights':list(model.weights),
    'nodes':used,'queries':queries,'episodes':episodes,'promotion_events':promotions,
    'R_hand_active_turns':hand_R_turns,'live_P_active_turns':active_P_turns,
    'hand_R_unlock_actions':unlock_actions,'candidate_hand_R_unlock_actions':candidate_unlock_actions,
    'seconds':time.perf_counter()-began,'status':'NODE_CAP' if used==PER_ARM else 'TIME_OR_SEARCH_CENSORED'})
   counts['nodes']+=used;counts['queries']+=queries;counts['episodes']+=episodes;counts['promotion_events']+=promotions
   counts['hand_R_unlock_actions']+=unlock_actions;counts['candidate_hand_R_unlock_actions']+=candidate_unlock_actions
   print(json.dumps(arm_rows[-1],sort_keys=True),flush=True)
   if time.perf_counter()-began>=HARD_SECONDS:break
 result={'status':'COMPLETED_CAPPED_OUTCOME_BLIND_MECHANISM_AND_COST_FEASIBILITY',
  'candidate_rule_sha256':sha(rule_raw),'pool_sha256':sha(pool_raw),'pool_audit_sha256':sha(audit_raw),
  'arms':arm_rows,'totals':dict(counts),'nodes':counts['nodes'],'seconds':time.perf_counter()-began,
  'promotion_feature_events':counts['promotion_events'],'hand_R_unlock_actions':counts['hand_R_unlock_actions'],
  'candidate_hand_R_unlock_actions':counts['candidate_hand_R_unlock_actions'],'strength_result':False,
  'scope':'80k combined search-node cap across four seeds on one selected candidate; actual terminal labels were not used; not registered training or evaluation.'}
 write(OUT/'result.json',result);print(json.dumps({k:v for k,v in result.items() if k!='arms'},indent=2))
if __name__=='__main__':main()
