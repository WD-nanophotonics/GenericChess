"""Exact chance-control distinctions, independent of the large source graph."""
from fractions import Fraction as F
from scripts.leaper_twoa_random_headroom import shortest_dag_lower,shadow_bounds,safety_probability

def test_attacker_max_is_not_uniform_or_adversarial_defender_min():
    # First choice: one success among2 replies. Second: one among3.
    edges=[[1,2],[3,4],[3,4,5],[],[],[]];sides=[0,1,1,1,0,0]
    lower=shortest_dag_lower(edges,sides,{3})
    p=F(lower['numerators'][0],lower['base']**lower['distances'][0])
    assert p==F(1,2)
    row=shadow_bounds(edges,sides,{3},[0],[2])['rows'][0]
    assert F(row['optimal_upper'])==F(1,2)
    assert F(row['uniform_upper'])==F(5,12)

def test_prior_count3_is_arrival_only_and_mate_has_precedence():
    edges=[[1,2],[3,4],[3,4,5],[],[],[]];sides=[0,1,1,1,0,0]
    lower=shortest_dag_lower(edges,sides,{3},blocked={1,3})
    assert F(lower['numerators'][0],lower['base']**lower['distances'][0])==F(1,3)
    # Blocked source1 can still choose its current outgoing action; a future
    # arrival at1 is removed. Scoring terminal3 is still a valid success.
    assert F(lower['numerators'][1],lower['base']**lower['distances'][1])==F(1,2)

def test_repeat_omission_is_an_upper_bound_not_an_actual_value():
    # Root0 -> defender1 -> root0(failure) or mate2(success). At most3
    # success attempts fit repeat4; fourth failure would have stopped atply6.
    edges=[[1],[0,2],[]];sides=[0,1,0]
    row=shadow_bounds(edges,sides,{2},[0],[8])['rows'][0]
    assert F(row['optimal_upper'])==F(15,16)
    actual_repeat4=F(1,2)+F(1,4)+F(1,8)
    assert actual_repeat4==F(7,8)<F(row['optimal_upper'])
    lower=shortest_dag_lower(edges,sides,{2})
    assert F(lower['numerators'][0],lower['base']**lower['distances'][0])==F(1,2)

def test_clock_shorter_than_all_paths_has_zero_upper():
    edges=[[1],[2],[]];sides=[0,1,0]
    row=shadow_bounds(edges,sides,{2},[0],[1])['rows'][0]
    assert F(row['optimal_upper'])==F(row['uniform_upper'])==0

def test_safety_survival_minimizes_over_all_attacker_choices():
    # One controller move offers defender draw chance1/2, the other1/4.
    # Counting only a favorable controller choice would give a false lower.
    edges=[[1,2],[-2,-1],[-2,-1,-1,-1]];sides=[0,1,1]
    assert safety_probability(edges,sides,set(),0,2)==F(1,4)

def test_safety_arrival_draw_is_distinct_from_current_ongoing_root():
    # At source0 the defender has one draw arrival and one zero-counted exit.
    # Absorbing source0 itself would falsely declare probability1.
    assert safety_probability([[-2,-1]],[1],set(),0,1)==F(1,2)
