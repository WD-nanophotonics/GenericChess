"""Complete-input and transcript regressions for the single component witness."""
import copy,json,time
from pathlib import Path
import pytest
from scripts import leaper_design as L
from scripts.leaper_component_paths import replay
from scripts.leaper_component_forward import game
from scripts.leaper_component_qualify import qualify_game

INPUT=Path('docs/research/data/leaper_policy_cost_20261024/next-inputs.json')
PATH=[('A',1,5,None),('K',24,18,None),('A',6,2,None),('K',18,17,None),('K',0,6,None),('K',17,21,None),('K',6,12,None),('K',21,15,None),('A',5,11,None),('K',15,10,None),('A',2,6,None)]

@pytest.fixture
def world():return L.load(INPUT)['worlds'][1]

def test_original_mixed_setup_has_literal_eleven_ply_mate(world):
    result=replay(world,PATH)
    assert result['plies']==11 and result['terminal']['status']=='checkmate' and result['terminal']['winner']==0
    assert result['initial_record']['initial_setup_key']=='opposite-colors'
    assert len(result['final_record']['actions'])==11
    assert result['rows'][-1]['full_state']['ply_count']==11

def test_same_color_setup_cannot_substitute_for_that_full_history(world):
    wrong=copy.deepcopy(world);wrong['roots'][0]['record']=L.load(INPUT)['worlds'][0]['roots'][0]['record']
    with pytest.raises(AssertionError):replay(wrong,PATH)

def test_changed_rule_cannot_borrow_the_frozen_witness(world):
    wrong=copy.deepcopy(world);wrong['rule']['max_ply']=32
    with pytest.raises(AssertionError,match='frozen full RuleSet'):replay(wrong,PATH)

@pytest.fixture
def transcript(world,tmp_path):return game(world,'FLOOR',202610240701,tmp_path/'game.json',time.perf_counter()+20)

def test_full_random_and_floor_choices_roundtrip(world,transcript):
    result=qualify_game(world,transcript)
    assert result['plies']==64 and result['value']==0
    assert result['counts']['RNG_choices']==32 and result['counts']['FLOOR_choices']==32
    assert result['counts'].get('Player_queries',0)==0

@pytest.mark.parametrize('field',['seed','initial_record','state_sha256','value'])
def test_transcript_corruptions_are_rejected(world,transcript,field):
    row=copy.deepcopy(transcript)
    if field=='seed':row['seed']+=7
    elif field=='initial_record':row['initial_record'].pop('initial_setup_key')
    elif field=='state_sha256':row['queries'][3]['state_sha256']='0'*64
    else:row['value']=1
    with pytest.raises(AssertionError):qualify_game(world,row)


def test_one_ordinary_defender_invalidates_attacker_only_quadratic_bound():
    # Three A/A paths each contribute -x0*x1*x3, from two move gates
    # and King1 safety; King/King and one-ordinary paths are at most quadratic.
    from dataclasses import replace
    from scripts.leaper_rule_coordinates import template
    difference=0
    for subset in range(8):
        mask=4|sum(1<<j for i,j in enumerate((0,1,3)) if subset>>i&1)
        board=[None]*16
        for sq,owner,tid in ((0,0,'K'),(1,0,'A'),(14,1,'A'),(15,1,'K')):board[sq]=L.Piece(owner,tid,tid)
        rule=replace(template(mask,4,(0,1,15)),initial_position=tuple(tuple(board[4*y:4*y+4])for y in range(4)))
        c=L.compile_rule(rule);ss=L.GameSession(c)
        width=sum(0 if child.terminal_status.is_terminal else len(L.legal_successors(child,c))for _,child in L.legal_successors(ss.state,c))
        difference+=(-1)**(3-subset.bit_count())*width
    assert difference==-3


def test_literal_root_win_has_no_search_context_and_is_not_missing_q_policy(world,tmp_path):
    proof=replay(world,PATH);prefix=copy.deepcopy(world)
    prefix['roots'][0]['record']=proof['rows'][-2]['full_record']
    row=game(prefix,'UNIT512',202610240999,tmp_path/'immediate.json',time.perf_counter()+20)
    decision=row['queries'][0]['decision']
    assert decision['termination_reason']=='root_immediate_win'
    assert decision['completed_depth']==0 and decision['result_ordinary_qdepth'] is None
    result=qualify_game(prefix,row)
    assert result['plies']==11 and result['value']==1 and result['counts']['Player_queries']==1
