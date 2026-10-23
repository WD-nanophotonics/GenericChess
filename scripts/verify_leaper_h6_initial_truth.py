"""Portable complete-Core-domain/H6-history/path/forecast verification."""
from collections import Counter
from pathlib import Path
import argparse,json,time,hashlib,gzip
import io,contextlib

from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_h6_initial_truth import admit,history_solver
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_cooperative_truth import cooperative_distances
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_design import state_sha
from scripts.leaper_h6_score_handoff import evaluate
from scripts.leaper_h6_occupation import run as occupation_run
from scripts.leaper_h6_adjacent_pairs import analyze as adjacent_analyze
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.verify_leaper_single_parity import without_cost

DEFAULT=Path('docs/research/data/leaper_h6_initial_truth_20261023')


def verify(directory=DEFAULT):
    tick=time.perf_counter();inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');summary=load(directory/'summary.json')
    if digest(inputs)!=truth['source_digest']or digest(truth)!=summary['truth_digest']:raise ValueError('source/truth digest differs')
    rootmap={r['id']:r for r in truth['roots']};counts=Counter();source_by={r['state_sha256']:r for r in inputs['rows']}
    if len(rootmap)!=3616 or set(rootmap)!=set(source_by):raise ValueError('support changed')
    if [f['family']for f in inputs['families']if f['status']=='MU_UNAVAILABLE']!=[0]:raise ValueError('unavailable mu changed')
    for family in inputs['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        source=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,source[0]);domain=load(directory/f"domain{family['family']}.json.gz")
        expected=next(f for f in summary['families']if f['family']==family['family'])
        if digest(domain)!=expected['domain_digest']:raise ValueError('domain digest mismatch')
        positions=[decode_position(p,c.initial_position)for p in domain['positions']];indices={p:i for i,p in enumerate(positions)}
        if len(positions)!=len(indices):raise ValueError('duplicate position')
        edges=domain['edges'];actions=domain['actions'];terms={int(i):w for i,w in domain['terminals'].items()}
        if len(edges)!=len(positions)or len(actions)!=len(positions):raise ValueError('incomplete supplied domain')
        for i,pos in enumerate(positions):
            s=fresh_state(pos,c)
            if s.terminal_status.is_terminal:
                if i not in terms or terms[i]!=s.terminal_status.winner or edges[i]or actions[i]:raise ValueError('wrong static terminal')
            else:
                actual=list(legal_successors(s,c))
                if i in terms or any(ch.position not in indices for a,ch in actual):raise ValueError('domain not closed')
                if [indices[ch.position]for a,ch in actual]!=edges[i]or[action_to_dict(a)for a,ch in actual]!=actions[i]:raise ValueError('actual Core edge mismatch')
                counts['Core_edges']+=len(actual)
            counts['Core_vertices']+=1
        ds,nxt=cooperative_distances(edges,{i for i,w in terms.items()if w is not None})
        if [min(ds.get(i,7),7)for i in range(len(positions))]!=domain['negative_potential']:raise ValueError('negative reachability potential differs')
        solve,work=history_solver(edges,terms,[p.side_to_move for p in positions],lambda calls:None)
        mu=digest(sorted(r['state_sha256']for r in source))
        for sr in source:
            target=rootmap[sr['state_sha256']];s=GameSession.replay(c,deserialize_game_record(json.dumps(sr['full_record'])))
            if state_sha(s.state)!=sr['state_sha256']or target['record']!=sr['full_record']or target['mu_id']!=mu:
                raise ValueError('full initial history/mu mismatch')
            i=indices[s.state.position];v,outcomes=solve(i,6,());branches=[]
            for a,j in zip(actions[i],edges[i],strict=True):
                cv,bits=solve(j,5,(i,));branches.append(dict(action=a,wdl_bounds=[cv,cv],terminal_outcomes_bits=bits))
            if target['wdl_bounds']!=[v,v]or target['action_bounds']!=branches or target['wdl_fork']!=(len({b['wdl_bounds'][0]for b in branches})>1):
                raise ValueError('history-WDL/action-fork recurrence mismatch')
            if target['cooperative_decisive']!=(ds.get(i,7)<=6)or bool(outcomes&5)!=target['cooperative_decisive']:
                raise ValueError('history/cooperative certificate mismatch')
            for action in target['cooperative_witness']:s.submit(action_from_dict(action));counts['positive_path_edges']+=1
            if target['cooperative_decisive']and(s.result.winner is None or state_sha(s.state)!=target['terminal_state_sha']):raise ValueError('literal target path does not score')
            counts['roots']+=1
        counts['history_memo_misses']+=work()
    literal=load(directory/'literal-validation.json')
    if not literal['verified']or literal['truth_digest']!=digest(truth)or literal['source_digest']!=digest(inputs)or literal['counts']['roots']!=3616:
        raise ValueError('full-GameState control receipt not bound')
    fm=load(directory/'forecasts-manifest.json');raw=(directory/'forecasts.json.gz').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=fm['compressed_sha256']or hashlib.sha256(gzip.decompress(raw)).hexdigest()!=fm['decoded_sha256']:
        raise ValueError('published forecast bytes differ')
    scores=evaluate(truth,json.loads(gzip.decompress(raw)))
    if digest(scores)!=digest(load(directory/'scores.json.gz')):raise ValueError('strict scores differ')
    facts=load(directory/'source-fact-bindings.json.gz')
    for r in facts['facts']:
        q=rootmap[r['id']]
        if r['literal_positive']and q['cooperative_decisive']is not True:raise ValueError('one-ply source fact conflicts')
        if r['colour_negative']and q['cooperative_decisive']is not False:raise ValueError('colour proof conflicts')
        if r['literal_fork']is not None and q['wdl_fork']is not r['literal_fork']:raise ValueError('literal fork source fact conflicts')
    if len(facts['facts'])!=3616:raise ValueError('source fact support incomplete')
    occupation=load(directory/'occupation.json.gz')
    with contextlib.redirect_stdout(io.StringIO()):actual_occupation=occupation_run(directory,load(directory/'occupation-plan.json'))
    if digest(without_cost(actual_occupation))!=digest(without_cost(occupation)):raise ValueError('occupation law differs')
    control=load(directory/'occupation-validation.json')
    if not control['verified']or control['occupation_digest']!=digest(occupation)or len(control['cases'])!=33:raise ValueError('literal occupation control not bound')
    adjacency=load(directory/'adjacent-pairs.json.gz');actual_adjacent=adjacent_analyze(directory)
    if digest(without_cost(adjacency))!=digest(without_cost(actual_adjacent)):raise ValueError('onebit common-mu counterfactual differs')
    certs=load(directory/'pair-certificates.json.gz');cert_nodes=0
    if certs['adjacency_digest']!=digest(adjacency)or len(certs['rows'])!=16:raise ValueError('onebit certificates wrong pair')
    for row in certs['rows']:
        family=next(f for f in inputs['families']if f.get('fingerprint')==rootmap[row['left_id']]['fingerprint'])
        source=next(r for r in inputs['rows']if r['family']==family['family']);c=admit(family,source)
        s,cert=decode_session_certificate(c,row['left_forced_loss_certificate'])
        result=verify_session_certificate(s,cert,max_nodes=8192,seconds=30)
        if not result['verified']or cert.target!=1 or state_sha(s.state)!=row['left_id']:raise ValueError('onebit literal LOSS certificate fails')
        cert_nodes+=result['nodes']
    return dict(verified=True,counts=dict(counts),truth_digest=digest(truth),scores_digest=digest(scores),
        occupation_roots=len(occupation['rows']),onebit_certificate_nodes=cert_nodes,
        source_sha='0815ac6cb8268266c215c0cd8a24bce12bf52a66',seconds=time.perf_counter()-tick,
        scope='All target Core edges, full-history/rule/mu joins, visitedset recurrence, positive paths and actual frozenforecast scores recomputed. Stored full-GameState ExactTree receipt bound but not rerun by this fast reader; separate literal verifier reproduces that check. No oldpickle,Player or newpolicygame.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',type=Path,default=DEFAULT);cli.add_argument('--output',required=True);a=cli.parse_args();r=verify(a.directory);save(a.output,r);print(json.dumps(r))
