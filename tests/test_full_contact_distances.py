import hashlib,json
from fractions import Fraction as F
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts.full_contact_distances import qualify_target_free
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.shogi_exact_contact_family import exact_board_means,exact_shogi_contact_intervals
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'
def load(name):return json.loads((DATA/f'{name}_20261005.json').read_text())

def test_full_mass_support_prefixes_and_independent_corrected_matches():
    shogi=load('shogi_full_contact_distance');qual=load('shogi_coordinate_comparison')
    assert shogi['complete'] and len(shogi['slabs'])==81 and len(shogi['rows'])==13
    assert qual['complete'] and all(row['match'] for row in qual['rows'])
    for row in shogi['rows']:assert sum(row['histogram'].values())+row['unreachable']==511920
    prefixes=load('shogi_long_ray_third')
    by_current={row['profile']['current']:row for row in shogi['rows']}
    for row in prefixes['rows']:
        actual=by_current[row['profile']['current']]['histogram']
        assert [actual[str(i)] for i in (1,2,3)]==[row[k] for k in ('direct','second','third')]
    chess=load('chess_zero_target_correction')
    assert chess['complete'] and all(row['match'] for row in chess['rows'].values())
    for row in chess['rows'].values():assert sum(row['histogram'].values())+row['unreachable']==249984
    assert chess['rows']['P']['target0_histogram']  # Promotion reaches a1; initial protocol prediction was wrong.
    assert chess['rows']['P']['unreachable']==56952
    assert not load('chess_full_pawn_distance')['complete']
    assert len(load('chess_full_pawn_distance')['slabs'])==64
    assert not load('shogi_coordinate_closure')['complete']

def test_exact_means_nested_laws_aliases_and_board_order_not_game_prices():
    for law in ('geometric_half','linear_mixture'):
        chess=exact_chess_contact_intervals(law)
        assert [mode for mode in 'QRNBP']==sorted('PNBRQ',key=lambda mode:chess['board',mode][0],reverse=True)
        assert all(lo==hi and 0<lo<=1 for lo,hi in chess.values())
        means=exact_board_means(law);order=('TR','R','TB','B','S','G','L','N','P')
        assert all(means[a]>means[b] for a,b in zip(order,order[1:]))
        assert all(means[mode]==means['G'] for mode in ('TP','TL','TN','TS'))
        boxes=exact_shogi_contact_intervals(law)
        assert len(boxes)==20 and all(lo==hi for (kind,mode),(lo,hi) in boxes.items() if kind=='board')
        assert boxes['board','TR']==(F(1),F(1))

def test_first_hit_qualification_rejects_asymmetry_and_nonprefix_rays():
    profile='actor'
    good=SimpleNamespace(area=3,closure={profile},quiet={(profile,i):() for i in range(3)},capture={(profile,i):{} for i in range(3)})
    good.quiet[profile,0]=((1,0,profile),);good.capture[profile,0]={1:(0,)}
    qualify_target_free(good)
    good.capture[profile,0]={}
    with pytest.raises(ValueError,match='equivalence'):qualify_target_free(good)
    good.quiet[profile,0]=((2,1<<1,profile),);good.capture[profile,0]={2:(1<<1,)}
    with pytest.raises(ValueError,match='prefix-closed'):qualify_target_free(good)

def test_all_new_closure_inputs_frozen_with_unchanged_caps():
    for name in ('shogi_long_ray_third','shogi_full_contact_distance','shogi_coordinate_closure',
        'shogi_coordinate_comparison','chess_full_nonpawn_distance','chess_full_pawn_distance',
        'chess_coordinate_closure','chess_zero_target_correction'):
        r=load(name);assert r['source_hashes_unchanged'] and r['public_transitions']==r['source_queries']==0
        assert r.get('cumulative_seconds',r['seconds'])<15
        for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
