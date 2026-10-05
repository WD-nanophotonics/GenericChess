"""Finite model union controls; fixtures are not new game outcomes."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Position
from generic_chess.core.terminal import TerminalResult, TerminalStatus as T
from scripts.contact_duration_union import duration_union_choice
from scripts.native_chess_contact_intervals import contact_interval_choice, EMPTY_AUX, FINGERPRINT

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'docs/research/data/contact_duration_union_20261005.json'
GAME = NS(terminal=lambda c: c.result)


def fixture(counts, *, foreign=False):
    board = [None]*64; board[0] = Piece(0,'K','K'); board[63] = Piece(1,'K','K')
    tokens = [Piece(0,t,t) for t, n in counts.items() for _ in range(n)]
    for i, p in enumerate(tokens, 1):
        board[i] = p
    return NS(position=Position(tuple(board), ruleset_fingerprint='foreign' if foreign else FINGERPRINT,
                                aux_state=EMPTY_AUX), result=TerminalResult(T.ONGOING))


def test_union_preserves_same_choice_lost_by_outer_hull():
    r = json.loads(RAW.read_text(encoding='utf-8'))
    d = r['witnesses']['stable_union_hull_uncertain']['difference']
    first = {t:max(n,0) for t,n in zip(('Q','R','N','B','P'),d)}
    second = {t:max(-n,0) for t,n in zip(('Q','R','N','B','P'),d)}
    children = {'A':fixture(first), 'B':fixture(second)}
    result = duration_union_choice(children,GAME,owner=0,complete=True)
    assert result['complete'] and result['selected'] == 'A'
    assert result['classification'] == 'union_stable'
    assert contact_interval_choice(children,GAME,owner=0,duration='both',complete=True)['selected'] is None


def test_incomplete_child_or_table_is_never_dropped():
    for children, complete in (({'A':fixture({'Q':1}),'B':fixture({},foreign=True)},True),
                               ({'A':fixture({'Q':1}),'B':fixture({})},False)):
        result=duration_union_choice(children,GAME,owner=0,complete=complete)
        assert not result['complete'] and result['selected'] is None
        assert result['classification']=='incomplete'


def test_within_model_uncertainty_is_not_replaced_by_midpoint():
    children={'A':fixture({'N':2}),'B':fixture({'R':1,'P':1})}
    result=duration_union_choice(children,GAME,owner=0,complete=True)
    assert result['complete'] and result['selected'] is None
    assert result['classification']=='within_model_uncertainty'


def test_census_pins_scope_and_partition():
    r=json.loads(RAW.read_text(encoding='utf-8'))
    assert r['complete'] and r['comparisons']==3124 and r['seconds']<15
    assert r['category_counts']=={'stable_union_hull_stable':2884,
        'within_model_uncertainty':214,'stable_union_hull_uncertain':26}
    assert r['public_transitions']==r['goal_queries']==0
    assert sum(r['category_counts'].values())==3124
    assert r['source_hashes_unchanged']
    for p,h in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
