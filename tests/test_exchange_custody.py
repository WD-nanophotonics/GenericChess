from scripts.audit_exchange_custody import audit


def test_public_legal_capture_and_drop_preserve_declared_custody_semantics():
    result = audit()
    for key, delta, before, after in [('chess_capture', 1, 0, 0), ('shogi_capture', 2, 0, 1),
                                      ('shogi_drop', 0, 1, 0)]:
        witness = result[key]
        assert witness['delta'] == delta
        assert witness['own_hand_before'] == before and witness['own_hand_after'] == after
        assert witness['terminal'] == 'ongoing'
        assert witness['complete_reply_count'] > 0
        assert witness['secured_task_success'] is (delta > 0)
    assert 0 < result['enumerated_actions'] <= 1000
