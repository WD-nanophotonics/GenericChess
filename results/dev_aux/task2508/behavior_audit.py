"""Closed endpoint first-difference/role audit; no search or new games."""
from pathlib import Path
from collections import Counter
import json,chess
OUT=Path('results/dev_aux/task2508')
def run():
 base=Path('results/dev_aux/task2507');rr=[json.loads(x)for x in(base/'games.jsonl').read_text().splitlines()];index={(r['seed'],r['family'],r['color'],r['treatment']):r for r in rr};details=[];summary=[]
 for a,b in(('plain_trained','initial'),('q2_trained','initial'),('q2_trained','plain_trained')):
  counts=Counter()
  for seed in(1977,8173,27182,31415):
   for family in range(91000,91016):
    for color in(0,1):
     x=index[(seed,family,color,a)];y=index[(seed,family,color,b)];assert x['initial_record']==y['initial_record'];xm=x['record']['moves'];ym=y['record']['moves'];n=next((i for i,(xx,yy)in enumerate(zip(xm,ym))if xx!=yy),None);rewarddelta=x['reward']-y['reward'];counts['pairs']+=1;counts['improved']+=rewarddelta>0;counts['worse']+=rewarddelta<0;counts['same_reward']+=rewarddelta==0
     if n is None:
      assert xm==ym and x['reward']==y['reward'];counts['identical_full_record']+=1;continue
     board=chess.Board(x['record']['initial'])
     for u in xm[:n]:board.push_uci(u)
     assert int(not board.turn)==color;assert chess.Move.from_uci(xm[n])in board.legal_moves and chess.Move.from_uci(ym[n])in board.legal_moves;counts['candidate_first_difference']+=1;details.append(dict(seed=seed,family=family,color=color,candidate=a,baseline=b,first_difference_full_record_ply=n,root_fen=board.fen(),candidate_action=xm[n],baseline_action=ym[n],reward_delta=rewarddelta,root_features=[len(board.pieces(t,chess.WHITE))-len(board.pieces(t,chess.BLACK))for t in(1,2,3,4,5)]))
  summary.append(dict(candidate=a,baseline=b,counts=dict(counts)))
 result=dict(status='PASS_ALL384_PAIRED_ENDPOINT_FIRST_DIFFERENCE_ROLES',comparisons=summary,details=details,scope='Allsame-seed/family/role firstdivergences occur at CANDIDATE turn with sameprefix/legalroot; fixedfoe cannotcausefirstdivergence. No search rerun/firstdifference score/PVclaim. Sourcecontrol flow plus0U actualterminalgames implies deploymentqueriesallcompleted D2, not differenttimecutoff depths; this inference isnot an independent fullsearch replay. Commonplainplayer only.')
 (OUT/'behavior-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(summary))
if __name__=='__main__':run()
