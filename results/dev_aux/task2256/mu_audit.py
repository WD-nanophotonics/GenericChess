"""TRAIN-only post-freeze exact-reference distribution diagnosis.
No DEV labels/outcomes, reward changes, root selection or optimizer access.
"""
from pathlib import Path
from collections import Counter
import json,time,hashlib
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2256')
def key(raw):return ''.join(raw[:-1])+str(raw[-1])
def run():
 assert not(OUT/'result.json').exists();start=time.perf_counter();stop=EvidenceStopReader(Path.cwd());panels=[]
 for study,labels in((2236,2216),(2251,2249)):
  inp=Path(f'results/dev_aux/task{study}/inputs.json');data=json.loads(inp.read_text());wanted={key(r['board']):r for r in data['roots']if r['split']=='TRAIN'};assert len(wanted)==32;found={};scanned=0
  with Path(f'results/dev_aux/task{labels}/labels.jsonl').open()as f:
   for line in f:
    scanned+=1
    if scanned%1024==0:stop();assert time.perf_counter()-start<180
    r=json.loads(line);k=key(r['board'])
    if k in wanted:found[k]=dict(family=wanted[k]['family'],canonical_fresh_optimal_label=r['label'],rank=r['rank'],quality=r['quality'],initial_side=r['board'][-1])
    if len(found)==32:break
  assert len(found)==32 and all(r['quality']=='EXACT_CANONICAL_FRESH_ROOT'for r in found.values());panels.append(dict(study=study,TRAIN_roots=32,DEV_labels_read=0,inputs_sha=hashlib.sha256(inp.read_bytes()).hexdigest(),exact_reference_counts=dict(Counter(r['canonical_fresh_optimal_label']for r in found.values())),rows=sorted(found.values(),key=lambda r:r['family']),scanned_labels=scanned))
 result=dict(status='PASS_POSTFREEZE_TRAIN_ONLY_REFERENCE_MU_DIAGNOSIS',panels=panels,seconds=time.perf_counter()-start,scope='All32FROZENTRAINroots/domainonly, no DEVrootlabelsorpricequeries. Exactfreshcanonicalreference labelsreadAFTERroots/protocolfrozen andtrainingstarted, inindependentprocess; neverprovidedtolearner/reward/rootselection. Describes distribution/opportunity, notpolicyvalueorerrorproof. AllDRAWdoesnotimplypricesuselessagainstfixedimperfectfoes; actualW-Ltransferstillneeded. No change/refit/capextension.')
 with(OUT/'result.json').open('x')as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status=result['status'],panels=[dict(study=p['study'],TRAIN_counts=p['exact_reference_counts'],DEV_labels_read=0)for p in panels],seconds=result['seconds'])))
if __name__=='__main__':run()
