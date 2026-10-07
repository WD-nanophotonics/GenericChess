import numpy as np

from generic_chess.learning.policy_v1 import fit_semantic_policy_v1


def _example(reverse=False):
    state = np.asarray((0.0, 1.0, 0.5), dtype=np.float64)
    base = np.zeros((2, 21), dtype=np.float64)
    base[0, 0] = 1.0
    base[1, 1] = 1.0
    categories = tuple(np.asarray(values, dtype=np.int64) for values in ((0, 1), (2, 2), (2, 0), (0, 1)))
    target = np.asarray((0.8, 0.2) if not reverse else (0.2, 0.8), dtype=np.float64)
    return state, base, categories, target


def test_f111_policy_v1_roundtrip_and_deterministic_model_identity():
    examples = (_example(), _example(True))
    kwargs = dict(ruleset_fingerprint="fingerprint", corpus_config={"games": 8}, seed=1110111, type_count=3)
    model_a = fit_semantic_policy_v1(examples, **kwargs)
    model_b = fit_semantic_policy_v1(examples, **kwargs)
    assert model_a.to_dict() == model_b.to_dict()
    restored = type(model_a).from_dict(model_a.to_dict())
    assert restored.computed_model_sha256 == model_a.to_dict()["model_sha256"]
    assert np.array_equal(model_a.logits(examples[0][0], examples[0][1], examples[0][2]), restored.logits(examples[0][0], examples[0][1], examples[0][2]))
