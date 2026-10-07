"""Policy tape behavior, independent of historical experiment artifacts."""
from generic_chess.benchmark.policy_tape import PolicyTape

def test_common_tape_reuses_raw_uniforms_when_legal_counts_differ():
    tape = PolicyTape("A", 1234, (0.01, 0.24, 0.51, 0.99))
    legal_counts_left = [2, 7, 3, 10]
    legal_counts_right = [5, 2, 9, 4]
    assert [tape.uniform(index) for index in range(4)] == [
        tape.uniform(index) for index in range(4)
    ]
    assert [tape.choose_index(index, count) for index, count in enumerate(legal_counts_left)] == [
        0, 1, 1, 9
    ]
    assert [tape.choose_index(index, count) for index, count in enumerate(legal_counts_right)] == [
        0, 0, 4, 3
    ]
