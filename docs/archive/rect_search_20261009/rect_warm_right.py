"""Changed premise: warm TT/order history across an actual temporary right.

Reuse one public player across initial -> transform/right -> ordinary expiry
in the frozen7x5 rule. An explicit aux-sensitive control evaluator assigns100
per set global bool to owner0, plus unit material; deliberately not useful
prices. Sorted/staged, same D2/4096/5sec/q0; compare each call with a cold player
and full-width Core score. No extension of prior frozen q2 cohort.
"""
from rect_probe import *
from generic_chess.rules.schema import ruleset_from_dict

class RightEvaluator(UnitEvaluator):
 def evaluate(self,state):
  base=super().evaluate(state)
  bonus=100*sum(v for _,v in state.position.aux_state if isinstance(v,int))
  return base+(bonus if state.position.side_to_move==0 else -bonus)

def main():
 p=Path(__file__).parent;out=p/'rect-warm-right.json';assert not out.exists()
 source=json.loads((p/'rect-effect-transfer.json').read_bytes())['cases'][0]
 c=compile_ruleset_for_execution(ruleset_from_dict(source['rules']));s=GameSession(c)
 effect=next(a for a in s.legal_actions() if record_value(a)==source['effect'])
 contexts=[('initial',())];s.submit(effect)
 contexts.append(('right_set',(effect,)))
 reply=next(a for a in s.legal_actions() if 'promotion_grants_one_turn_right' not in str(a))
 s.submit(reply);contexts.append(('right_expired',(effect,reply)))
 r=dict(complete=False,declaration=__doc__,routes=record_value(contexts),cases=[])
 for staged in (False,True):
  ev=RightEvaluator();tuning=SearchTuning(use_root_tactical=False,use_staged_move_picker=staged)
  warm=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=False,tuning=tuning)
  for label,route in contexts:
   s=GameSession(c)
   for action in route:s.submit(action)
   original=s.state;counted=CountedEvaluator(ev,seconds=5,evaluations=4096)
   ref,_=reference_minimax(original,2,counted,c)
   cold=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=False,tuning=tuning)
   results=[]
   for name,player in (('warm',warm),('cold',cold)):
    dec=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=4096,max_time_seconds=5,quiescence_max_depth=0,quiescence_hard_max_depth=0))
    validate_pv(s,dec);assert s.state==original;assert dec.completed_depth==2 and dec.score==ref
    results.append(dict(kind=name,decision=record_value(dec)))
   r['cases'].append(dict(staged=staged,context=label,root=record_value(original),control_eval=ev.evaluate(original),reference=ref,leaves=counted.calls,results=results));write_record(out,r)
 r['complete']=True;r['producer_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();write_record(out,r)
 print([(z['staged'],z['context'],z['control_eval'],z['reference'],[(v['kind'],v['decision']['nodes'],v['decision']['tt_hits']) for v in z['results']]) for z in r['cases']])
if __name__=='__main__':main()
