from __future__ import annotations

import hashlib
import json
import unittest

from results.dev_aux.task2618.register_learners import (
    CAP_NAMESPACE,
    derived_seed,
    family_caps,
    record_set_digest,
    training_source_index,
)


class RegisterLearnersTests(unittest.TestCase):
    def test_family_cap_map_is_reproducible_balanced_and_total(self):
        families = list(range(910001, 910033))
        seed = derived_seed(CAP_NAMESPACE)
        first, order = family_caps(families, seed)
        second, order_again = family_caps(families, seed)
        self.assertEqual(first, second)
        self.assertEqual(order, order_again)
        self.assertEqual(set(first), {str(family) for family in families})
        self.assertEqual(list(first.values()).count(20_000), 16)
        self.assertEqual(list(first.values()).count(40_000), 16)
        self.assertEqual(set(order), set(families))

    def test_family_cap_map_rejects_duplicate_or_wrong_sized_panel(self):
        with self.assertRaisesRegex(ValueError, "32 unique"):
            family_caps([1] * 32, 7)
        with self.assertRaisesRegex(ValueError, "32 unique"):
            family_caps(list(range(31)), 7)

    def test_record_digest_matches_audit_newline_canonicalization(self):
        rows = [{"record": {"moves": ["e2e4"]}}, {"record": {"moves": ["d2d4"]}}]
        serialized = b"\n".join(
            json.dumps(row["record"], sort_keys=True, separators=(",", ":")).encode()
            for row in rows
        )
        self.assertEqual(
            record_set_digest(rows),
            hashlib.sha256(serialized).hexdigest(),
        )

    def test_v2_training_manifest_reuses_the_same_panel_for_every_seed(self):
        panel_indices = list(range(120))
        for seed_index in range(4):
            self.assertEqual(
                [training_source_index(2, seed_index, root_index, panel_indices)
                 for root_index in range(120)],
                panel_indices,
            )

    def test_v1_training_manifest_maps_each_seed_to_its_disjoint_block(self):
        audited_indices = list(range(37, 517))
        for seed_index in range(4):
            mapped = [training_source_index(1, seed_index, root_index, audited_indices)
                      for root_index in range(120)]
            self.assertEqual(mapped, audited_indices[seed_index * 120:(seed_index + 1) * 120])

    def test_training_manifest_rejects_invalid_revision_or_index(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            training_source_index(3, 0, 0, [0])
        with self.assertRaisesRegex(ValueError, "out of range"):
            training_source_index(2, 0, 1, [0])


if __name__ == "__main__":
    unittest.main()
