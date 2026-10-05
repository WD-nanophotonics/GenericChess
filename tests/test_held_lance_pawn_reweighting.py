from fractions import Fraction as F
import json
from pathlib import Path
import pytest
from scripts.shogi_complete_board_intervals import moment
ROOT=Path(__file__).resolve().parents[1]


def test_independent_all_world_removed_fraction_and_pawn_direct_intermediate():
    delta=F(0);direct=F(0)
    for d in range(81):
        for b in range(81):
            if d==b:continue
            a={q for q in range(72) if q not in (d,b)}
            retained={q for q in a if q%9!=b%9}
            delta+=F(len(a-retained),len(a))
            if d-9 in a:direct+=F(1,len(a))
    assert delta/6480==F(575,5751)
    assert direct/6480==F(575,46008)


@pytest.mark.parametrize('law,expected',[('geometric_half',F(36073,21470400)),('linear_mixture',F(50719,120771000))])
def test_different_held_laws_still_have_a_positive_conservative_gap(law,expected):
    raw=json.loads((ROOT/'docs/research/data/shogi_random_deployment_20261005.json').read_text())
    rows={r['type']:r for r in raw['rows']}
    extra=F(rows['L']['masses']['direct'])-F(575,46008)
    assert extra==F(48317,1150200)
    bound=extra*(moment(law,2)-moment(law,3))-F(575,5751)*moment(law,2)/7
    assert bound==expected>0
    assert F(rows['L']['bounds'][law][0])<F(rows['P']['bounds'][law][1])
