"""Portable Core reader for the AUX explorer truth handoff, not an E0 run."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import time

from generic_chess.core.actions import action_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.leaper_design import state_sha
from scripts.leaper_explorer_truth import load,save,digest,materialize,rule_targets
from scripts.leaper_cooperative_certificate import verify as verify_cooperative
from scripts.verify_leaper_finite_outcomes import verify as verify_finite
from scripts.leaper_microgames import role_stop_requested


def verify(directory,*,finite=True):
    start=time.perf_counter();directory=Path(directory);manifest=load(directory/'manifest.json')
    for name,expected in manifest['files'].items():
        raw=(directory/name).read_bytes()
        if expected.get('normalization')=='git_text_lf':raw=raw.replace(b'\r\n',b'\n')
        assert len(raw)==expected['bytes']and hashlib.sha256(raw).hexdigest()==expected['sha256']
    truth=load(directory/'truth.json.gz');context=load(directory/'source-context.json.gz')
    cooperative=load(directory/'cooperative.json');observed=load(directory/'observed-suffixes.json.gz')
    roots={r['id']:r for r in truth['roots']};assert len(roots)==len(truth['roots'])==34037
    origins={(o['record_id'],o['ply']):r for r in roots.values()for o in r['origins']}
    compiled={fp:compile_rule(ruleset_from_dict(raw))for fp,raw in truth['rules'].items()}
    assert all(compute_fingerprint(ruleset_from_dict(truth['rules'][fp]))==fp for fp in compiled)
    stats=Counter();results={};positions={};movers={};checked=set()
    for rid,record in truth['records'].items():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        assert digest(record)==rid
        c=compiled[record['ruleset_fingerprint']]
        s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
        ps=[]
        for ply,raw_action in enumerate(record['actions']):
            r=origins[rid,ply];hid=state_sha(s.state)
            assert hid==r['id']and r['fingerprint']==c.ruleset_fingerprint and not s.state.terminal_status.is_terminal
            assert r['ply']==ply and r['rule_remaining']==c.max_ply-ply
            assert r['actors']==sum(pc is not None for pc in s.state.position.board)
            assert r['max_repetition_count']==max(n for _,n in s.state.repetition_counts)
            ps.append(s.state.position);movers[hid]=s.state.position.side_to_move
            if hid not in checked:
                if r['action_bounds']:
                    labels={action_from_dict(q['action']):q['wdl_bounds']for q in r['action_bounds']}
                    assert set(labels)==set(s.legal_actions())
                    assert len(labels)==len(r['action_bounds'])
                    assert all(lo==hi and lo in(-1,0,1)for lo,hi in labels.values())
                    assert r['wdl_bounds']==[max(v[0]for v in labels.values())]*2
                    assert r['wdl_fork']==(len({v[0]for v in labels.values()})>1)
                    if r['graph_structural_deadzone']:assert all(v==[0,0]for v in labels.values())
                    stats['bound_legal_actions']+=len(labels);stats['known_roots']+=1
                else:assert r['wdl_bounds']==[-1,1]and r['wdl_fork']is None
                checked.add(hid)
            s.submit(action_from_dict(raw_action));stats['replayed_actions']+=1
        assert s.result.status.value!='ongoing';positions[rid]=ps;results[rid]=s.result;stats['records']+=1
        for ref in context['records'][rid]:
            assert len(ref['queries'])==len(record['actions'])and ref['censor']is None
            for q in ref['queries']:
                assert q[0]==origins[rid,q[1]]['id']and q[2]==movers[q[0]]
                assert q[3]==ref['policy_by_actor'][str(q[2])]
                stats['context_reference_visits']+=1
    assert checked==set(roots)and stats['known_roots']==31390
    assert observed['truth_digest']==digest(truth)
    for q in observed['positive']:
        assert origins[q['record_id'],q['prefix_ply']]['id']==q['id']
        assert results[q['record_id']].winner is not None and results[q['record_id']].winner==q['terminal']['winner']
        assert q['suffix_length']==len(truth['records'][q['record_id']]['actions'])-q['prefix_ply']
        stats['observed_mate_suffix_roots']+=1
    mechanisms=load(directory/'mechanisms.json.gz')
    for q in mechanisms['finite_exitable_returns']:
        ps=positions[q['record_id']]
        assert ps[q['previous_ply']]==ps[q['current_ply']]
        assert origins[q['record_id'],q['previous_ply']]['id']!=q['id']
        stats['finite_exitable_returns']+=1
    for q in mechanisms['critical']:
        result=results[q['record_id']]
        payoff=0 if result.winner is None else 1 if result.winner==movers[q['id']]else-1
        assert payoff==q['eventual_mover_payoff']and q['chosen_wdl']<q['root_wdl']
        if q['child_all_future_draw']is True:
            if q['child_id']is None:assert result.winner is None
            else:assert roots[q['child_id']]['graph_structural_deadzone']is True
        stats['critical_record_actions']+=1
    material=materialize(truth,cooperative,observed)
    assert rule_targets(material)==load(directory/'rule-targets.json')
    laws=load(directory/'sampling-laws.json')['rows']
    assert [r['denominator']for r in laws]==[34037,stats['replayed_actions'],stats['context_reference_visits'],10]
    for law in laws:
        for p in law['properties'].values():
            assert p['positive']+p['negative']+p['unknown']==law['denominator']
            assert p['prevalence_bounds']==[p['positive']/law['denominator'],(p['positive']+p['unknown'])/law['denominator']]
    certificates=verify_cooperative(truth,cooperative,load(directory/'negative-certificates.json.gz'))
    finite_receipt=verify_finite(load(directory/'finite-occupation.json.gz'))if finite else None
    return dict(verified=True,counts=dict(stats),cooperative=certificates,finite=finite_receipt,
                seconds=time.perf_counter()-start,
                scope='All full-record/history/action bindings and selected cooperative certificates. Imported minimax labels are not independently re-solved; no E0 calibration/generalization or actual learner speedup established.')


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--directory',default='docs/research/data/leaper_explorer_truth_20261023');cli.add_argument('--skip-finite',action='store_true');cli.add_argument('--output',required=True);args=cli.parse_args()
    receipt=verify(args.directory,finite=not args.skip_finite);save(args.output,receipt);print(json.dumps(receipt))


if __name__=='__main__':main()
