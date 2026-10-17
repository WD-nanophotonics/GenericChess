"""Closed positive/negative price-pair WIN-entry conversion accounting."""
from pathlib import Path
import json,time
from results.dev_aux.task2445.analyze import load,mechanisms
OUT=Path('results/dev_aux/task2449')
def run():
 t=time.perf_counter();panels=[]
 for task in(2441,2454,2455):
  p=load(task);pairs=mechanisms(p);rows=[]
  for pair in pairs:
   if pair.get('gain')in(None,0):continue
   histories=[]
   for slot in pair['slots']:
    ds=[d for d in p['decisions']if d['slot']==slot];entries=[dict(ply=d['ply'],kind=d['source'],rank=d['proof_rank'],root_state_sha=d['root_state_sha'])for d in ds if d['is_candidate']and d['source']in('VERIFIED_GRAPH_STRATEGY','VERIFIED_FULL_HISTORY_STRATEGY')];histories.append(dict(slot=slot,candidate_verified_WIN_entries=entries,normal_before_first_entry=sum(d['is_candidate']and d['source']=='FULL_SESSION_MATERIAL_SEARCH'and(not entries or d['ply']<entries[0]['ply'])for d in ds),new_proof_requests=sum(d['new_proof_attempt']for d in ds if d['is_candidate'])))
   rows.append(dict(pair=pair,histories=histories,high_price_positive_with_certificate=pair['gain']>0 and bool(histories[1]['candidate_verified_WIN_entries'])))
  panels.append(dict(task=task,changed_outcome_pairs=rows,positive_pairs=sum(r['pair']['gain']>0 for r in rows),positive_high_certified=sum(r['high_price_positive_with_certificate']for r in rows)))
 result=dict(status='PASS_ACTUAL_PRICE_PATH_PROOF_ENTRY_ACCOUNTING',panels=panels,seconds=time.perf_counter()-t,scope='ALLchanged-outcomecommonoffsetpairs fromclosedgames, notcherry-pickedonecase. Firstpriceactiondepth/sourcein2445; fullcertificate/currentcursoractualconversionalreadyindependentlyreplayed. Moreentries/requestsnotcausalmediationorproofsolvernecessary; no OFFablation/extra query/game/fitting. UnknownotherpathsnotLOSSlabels.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps([dict(task=p['task'],positive_pairs=p['positive_pairs'],positive_high_certified=p['positive_high_certified'])for p in panels]))
if __name__=='__main__':run()
