from fractions import Fraction
from scripts.leaper_ab_material_cells import analyze,signature


def test_exact_positive_crossings_and_open_cell_order():
    a=analyze();assert a['positive_possible_knots']==['1/2','1','2']
    lines=[tuple(x)for x in a['lines']]
    assert signature(lines,Fraction(51,100))==signature(lines,Fraction(999,1000))
    assert signature(lines,Fraction(1))!=signature(lines,Fraction(999,1000))


def test_unit_merges_the_actual_alternative_feature_values():
    a=analyze();assert any([-1,0]in group and[0,-1]in group for group in a['unit_signature'])
    assert not any([-1,0]in group and[0,-1]in group for group in a['below_unit_signature'])
