"""Separate exposed-input cost control: proof-first versus full graph preaudit.

The first CLOSED900s batch is immutable, including its three UNKNOWN slots.
This changed method only proposes certificates from cached graphs, then checks
literal positive paths or negative Core potentials. No old graph is expanded.
"""
import argparse
import json
from pathlib import Path
import time

from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_cooperative_truth import run
from scripts.leaper_cooperative_certificate import pack,verify


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--truth',required=True);cli.add_argument('--original',required=True);cli.add_argument('--output',required=True);args=cli.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    truth=load(args.truth);old=load(args.original)
    spec=dict(question='Does checking only claim-sufficient certificates reduce actual AUX truth-validation work on the same frozen25history inputs?',
              changed_premise='The prior producer audited complete graphs before every positive claim. An existential positive needs only its actual Core path; the negative potential checker already validates closure/edges.',
              original_digest=digest(old),truth_digest=digest(truth),original_status=old['status'],original_unresolved=old['unresolved'],
              source='sandbox8f1f9e5 shared Core; own original executed-source snapshot retained',
              expected_seconds=60,caps=dict(total_seconds=900,graphs=30),
              cheaper_alternative='Retain known cooperative source suffixes/nonzero-WDL consequences without a new query; this control concerns portable proof cost on the same already exposed inputs.',
              fairness='Same cached complete graphs and25preselected histories, current shared Core. No experiment expansion, new game, E0 prediction or population claim. Ordinary concurrent machine load and warm file caches are uncontrolled.',
              stop='One new method-control run; no refill. Preserve every original UNKNOWN separately. This is not GameSession-learner/search acceleration.')
    save(out/'spec.json',spec);start=time.perf_counter()
    result=run(truth,seconds=900,audit_full_graph=False)
    save(out/'cooperative.json',result)
    assert result['selected']==old['selected']
    old_by_id={r['id']:r for r in old['rows']}
    assert all(old_by_id[r['id']]['cooperative_decisive']==r['cooperative_decisive']for r in result['rows']if r['id']in old_by_id)
    packet=pack(truth,result);save(out/'negative-certificates.json.gz',packet)
    remaining=900-(time.perf_counter()-start)
    if remaining<=0:raise RuntimeError('CONTROL_CAP_UNKNOWN')
    receipt=verify(truth,result,packet,seconds=remaining);save(out/'verification.json',receipt)
    summary=dict(status='COMPLETE'if not result['unresolved']else 'PARTIAL',seconds=time.perf_counter()-start,
                 original_complete=len(old['rows']),original_unresolved=old['unresolved'],
                 new_complete=len(result['rows']),new_unresolved=result['unresolved'],
                 original_producer_seconds=old['seconds'],original_complete_graph_positions=sum(g['positions']for g in old['graph_checks']),
                 original_complete_graph_edges=sum(g['edges']for g in old['graph_checks']),
                 new_core_verification=receipt,negative_certificates=len(packet['proofs']),
                 logical_match_on_shared_completed=True,original_unchanged=True,
                 claim='Measured AUX certificate-validation control only; no learner or player speedup, blind test or general guarantee.')
    save(out/'summary.json',summary);print(json.dumps(summary))


if __name__=='__main__':main()
