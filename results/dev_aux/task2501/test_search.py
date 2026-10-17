import pytest,chess,random
from results.dev_aux.task2501.search import TrainingSearch
from results.dev_aux.task2492.learning import Model,AlphaBeta
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2492.test_learning import Tree

def test_plain_path_seeded_search_matches_exhaustive_minimax():
 for seed in range(60):
  rng=random.Random(seed);values=[[rng.randint(-8,8)for _ in range(2)]for _ in range(2)];t=Tree(values);r=TrainingSearch().search(t,Model([1,1]),seed=seed)
  assert r.complete and r.value==max(map(min,values)) and t.path==[]
  for s in r.samples[:-1]:assert s.lower<=min(values[int(s.phi[1]-100)])<=s.upper

def test_plain_exact_root_matches_existing_engine_with_new_order_only():
 for seed in range(8):
  e=ChessEnv();rng=random.Random(70000+seed)
  for _ in range(16):e.push(rng.choice(sorted(e.actions(),key=lambda a:a.uci())))
  before=e.record();m=Model([1,1,1,1,1]);a=TrainingSearch().search(e,m,nodes=20000,seed=seed);b=AlphaBeta(2,0).search(e,m,nodes=20000,seed=seed)
  assert a.complete and b.complete and a.value==b.value and e.record()==before

def test_qsearch_refuses_in_check_standpat_and_replays_pv_feature_value():
 # White has mate in one; other checking branches require genuine evasions.
 # Quiet checking moves beyond the frontier are deliberately NOT extended.
 e=ChessEnv(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1'));before=e.record();s=TrainingSearch(1,quiet=True);r=s.search(e,Model([1]*5),nodes=8192)
 assert r.complete and r.value==1000000 and r.pv_terminal and e.record()==before
 assert s.last_stats['check_evasion_nodes']>0 or s.last_stats['actual_terminal_nodes']>0

def test_q_resource_or_stack_abort_discards_all_partial_targets():
 e=ChessEnv(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1'));before=e.record()
 r=TrainingSearch(1,quiet=True,qstack=1).search(e,Model([1]*5),nodes=8192)
 assert not r.complete and r.action is None and r.value is None and not r.samples and e.record()==before
 r=TrainingSearch(2,quiet=True).search(e,Model([1]*5),nodes=2)
 assert not r.complete and r.nodes==2 and not r.samples and e.record()==before

def test_qsearch_has_no_extra_depth_cutoff_leaf_labels():
 e=ChessEnv();s=TrainingSearch(2,quiet=True);m=Model([1]*5);before=e.record();r=s.search(e,m,nodes=20000)
 assert r.complete and s.last_stats['qnodes']>0 and r.q_caps==0 and s.last_stats['q_truncated_leaf_labels']==0
 assert r.pv_terminal or m.raw(r.pv_phi)==r.value
 assert e.record()==before
