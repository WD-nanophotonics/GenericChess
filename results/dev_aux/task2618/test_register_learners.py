from __future__ import annotations

import hashlib
import json
import unittest

from results.dev_aux.task2618.register_learners import (
    CAP_NAMESPACE,
    derived_seed,
    family_caps,
    record_set_digest,
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


if __name__ == "__main__":
    unittest.main()
