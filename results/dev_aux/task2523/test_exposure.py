from results.dev_aux.task2523.exposure import rank,consistency

def test_rank_and_consistency_independent_known_vectors():
 assert rank([[1,2,3,4],[2,4,6,8],[0,0,0,0],[0,0,0,0]])==1
 assert rank([[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])==4
 same=consistency([[1,2,3,4,5]]*4)
 assert same['pairwise_free_coordinate_RMS']==0 and same['mean_pair_order_agreement']==1
 reversed_order=consistency([[1,1,2,3,4],[1,4,3,2,1]])
 assert reversed_order['mean_pair_order_agreement']==0
 assert abs(reversed_order['pairwise_free_coordinate_RMS']-5**.5)<1e-12

def test_random_prefix_is_nested_and_preserves_terminal_without_filter():
 import random,chess
 from results.dev_aux.task2492.adapters import ChessEnv
 from results.dev_aux.task2523.training_audit import outcome
 b=chess.Board();rng=random.Random(111000);at16=None
 for ply in range(64):
  if outcome(b)is not None:break
  b.push(rng.choice(sorted(b.legal_moves,key=lambda m:m.uci())))
  if ply==15:at16=b.copy(stack=True)
 assert at16 is not None and b.move_stack[:16]==at16.move_stack
 assert ChessEnv(b).record()['moves']==[m.uci()for m in b.move_stack]
 # An already terminal source has no fabricated extra moves or draw labels.
 terminal=chess.Board('7k/6Q1/6K1/8/8/8/8/8 b - - 0 1')
 assert outcome(terminal)==1 and ChessEnv(terminal).terminal()==1
