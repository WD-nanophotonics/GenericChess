from scripts.leaper_ab_history_barrier import rank_avoidance


def test_winner_can_use_an_alternative_strict_rank_path():
    edges=[[1,2],[3],[3],[]];sides=[0,1,1,0];ranks={0:2,1:1,2:1,3:0}
    rank,policy,_=rank_avoidance(edges,sides,{3:0},ranks,{1},0)
    assert rank==2 and policy[0]==[2] and policy[2]==[3]


def test_defender_barrier_is_unknown_and_not_a_draw_label():
    edges=[[1,2],[3],[3],[]];sides=[1,0,0,0];ranks={0:2,1:1,2:1,3:0}
    rank,policy,_=rank_avoidance(edges,sides,{3:0},ranks,{1},0)
    assert rank is None and policy=={}


def test_original_terminal_precedence_and_non_decreasing_path_rejection():
    assert rank_avoidance([[]],[0],{0:0},{0:0},{0},0)[0]==0
    rank,policy,_=rank_avoidance([[1],[2],[]],[0,0,0],{2:0},{0:1,1:1,2:0},set(),0)
    assert rank is None and policy=={}
