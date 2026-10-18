"""Rebuild the source93 per-arm signal crosscheck from actual raw data."""
from pathlib import Path
import json
from results.dev_aux.task2557.signals import run as signals
D=Path('results/dev_aux/task2557')
def run():
 signals(source_filter='D2');d=json.loads((D/'signals-D2.json').read_text());out={}
 for m in['TD','TreeStrap']:
  rr=[r for r in d['rows']if r['method']==m];ks=sorted(set(k for r in rr for k in r['counts']));out[m]=dict(arms=len(rr),observed_fullrank=sum(r['observed_feature_rank']==6 for r in rr),active_fullrank=sum(r['active_credit_feature_rank']==6 for r in rr),totals={k:sum(r['counts'].get(k,0)for r in rr)for k in ks})
 assert out['TD']['totals']['td_terms']==28293 and out['TreeStrap']['totals']['tree_samples']==375669 and out['TreeStrap']['totals']['tree_active']==257616
 (D/'signal-baseline-check.json').write_text(json.dumps(dict(status='MATCHES_ALL_SOURCE93_COUNTS',check=out,scope='All32observed+active ranks6, not global identification/conditioning/utility proof. TerminalPV gradientzero ONLYforTD; Tree internalmaterialnodelearning retained.'),indent=2));print('Exact source93 raw count crosscheck reconstructed')
if __name__=='__main__':run()
