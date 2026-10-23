"""Separate, source-bound truth supplement; never overwrite old capped results."""
from copy import deepcopy
from pathlib import Path
from collections import Counter
import argparse

from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_colour_certificate import admit, verify as verify_colour
from scripts.leaper_explorer_truth import load,save,digest,materialize,rule_targets


def apply_supplement(truth,supplement):
    if supplement['input_digest']!=digest(truth):raise ValueError('supplement truth mismatch')
    result=deepcopy(truth);roots={r['id']:r for r in result['roots']};seen=set()
    for q in supplement['rows']:
        if q['id'] in seen:raise ValueError('duplicate supplement root')
        seen.add(q['id']);r=roots[q['id']]
        if q['fingerprint']!=r['fingerprint']:raise ValueError('supplement rule mismatch')
        if q.get('cooperative_decisive') is q.get('universal_draw'):
            raise ValueError('cooperation/universal-DRAW complement required')
        for field in ('wdl_fork','cooperative_decisive','universal_draw'):
            if field in q:
                if type(q[field])is not bool:raise ValueError('supplement truth must be boolean')
                if r[field]is not None and r[field]!=q[field]:raise ValueError('supplement contradicts known truth')
                r[field]=q[field]
        if 'wdl_bounds' in q:
            bounds=q['wdl_bounds']
            if bounds!=[0,0]or any(type(v)is not int for v in bounds)or r['wdl_bounds']not in([-1,1],[0,0]):
                raise ValueError('this supplement only adds invariant DRAW WDL')
            r['wdl_bounds']=bounds;r['action_bounds']=q['action_bounds']
            r['original_truth_basis']=r.get('truth_basis')
            r['truth_basis']='supplement_'+q['basis']
        r['cooperative_basis']=q['basis']
        r['supplement_basis']=q['basis']
    result['supplement_digest']=digest(supplement)
    return result


def build(folder,artifacts):
    p=Path(folder);a=Path(artifacts)
    original=load(p/'truth.json.gz')
    truth=materialize(original,load(p/'cooperative.json'),load(p/'observed-suffixes.json.gz'))
    cert=load(a/'colour-invariant/certificate.json')
    # Receipt is recomputed from parsed rules, complete geometry and actual
    # source replay, never accepted merely because a JSON says verified=true.
    receipt=verify_colour(original,cert)
    _,compiled=admit(original['rules'][cert['fingerprint']])
    by_id={r['id']:r for r in truth['roots']};rows=[]
    for hid in receipt['bound_histories']:
        r=by_id[hid]
        if r['wdl_bounds']==[0,0]and r['cooperative_decisive']is False:continue
        _,s=root_session(original,hid,compiled)
        actions=[dict(action=action_to_dict(ac),wdl_bounds=[0,0])for ac,_ in legal_successors(s.state,compiled)]
        rows.append(dict(id=hid,fingerprint=cert['fingerprint'],wdl_bounds=[0,0],
                   action_bounds=actions,wdl_fork=False,cooperative_decisive=False,
                   universal_draw=True,basis='colour_invariant_no_mate_draw_only_finite_terminal'))
    suffix=load(a/'suffix24/result.json')
    if suffix['spec']['source_truth_digest']!=digest(original):raise ValueError('suffix source mismatch')
    # A positive needs only the literal path. Full-set claims remain bound to
    # the independent finite-tree receipt; this materialization uses no partial.
    for q in suffix['rows']:
        if q['status']!='COMPLETE' or not q['cooperative_decisive']:continue
        r=by_id[q['id']]
        if r['cooperative_decisive']is None:
            from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
            from generic_chess.rules.schema import ruleset_from_dict
            from generic_chess.core.actions import action_from_dict
            c=compile_rule(ruleset_from_dict(original['rules'][r['fingerprint']]))
            _,s=root_session(original,r['id'],c)
            for action in q['witness']:s.submit(action_from_dict(action))
            if s.result.winner is None:raise ValueError('invalid new literal mate path')
            rows.append(dict(id=r['id'],fingerprint=r['fingerprint'],cooperative_decisive=True,
                        universal_draw=False,basis='literal_actual_history_suffix_mate',witness=q['witness']))
    supplement=dict(format='leaper-explorer-truth-supplement-v1',input_digest=digest(truth),
          original_truth_digest=digest(original),colour_certificate_digest=digest(cert),
          suffix_result_digest=digest(suffix),rows=rows,
          scope='Only separately certified new labels on the identical original histories/mu. Original failed/partial/UNKNOWN runs remain immutable; this is new evidence under a different proof premise. No E0 predictions, TRAIN starts or unseen-rule claims.')
    updated=apply_supplement(truth,supplement)
    summary=dict(rows=len(rows),new_wdl=sum('wdl_bounds'in r for r in rows),
          new_action_bindings=sum(len(r.get('action_bounds',[]))for r in rows),
          property_counts={prop:dict(Counter(str(r[prop])for r in updated['roots']))
                           for prop in ('wdl_fork','cooperative_decisive','universal_draw')},
          wdl_known=sum(r['wdl_bounds'][0]==r['wdl_bounds'][1]for r in updated['roots']),
          initial=[{k:r[k]for k in ('id','fingerprint','wdl_bounds','wdl_fork','cooperative_decisive','universal_draw')}
                   for r in updated['roots']if r['ply']==0],
          updated_truth_digest=digest(updated),colour_verification=receipt|dict(bound_histories=None,records=None))
    return supplement,updated,summary


def verify_supplement(truth,supplement,certificate):
    """Verify each incoming claim; a saved producer receipt is not authority."""
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.core.actions import action_from_dict
    if digest(truth)!=supplement['original_truth_digest']:
        raise ValueError('supplement original source mismatch')
    if digest(certificate)!=supplement['colour_certificate_digest']:
        raise ValueError('colour certificate binding mismatch')
    verified=verify_colour(truth,certificate);allowed=set(verified['bound_histories'])
    roots={r['id']:r for r in truth['roots']};compiled={};counts=Counter();seen=set()
    for q in supplement['rows']:
        if q['id']in seen:raise ValueError('duplicate supplement root')
        seen.add(q['id']);r=roots[q['id']];fp=r['fingerprint']
        if fp!=q['fingerprint']:raise ValueError('supplement fingerprint mismatch')
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        _,s=root_session(truth,q['id'],compiled[fp])
        if q['basis']=='colour_invariant_no_mate_draw_only_finite_terminal':
            if q['id']not in allowed or fp!=certificate['fingerprint']:
                raise ValueError('colour proof does not bind this root')
            if (q['wdl_bounds']!=[0,0] or any(type(v)is not int for v in q['wdl_bounds'])or q['wdl_fork']is not False or
                q['cooperative_decisive']is not False or q['universal_draw']is not True):
                raise ValueError('colour truth vector mismatch')
            actual={digest(action_to_dict(ac))for ac,_ in legal_successors(s.state,compiled[fp])}
            claimed=[digest(row['action'])for row in q['action_bounds']]
            if len(claimed)!=len(set(claimed))or set(claimed)!=actual or any(
                 row['wdl_bounds']!=[0,0]or any(type(v)is not int for v in row['wdl_bounds'])for row in q['action_bounds']):
                raise ValueError('new WDL action bindings incomplete/incorrect')
            counts['colour_roots']+=1;counts['new_action_bindings']+=len(actual)
        elif q['basis']=='literal_actual_history_suffix_mate':
            if ('wdl_bounds'in q or q['cooperative_decisive']is not True or
                q['universal_draw']is not False or len(q['witness'])>r['rule_remaining']):
                raise ValueError('literal witness claim outside scope')
            for ac in q['witness']:s.submit(action_from_dict(ac))
            if s.result.winner is None:raise ValueError('literal witness does not mate')
            counts['positive_paths']+=1;counts['positive_edges']+=len(q['witness'])
        else:raise ValueError('unknown supplement proof basis')
    return dict(verified=True,counts=dict(counts),supplement_digest=digest(supplement),
                colour=verified|dict(bound_histories=None,records=None),
                scope='Each supplementary WDL action and cooperative claim is rechecked; old partial/UNKNOWN search results are not re-executed or filled.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--folder',default='docs/research/data/leaper_explorer_truth_20261023');cli.add_argument('--artifacts',default='artifacts/explorer-followup-20261023');cli.add_argument('--output',required=True)
    args=cli.parse_args();p=Path(args.output);p.mkdir(parents=True,exist_ok=False)
    supplement,truth,summary=build(args.folder,args.artifacts)
    save(p/'supplement.json.gz',supplement);save(p/'summary.json',summary)
    save(p/'rule-targets.json',rule_targets(truth));print(__import__('json').dumps(summary))
