"""Saved coarse deployment population and independent mask/direct controls."""
from fractions import Fraction as F
import hashlib,json
from pathlib import Path
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.shogi_complete_board_intervals import board_intervals,moment
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shogi_random_deployment_20261005.json'


def rows():return {r['type']:r for r in json.loads(RAW.read_text())['rows']}


def test_saved_full_mass_bounds_cost_and_frozen_pins():
    r=json.loads(RAW.read_text());assert r['complete'] and r['seconds']<15
    assert r['empty_drop_worlds']==0 and len(r['rows'])==7
    assert r['public_transitions']==r['goal_queries']==r['event_materializations']==0
    for row in r['rows']:
        assert sum(F(v) for v in row['masses'].values())==1
        assert sum(row['drop_set_sizes'].values())==81*80*7
        for bounds in row['bounds'].values():assert 0<F(bounds[0])<=F(bounds[1])<1
    for p,h in r['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h


def test_actual_drop_mask_coordinates_and_pawn_nifu_contract():
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    for owner in (0,1):
        for t in ('P','L','N','S','G','B','R'):
            cutoff=7 if t=='N' else 8 if t in ('P','L') else 9
            assert c.support.drop_allowed[t][owner]==tuple((q//9 if owner==0 else 8-q//9)<cutoff for q in range(81))
    p=next(p for p in c.ir.patterns if p.name=='standard_drop_contract')
    assert len(p.guards)==1 and len(p.postconditions)==2
    g=p.guards[0]
    assert g.location=='board' and g.promoted=='no' and g.compare_field=='base'
    assert g.spatial.kind=='same_file' and g.comparison=='eq' and g.value==0


def test_independent_pawn_direct_mass_includes_nifu_and_variable_denominators():
    total=F(0)
    for d in range(81):
        q=d-9
        for b in range(81):
            if d==b:continue
            for pawn_blocker,weight in ((False,6),(True,1)):
                allowed={s for s in range(72) if s not in (d,b) and (not pawn_blocker or s%9!=b%9)}
                if q in allowed:total+=F(weight,len(allowed))
    r=rows()
    assert total/(81*80*7)==F(r['P']['masses']['direct'])
    assert F(r['P']['masses']['zero'])==F(6,7)*F(r['L']['masses']['zero'])


def test_unrestricted_population_identity_uses_shifted_deadline_moments():
    r=rows()
    board=board_intervals('geometric_half')
    for t in ('S','G','B','R'):
        assert tuple(F(x) for x in r[t]['bounds']['geometric_half'])==tuple(x/2 for x in board[t])
    for law in ('geometric_half','linear_mixture'):
        exact=(99360*moment(law,2)+409536*moment(law,3)+3024*moment(law,4))/511920
        assert tuple(F(x) for x in r['R']['bounds'][law])==(exact,exact)
    assert F(r['R']['bounds']['linear_mixture'][0])!=board_intervals('linear_mixture')['R'][0]*moment('linear_mixture',1)
