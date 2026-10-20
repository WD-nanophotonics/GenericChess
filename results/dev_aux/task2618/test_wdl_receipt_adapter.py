import unittest

from results.dev_aux.task2618.wdl_receipt_adapter import (
    EPISODE_ORDER, accept_proposal, charge_nodes, initial_weights, paired_interval,
    propose, reward_bounds,
)


def rows(outcomes):
    return [dict(variant=v, color=c, white_outcome=z, root_key="same-root")
            for (v, c), z in zip(EPISODE_ORDER, outcomes)]


class WDLReceiptAdapterTest(unittest.TestCase):
    def test_seeded_proposal_changes_one_non_pawn_coordinate(self):
        start = initial_weights(1977)
        first = propose(start, 1977, 3)
        self.assertEqual((start[0], first[0]), (1.0, 1.0))
        changed = [i for i, (a, b) in enumerate(zip(start, first)) if a != b]
        self.assertEqual(changed, [4])
        self.assertEqual(first, propose(start, 1977, 3))

    def test_actual_terminal_outcome_is_oriented_to_candidate_color(self):
        self.assertEqual(reward_bounds(1, 0), (1, 1))
        self.assertEqual(reward_bounds(1, 1), (-1, -1))
        self.assertEqual(reward_bounds(None, 1), (-1, 1))

    def test_accept_only_strictly_positive_complete_paired_interval(self):
        accepted, interval = accept_proposal(rows([-1, 1, -1, 1]))
        self.assertTrue(accepted)
        self.assertEqual(interval, (2.0, 2.0))
        accepted, interval = accept_proposal(rows([1, 1, -1, -1]))
        self.assertFalse(accepted)
        self.assertEqual(interval, (0.0, 0.0))

    def test_unknown_is_full_interval_and_never_assumed_draw(self):
        accepted, interval = accept_proposal(rows([0, None, 0, 0]))
        self.assertFalse(accepted)
        self.assertEqual(interval, (-0.5, 0.5))
        accepted, interval = accept_proposal(rows([None, 1, -1, None]))
        self.assertFalse(accepted)
        self.assertLessEqual(interval[0], 0)
        self.assertGreaterEqual(interval[1], 0)

    def test_partial_or_unpaired_block_cannot_update(self):
        self.assertIsNone(paired_interval(rows([1, 1, -1])))
        bad = rows([1, 1, -1, -1])
        bad[1]["root_key"] = "different-root"
        with self.assertRaisesRegex(ValueError, "share one opening root"):
            paired_interval(bad)

    def test_wrong_episode_order_rejected(self):
        bad = rows([1, 1, -1, -1])
        bad[0], bad[1] = bad[1], bad[0]
        with self.assertRaisesRegex(ValueError, "frozen four-game order"):
            paired_interval(bad)

    def test_candidate_and_foe_nodes_share_one_cap(self):
        candidate, foe = charge_nodes(40, 30, True, 20, 100)
        candidate, foe = charge_nodes(candidate, foe, False, 10, 100)
        self.assertEqual((candidate, foe), (60, 40))
        with self.assertRaisesRegex(ValueError, "combined"):
            charge_nodes(candidate, foe, False, 1, 100)


if __name__ == "__main__":
    unittest.main()
