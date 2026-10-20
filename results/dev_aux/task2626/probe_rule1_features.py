"""Capped outcome-blind eight-ply feature screen for fixed-order task2433 rule 1."""
from __future__ import annotations
import hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2621.fixed_scale import FixedScaleSessionEnv
from results.dev_aux.task2606.train import prefix
from tools.local_agent.environment import require_identity
OUT=ROOT/'results/dev_aux/task2626/rule1-feature-probe-v2.json'
RULE=ROOT/'results/dev_aux/task2433/rules-1.json'
SEED_RULE=2433001;LIMIT=10000;CAP=120.0
def main():
 require_identity()
 with OUT.open('x',encoding='utf-8') as f:
  raw=RULE.read_bytes();compiled=compile_ruleset_for_execution(ruleset_from_dict(json.loads(raw)))
  began=time.perf_counter();c={'families':0,'ongoing_8ply':0,'R_hand':0,'R_board':0,'P_promoted':0,'R_hand_and_R_board':0,'all_three':0,'same_owner_all_three':0};sample={k:None for k in c if k not in ('families','ongoing_8ply')}
  for family in range(LIMIT):
   if time.perf_counter()-began>=CAP:break
   env=FixedScaleSessionEnv(GameSession(compiled));prefix(env,SEED_RULE,family,8);c['families']+=1
   if len(env.record()['actions'])!=8 or env.terminal() is not None:continue
   c['ongoing_8ply']+=1;pos=env.session.state.position
   rh=sum(n for h in pos.hands for base,n in h.counts if base=='R')
   rb=sum(1 for p in pos.board if p is not None and p.current_type_id=='R')
   pr=sum(1 for p in pos.board if p is not None and p.base_type_id=='P' and p.current_type_id=='R')
   tests={'R_hand':rh>0,'R_board':rb>0,'P_promoted':pr>0,'R_hand_and_R_board':rh>0 and rb>0,'all_three':rh>0 and rb>0 and pr>0}
   same_owner=any(sum(n for base,n in pos.hands[owner].counts if base=='R')>0 and
      any(p is not None and p.owner==owner and p.current_type_id=='R' for p in pos.board) and
      any(p is not None and p.owner==owner and p.base_type_id=='P' and p.current_type_id=='R' for p in pos.board)
      for owner in (0,1))
   tests['same_owner_all_three']=same_owner
   for k,v in tests.items():
    if v:c[k]+=1;sample[k]=sample[k] or family
  result={'status':'CAPPED_OUTCOME_BLIND_FEATURE_FEASIBILITY','rule_path':RULE.relative_to(ROOT).as_posix(),
   'rule_sha256':hashlib.sha256(raw).hexdigest(),'rule_index':1,'prefix_plies':8,'generator_seed_identity':SEED_RULE,
   'family_limit':LIMIT,'cap_seconds':CAP,'counts':c,'first_witness_family':sample,
   'selection_fields':'Complete legal histories, terminal status and current/base board or hand feature counts only; same-owner conjunction enforces the side that owns an R hand can move its promoted R. No outcomes, search values, or model weights.',
   'seconds':time.perf_counter()-began}
  json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush()
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
