"""Regression for the observed missing actual-DRAW-zero crossing."""
from copy import copy
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.pieces import Piece
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_proof_rnb_bridge import uci
from results.dev_aux.task2126.correct_trees import corrected
from results.dev_aux.task2122.decision_cells import boundaries

def actual_counterexample():
 raw=tuple('.KbNnBk..')
 base=deserialize_ruleset(Path('results/dev_aux/task2093/rules.json').read_text(encoding='utf-8'))
 board=tuple(None if ch=='.'else Piece(int(ch.islower()),ch.upper(),ch.upper())for ch in raw)
 return GameSession(compile_ruleset_for_execution(replace(base,initial_position=tuple(tuple(board[y:y+3])for y in range(0,9,3)),initial_setup_options=())))

def test_actual_stalemate_zero_must_participate_in_region_crossings():
 s=actual_counterexample();legal={uci(a):a for a in s.legal_actions()};draw=copy(s);draw.submit(legal['a2c1']);assert draw.result.status is not SessionStatus.ONGOING and draw.result.winner is None
 alt=copy(s);alt.submit(legal['b1c1']);assert alt.result.status is SessionStatus.ONGOING
 replies=alt.legal_actions();assert len(replies)==1;alt.submit(replies[0]);assert alt.result.status is SessionStatus.ONGOING
 n=sum(1 if p.owner==0 else-1 for p in alt.state.position.board if p is not None and p.current_type_id=='N');b=sum(1 if p.owner==0 else-1 for p in alt.state.position.board if p is not None and p.current_type_id=='B');assert(n,b)==(-1,1)
 tree=dict(max=True,edges=[('a2c1',dict(terminal=0)),('b1c1',dict(coeff=[n,b]))]);points,rows=corrected(tree);assert points==['1'];assert rows[0]['first_action']=='b1c1';assert rows[1]['top_actions']==['a2c1','b1c1'];assert rows[-1]['first_action']=='a2c1'

def test_more_actor_coefficients_can_introduce_new_boundaries():
 # Scope regression: a second knight can create a half-unit crossing.
 assert Fraction(1,2)in boundaries({(-1,1),(1,0),(0,0)})
 assert boundaries({(-1,-1),(-1,0),(-1,1),(0,-1),(0,0),(0,1)})==[Fraction(1),Fraction(2)]
