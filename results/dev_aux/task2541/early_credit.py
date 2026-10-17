"""Bounded actual closed-game sign/credit preflight for the new trainer."""
from pathlib import Path
from math import tanh,isclose
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2529.training_audit import terminal
D=Path('results/dev_aux/task2539');O=Path('results/dev_aux/task2541')
def run():
 p=json.loads((D/'plan.json').read_text());closed={}
 for raw in(D/'games.jsonl').read_bytes().splitlines():
  if not raw.endswith(b'}'):continue
  r=json.loads(raw)
  if r['method']=='TD'and r['color']==1 and r['outcome']is not None and r['observed']:closed[r['gameid']]=r
 qs={};case=None
 for raw in(D/'queries.jsonl').open():
  try:q=json.loads(raw)
  except json.JSONDecodeError:break
  if q['gameid']not in closed:continue
  qs.setdefault(q['gameid'],[]).append(q);e=closed[q['gameid']]
  if len(qs[q['gameid']])==e['queries']and q['actor']==0:case=e;break
 assert case is not None,'No actual sign-control case yet; no invented data'
 rr=qs[case['gameid']];w=case['initial_weights'];obs=[q for q in rr if q['observed_by_TD']];assert obs and all(q['actor']==1 and q['weights']==w for q in obs)and not rr[-1]['observed_by_TD'];pred=[tanh(q['value']/10)for q in obs];grads=[[0.]*6 if q['pv_terminal']else[x*(1-v*v)/10 for x in q['pv_phi']]for q,v in zip(obs,pred)];errors=[pred[i+1]-pred[i]for i in range(len(pred)-1)]+[case['outcome']-pred[-1]];future=0;delta=[0.]*6
 for i in reversed(range(len(pred))):future=errors[i]+p['lam']*future;delta=[x+future*g for x,g in zip(delta,grads[i])]
 assert all(isclose(x,y+p['eta']*z,rel_tol=1e-10,abs_tol=1e-12)for x,y,z in zip(case['after_TD_weights'],w,delta));assert case['reward']==-case['outcome']
 compiled=compile_ruleset(ruleset_from_dict(json.loads(Path('results/dev_aux/task2525',f"rules-{case['generator_seed']}.json").read_text())));session=GameSession.replay(compiled,deserialize_game_record(json.dumps(case['record'])));assert terminal(session)==case['outcome']
 out=dict(status='PASS_ACTUAL_NEW_TRAINER_BLACK_TD_WHITE_TERMINAL_CREDIT',gameid=case['gameid'],rule=case['generator_seed'],seed=case['seed'],family=case['family'],candidate_TD_observations=len(obs),last_actual_actor=rr[-1]['actor'],white_terminal=case['outcome'],black_utility=case['reward'],record_sha=hashlib.sha256(json.dumps(case['record'],sort_keys=True).encode()).hexdigest(),scope='FIRSTclosedactualblackTDgame endingonwhitefoeturn withpriorcandidateobservations, diagnosticselectiononly/notstrength. Candidatewhiteorientation unchanged; no extra learnersearch; entireepisodeupdateindependentlyreconstructed/fullpublicreplay. Livejournalreadstopsatclosedgame, notallfuturequeries.')
 (O/'early-credit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
