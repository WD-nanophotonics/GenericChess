from dataclasses import replace
import hashlib,json
from pathlib import Path
import pytest
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.shared_contact_prefix import Profile
from scripts.nonpromotable_contact_prefix import NonpromotableContactPrefix
ROOT=Path(__file__).resolve().parents[1]


def test_preserved_failure_and_separate_cross_game_correction():
    failed=json.loads((ROOT/'docs/research/data/shared_prefix_chess_20261005.json').read_text())
    r=json.loads((ROOT/'docs/research/data/shared_prefix_chess_correction_20261005.json').read_text())
    assert not failed['complete'] and failed['rows']==[] and 'promotion pattern' in failed['error']
    assert r['complete'] and r['matches_prior_arithmetic'] and r['seconds']<15
    assert r['preprocessing']['checked_patterns']==8
    assert r['preprocessing']['geometry_candidates']==1792
    assert r['preprocessing']['raw_pattern_candidates']==6496
    assert r['preprocessing']['source_geometry_tables']==1024
    expected={'N':(20832,66472),'B':(33936,85824),'R':(53760,194432),'Q':(87696,162048)}
    for row in r['rows']:
        assert (row['direct'],row['second'])==expected[row['profile']['current']]
        assert row['direct']+row['second']+row['remaining']==row['total']==249984
    for report in (failed,r):
        assert report['public_transitions']==report['goal_queries']==report['event_materializations']==0
        for p,h in report['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h


def test_nonpromotable_extension_does_not_admit_pawn_or_shogi_promotion():
    c=compile_semantic_ruleset(build_western_chess_ruleset())
    with pytest.raises(ValueError,match='native nonpromotable'):NonpromotableContactPrefix(c,[Profile('P','P')])
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    with pytest.raises(ValueError,match='native nonpromotable'):NonpromotableContactPrefix(c,[Profile('S','S')])


def test_none_with_explicit_target_remains_unknown():
    c=compile_semantic_ruleset(build_western_chess_ruleset())
    patterns=list(c.ir.patterns)
    i=next(i for i,p in enumerate(patterns) if p.pattern_id=='sem_06_r_quiet')
    patterns[i]=replace(patterns[i],explicit_promotion_type='Q')
    with pytest.raises(ValueError,match='none cannot'):NonpromotableContactPrefix(replace(c,ir=replace(c.ir,patterns=tuple(patterns))),[Profile('R','R')])
