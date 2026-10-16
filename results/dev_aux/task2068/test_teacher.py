from pathlib import Path
from dataclasses import replace
import json
import pytest
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.movement import LeapAtom
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2063.campaign import evaluator
@pytest.fixture(scope='module')
def teacher():return CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059')
def session():return GameSession(compile_ruleset_for_execution(deserialize_ruleset(Path('results/dev_aux/task2063/rules-0.json').read_text())))
def test_fresh_label_but_history_unknown(teacher):
 s=session();r=teacher.label(s);assert r.quality=='EXACT_CANONICAL_FRESH_ROOT'and r.value in(-1,0,1)and r.optimal_actions
 s.submit(s.legal_actions()[0]);r=teacher.label(s);assert r.quality=='UNKNOWN'and r.value is None and r.reason=='noncanonical_history_not_qualified'
def test_changed_execution_not_old_label(teacher):
 rs=deserialize_ruleset(Path('results/dev_aux/task2064/rules.json').read_text());s=GameSession(compile_ruleset_for_execution(rs));r=teacher.label(s);assert r.quality=='UNKNOWN'and r.value is None and r.reason=='execution_rules_not_qualified'
def test_evaluator_target_perspective_is_antisymmetric():
 s=session();models=json.loads(Path('results/dev_aux/task2060/models.json').read_text())
 for w in models.values():
  f=evaluator(w);assert f(s.state.position,0)==-f(s.state.position,1)
