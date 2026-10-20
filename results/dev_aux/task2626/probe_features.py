"""Capped outcome-blind feature-excitation feasibility probe for task2433 rule 0."""
from __future__ import annotations
import hashlib, json, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2606.train import prefix
from tools.local_agent.environment import require_identity

OUT=ROOT/'results/dev_aux/task2626'
RULE=ROOT/'results/dev_aux/task2433/rules-0.json'
CAP_SECONDS=120.0
FAMILY_LIMIT=10000
SEED_RULE=2433*1000

def main():
 require_identity(); OUT.mkdir(parents=True,exist_ok=True)
 path=OUT/'feature-probe-v3.json'
 with path.open('x',encoding='utf-8') as dest:
  raw=RULE.read_bytes(); comp=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
  began=time.perf_counter(); counts={'families':0,'ongoing_8ply':0,'R_hand':0,'P_on_board':0,'promoted':0,'R_hand_and_P_on_board':0,'both_R_hand_and_promoted':0,'neither_R_hand_nor_P':0}
  samples={'R_hand':None,'P_on_board':None,'promoted':None,'R_hand_and_P_on_board':None,'both_R_hand_and_promoted':None}; dimensions=None
  for family in range(FAMILY_LIMIT):
   if time.perf_counter()-began>=CAP_SECONDS: break
   env=FixedScaleSessionEnv(GameSession(comp)); prefix(env,SEED_RULE,family,8)
   counts['families']+=1
   if len(env.record().get('actions',()))!=8 or env.terminal() is not None: continue
   counts['ongoing_8ply']+=1
   pos=env.session.state.position
   rh=sum(n for hand in pos.hands for base,n in hand.counts if base=='R')
   pawn=sum(1 for p in pos.board if p is not None and p.base_type_id=='P' and p.current_type_id=='P')
   pr=sum(1 for p in pos.board if p is not None and (p.promoted or p.current_type_id!=p.base_type_id))
   dimensions=len(env.features())
   if rh: counts['R_hand']+=1; samples['R_hand']=samples['R_hand'] or family
   if pawn: counts['P_on_board']+=1; samples['P_on_board']=samples['P_on_board'] or family
   if pr: counts['promoted']+=1; samples['promoted']=samples['promoted'] or family
   if rh and pawn: counts['R_hand_and_P_on_board']+=1; samples['R_hand_and_P_on_board']=samples['R_hand_and_P_on_board'] or family
   if rh and pr: counts['both_R_hand_and_promoted']+=1; samples['both_R_hand_and_promoted']=samples['both_R_hand_and_promoted'] or family
   if not rh and not pawn: counts['neither_R_hand_nor_P']+=1
  result={'status':'CAPPED_OUTCOME_BLIND_FEATURE_FEASIBILITY','candidate':RULE.relative_to(ROOT).as_posix(),
    'candidate_sha256':hashlib.sha256(raw).hexdigest(),'prefix_plies':8,'fixed_order_seed_identity':SEED_RULE,
    'cap_seconds':CAP_SECONDS,'family_limit':FAMILY_LIMIT,'counts':counts,'first_witness_family':samples,
    'feature_dimension':dimensions,'seconds':time.perf_counter()-began,
    'selection_inputs':'Legality, complete GameSession state, terminal status, and material feature channels only; no outcome/search/model data.'}
  json.dump(result,dest,indent=2,sort_keys=True);dest.write('\n');dest.flush()
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
