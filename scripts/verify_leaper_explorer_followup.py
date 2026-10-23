"""Portable reader for separate explorer truth proof/bound layers."""
from pathlib import Path
import argparse
import hashlib
import time

from scripts.leaper_explorer_truth import load,save,digest,materialize,rule_targets
from scripts.leaper_explorer_supplement import verify_supplement,apply_supplement
from scripts.leaper_local_truth import verify_layer,apply_layer
from scripts.leaper_truth_views import initial_history_view
from scripts.leaper_episode_exposure import run as episodes
from scripts.verify_leaper_suffix_truth import verify as verify_suffix


def verify(directory,*,original=True):
    start=time.perf_counter();p=Path(directory).resolve();root=p.parents[3]
    manifest=load(p/'manifest.json')
    for section,base in (('files',p),('sources',root)):
        for name,expected in manifest[section].items():
            target=(base/name).resolve()
            if not target.is_relative_to(base):raise ValueError('manifest path outside declared root')
            raw=target.read_bytes()
            if expected.get('normalization')=='git_text_lf':raw=raw.replace(b'\r\n',b'\n')
            if hashlib.sha256(raw).hexdigest()!=expected['sha256']or len(raw)!=expected['bytes']:
                raise ValueError('manifest byte mismatch: '+name)
    parent=p.parent/'leaper_explorer_truth_20261023'
    parent_receipt=None
    if original:
        from scripts.verify_leaper_explorer_truth import verify as verify_parent
        parent_receipt=verify_parent(parent)
    raw=load(parent/'truth.json.gz')
    base=materialize(raw,load(parent/'cooperative.json'),load(parent/'observed-suffixes.json.gz'))
    colour=verify_supplement(raw,load(p/'supplement.json.gz'),load(p/'colour-certificate.json'))
    finite=verify_suffix(raw,load(p/'suffix-result.json'))
    mid=apply_supplement(base,load(p/'supplement.json.gz'))
    local=verify_layer(mid,load(p/'local-layer.json.gz'))
    truth=apply_layer(mid,load(p/'local-layer.json.gz'))
    summary=load(p/'summary.json')
    if summary['final_truth_digest']!=digest(truth):raise ValueError('final materialized truth mismatch')
    if initial_history_view(truth)!=load(p/'initial-view.json.gz'):raise ValueError('initial view mismatch')
    if rule_targets(truth)!=load(p/'rule-targets.json'):raise ValueError('rule target mismatch')
    observed=episodes(truth,load(parent/'source-context.json.gz'))
    if observed!=load(p/'episode-exposure.json.gz'):raise ValueError('episode event coverage mismatch')
    if summary['exact_wdl']!=sum(r['wdl_bounds'][0]==r['wdl_bounds'][1]for r in truth['roots']):
        raise ValueError('exact WDL count mismatch')
    return dict(verified=True,files=len(manifest['files']),sources=len(manifest['sources']),
                parent=parent_receipt,colour=colour,suffix=finite,local=local,
                final_truth_digest=digest(truth),episode_summaries=observed['summaries'],
                seconds=time.perf_counter()-start,
                scope='Bound source/actual Core claims and finite-case accounting only. No real E0/baseline supplied, no FP/FN measurement, generic feature/default promotion, statistical calibration or unseen-rule validation.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',default='docs/research/data/leaper_explorer_followup_20261023');cli.add_argument('--skip-original',action='store_true');cli.add_argument('--output',required=True)
    args=cli.parse_args();r=verify(args.directory,original=not args.skip_original);save(args.output,r)
    print(__import__('json').dumps({k:r[k]for k in('verified','files','sources','final_truth_digest','seconds')}))
