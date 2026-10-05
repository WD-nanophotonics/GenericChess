"""Saved legality geometry and independent exact policy accounting."""
from fractions import Fraction as F
import hashlib,json
from pathlib import Path
from scripts.royal_interposition_values import population,moment
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'docs/research/data/shogi_royal_context_law_20261005.json'


def test_full_saved_ray_filter_including_zero_drop_contexts():
    data=json.loads(RAW.read_text());assert data['complete']
    assert len(data['rows'])==72 and data['enumerated_actions']==613
    assert data['seconds']<15 and data['public_transitions']==data['goal_queries']==data['virtual_materializations']==0
    empty=0
    for row in data['rows']:
        board=row['position']['board'];f=row['file'];r=row['rank']
        assert row['owner_checked'] and row['previous_owner_safe']
        king=board.index(next(p for p in board if p and p['owner']==0 and p['current_type_id']=='K'))
        rook=board.index(next(p for p in board if p and p['owner']==1 and p['current_type_id']=='R'))
        # Independent open ray, intersected with the saved coarse mask.
        between=set(range(king+9,rook,9));expected=between.intersection(row['coarse_drops'])
        assert expected==set(row['legal_drops'])
        assert len(row['coarse_drops'])==63 and len(expected)==7-r
        assert {a['target'] for a in row['all_actions'] if a['source'] is None}==expected
        assert any(a['actor_type']=='K' for a in row['all_actions'])
        empty+=not expected
        assert board[27+(f+5)%9]['base_type_id']=='P'
        assert row['ledger']==data['rows'][0]['ledger']
    assert empty==9


def test_shared_deadline_total_time_and_fixed_mass_accounting():
    # Enumerate the504 equally weighted coarse attempts independently of rank means.
    for law in ('geometric_half','linear_mixture'):
        p=population(law)
        expected=sum((moment(law,9-j) for r in range(8) for j in range(r+1,8)),F(0))/504
        assert p['fixed']==expected and p['legal']>p['fixed']>0
        assert p['empty_mass']==F(1,8)
        assert p['conditional_nonempty']*F(7,8)==p['legal']
        assert p['conditional_nonempty']>p['legal']
        assert p['rows'][7]['legal_resampling']==0
        assert all(p['rows'][r]['legal_resampling']<p['rows'][r+1]['legal_resampling'] for r in range(6))
    # Shared latent gamma: multiplying separate mean discounts is incorrect.
    assert moment('linear_mixture',3)!=moment('linear_mixture',1)*moment('linear_mixture',2)


def test_all_frozen_context_inputs_match():
    data=json.loads(RAW.read_text());assert data['source_hashes_unchanged']
    for p,h in data['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
