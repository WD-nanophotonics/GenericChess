"""Synthetic-only tests for the prospective dual-layer certificate."""

from __future__ import annotations

import copy
import hashlib
import unittest

from experiments.dual_layer_coverage_certificate import (
    CertificateError, digest, issue_certificate, ruleset_coverage_complete,
    verify_certificate,
)


PREDICATE = "typed-referenced-cell-current-type-count-equals-one"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def context(*, retained_actor: bool = False) -> dict:
    actor = "actor-retained" if retained_actor else "actor-excluded"
    term = f"term:{actor}:u"
    nodes = ["event:x", term, "output:vector"]
    edges = [["event:x", term]]
    if retained_actor:
        nodes.extend([f"term:{actor}:c", f"term:{actor}:b"])
        edges.extend([
            [term, f"term:{actor}:b"],
            [f"term:{actor}:c", f"term:{actor}:b"],
            [f"term:{actor}:b", "output:vector"],
        ])
    ledger = [{
        "row_id": "row:unsupported-x",
        "variable_id": "event:x",
        "actor_ref": actor,
        "predicate_shape": PREDICATE,
        "status": "unsupported",
    }]
    return {
        "ruleset_fingerprint": _sha("synthetic-ruleset"),
        "formula_identity": "synthetic-frozen-formula-v1",
        "formula_source_sha256": _sha("formula-source-v1"),
        "output_spec": {"output_id": "requested-non-anchor-vector-v1", "nodes": ["output:vector"]},
        "retained_domain": ["actor-retained"],
        "normalization": "owner-mean; source-mean-over-frozen-support",
        "graph": {"nodes": nodes, "edges": edges},
        "ledger": ledger,
        "frozen_ledger_sha256": digest(ledger),
        "reference_accessed": False,
    }


class DualLayerCertificateTests(unittest.TestCase):
    def test_excluded_actor_stays_unsupported_but_output_is_identifiable(self):
        ctx = context(retained_actor=False)
        certificate = issue_certificate(ctx)
        self.assertFalse(ruleset_coverage_complete(ctx))
        self.assertFalse(certificate["ruleset_coverage_complete"])
        self.assertTrue(certificate["requested_output_identifiable"])
        self.assertEqual(certificate["unsupported_variables"], ["event:x"])
        self.assertTrue(verify_certificate(ctx, certificate))

    def test_same_predicate_shape_on_retained_actor_fails_closed(self):
        excluded = context(retained_actor=False)
        retained = context(retained_actor=True)
        self.assertEqual(excluded["ledger"][0]["predicate_shape"], retained["ledger"][0]["predicate_shape"])
        certificate = issue_certificate(retained)
        self.assertFalse(certificate["ruleset_coverage_complete"])
        self.assertFalse(certificate["requested_output_identifiable"])

    def test_provenance_and_scope_mutations_invalidate_old_certificate(self):
        base = context(retained_actor=False)
        certificate = issue_certificate(base)
        mutations = []
        for key, value in (
            ("formula_identity", "synthetic-frozen-formula-v2"),
            ("formula_source_sha256", _sha("formula-source-v2")),
            ("ruleset_fingerprint", _sha("other-ruleset")),
            ("retained_domain", ["actor-retained", "actor-excluded"]),
            ("normalization", "different-normalization"),
        ):
            changed = copy.deepcopy(base)
            changed[key] = value
            mutations.append(changed)
        changed_output = copy.deepcopy(base)
        changed_output["output_spec"]["output_id"] = "other-requested-output"
        mutations.append(changed_output)
        changed_graph = copy.deepcopy(base)
        changed_graph["graph"]["nodes"].append("unused:aggregate")
        changed_graph["graph"]["edges"].append(["event:x", "unused:aggregate"])
        mutations.append(changed_graph)
        for changed in mutations:
            with self.subTest(binding=digest(changed)):
                self.assertFalse(verify_certificate(changed, certificate))

    def test_new_cross_type_edge_invalidates_then_fails_identifiability(self):
        ctx = context(retained_actor=False)
        certificate = issue_certificate(ctx)
        changed = copy.deepcopy(ctx)
        changed["graph"]["nodes"].extend(["term:actor-retained:u", "term:actor-retained:b"])
        changed["graph"]["edges"].append(["event:x", "term:actor-retained:u"])
        changed["graph"]["edges"].extend([
            ["term:actor-retained:u", "term:actor-retained:b"],
            ["term:actor-retained:b", "output:vector"],
        ])
        self.assertFalse(verify_certificate(changed, certificate))
        recomputed = issue_certificate(changed)
        self.assertFalse(recomputed["requested_output_identifiable"])

    def test_dropped_or_reclassified_ledger_row_invalidates_and_cannot_be_reissued(self):
        base = context(retained_actor=False)
        certificate = issue_certificate(base)
        for mutate in (
            lambda c: c["ledger"].clear(),
            lambda c: c["ledger"][0].update(status="modeled"),
            lambda c: c["ledger"][0].update(status="zero"),
        ):
            changed = copy.deepcopy(base)
            mutate(changed)
            self.assertFalse(verify_certificate(changed, certificate))
            with self.assertRaises(CertificateError):
                issue_certificate(changed)

    def test_unfrozen_output_or_post_reference_scope_fails_closed(self):
        base = context(retained_actor=False)
        missing_output = copy.deepcopy(base)
        missing_output["output_spec"] = {"nodes": ["output:vector"]}
        with self.assertRaises(CertificateError):
            issue_certificate(missing_output)
        after_reference = copy.deepcopy(base)
        after_reference["reference_accessed"] = True
        with self.assertRaises(CertificateError):
            issue_certificate(after_reference)

    def test_missing_unsupported_variable_from_graph_fails_closed(self):
        changed = context(retained_actor=False)
        changed["graph"]["nodes"].remove("event:x")
        changed["frozen_ledger_sha256"] = digest(changed["ledger"])
        with self.assertRaises(CertificateError):
            issue_certificate(changed)

    def test_opaque_relabeling_does_not_change_the_decision(self):
        original = context(retained_actor=False)
        relabeled = copy.deepcopy(original)
        relabeled["ruleset_fingerprint"] = _sha("isomorphic-renamed-ruleset")
        relabeled["retained_domain"] = ["role-z"]
        relabeled["ledger"][0]["actor_ref"] = "role-y"
        relabeled["ledger"][0]["variable_id"] = "predicate-y"
        relabeled["frozen_ledger_sha256"] = digest(relabeled["ledger"])
        relabeled["graph"]["nodes"] = [
            "predicate-y" if n == "event:x" else
            n.replace("actor-excluded", "role-y") if "actor-excluded" in n else n
            for n in relabeled["graph"]["nodes"]
        ]
        relabeled["graph"]["edges"] = [
            ["predicate-y" if n == "event:x" else
             n.replace("actor-excluded", "role-y") if "actor-excluded" in n else n
             for n in edge]
            for edge in relabeled["graph"]["edges"]
        ]
        self.assertEqual(
            issue_certificate(original)["requested_output_identifiable"],
            issue_certificate(relabeled)["requested_output_identifiable"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
