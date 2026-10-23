from copy import deepcopy
from pathlib import Path
import pytest

from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_cooperative_certificate import verify,decode_position
from scripts.leaper_retrograde import fresh_state
from generic_chess.session.session import GameSession
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.core.transition import legal_successors


@pytest.fixture(scope='module')
def inputs():
    p=Path('docs/research/data/leaper_explorer_truth_20261023')
    return load(p/'truth.json.gz'),load(p/'cooperative.json'),load(p/'negative-certificates.json.gz')


def test_clock_certificate_needs_strictly_more_distance_than_remaining(inputs):
    t,q,p=inputs;p=deepcopy(p);proof=p['proofs'][0]
    root=next(r for r in t['roots']if r['id']==proof['id'])
    proof['potential'][proof['root_index']]=root['rule_remaining']
    with pytest.raises(AssertionError):verify(t,q,p,seconds=60)


def test_cannot_invent_repetition_barriers(inputs):
    t,q,p=inputs;p=deepcopy(p);proof=p['proofs'][0]
    proof['blocked'].append(next(i for i in range(len(proof['potential']))if i not in proof['blocked']))
    with pytest.raises(AssertionError):verify(t,q,p,seconds=60)


def test_incomplete_positive_path_is_not_a_cooperative_mate(inputs):
    t,q,p=inputs;q=deepcopy(q);p=deepcopy(p)
    row=next(r for r in q['rows']if r['cooperative_decisive']);row['witness'].pop()
    p['cooperative_digest']=digest(q)  # Pass transport integrity; test Core proof.
    with pytest.raises(AssertionError):verify(t,q,p,seconds=60)


def test_omitting_a_legal_closure_child_is_rejected(inputs):
    t,q,p=inputs;p=deepcopy(p);proof=p['proofs'][0];g=p['graphs'][proof['graph_id']]
    c=compile_rule(ruleset_from_dict(t['rules'][g['fingerprint']]));template=GameSession(c).state.position
    positions=[decode_position(raw,template)for raw in g['positions']];indices={pos:i for i,pos in enumerate(positions)}
    root=positions[proof['root_index']]
    removed=next(indices[ch.position]for _,ch in legal_successors(fresh_state(root,c),c)
                 if indices[ch.position]not in set(proof['blocked'])|{proof['root_index']})
    g['positions'].pop(removed);proof['potential'].pop(removed)
    proof['root_index']-=proof['root_index']>removed
    proof['blocked']=[i-(i>removed)for i in proof['blocked']if i!=removed]
    with pytest.raises(KeyError):verify(t,q,p,seconds=60)
