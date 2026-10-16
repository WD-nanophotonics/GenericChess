"""Capture-closed <=4piece projection of an already complete audited graph.

No new Core census, reward, fitting or online policy change. Renumber label
indices, keep every legal edge, retain identical WDL/rank/winning action.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,time
CEN=Path('results/dev_aux/task2108');LAB=Path('results/dev_aux/task2109')
def write(p,d):p.write_text(json.dumps(d,indent=2),encoding='utf-8')
def main():
 if(CEN/'states.jsonl').exists():raise RuntimeError('no rerun')
 start=time.perf_counter();parent=json.loads(Path('results/dev_aux/task2097/plan.json').read_text(encoding='utf-8'));audit=json.loads(Path('results/dev_aux/task2099/result.json').read_text(encoding='utf-8'));assert audit['status']=='PASS_COMPLETE_COVERAGE_BELLMAN_RANK_CANONICAL_HISTORY';modes=[m for m in parent['inventories']if len(m)<=2];plan=dict(status='FROZEN_STRUCTURAL_SUBSET_BEFORE_DERIVATION',rules=parent['rules'],rules_sha=parent['rules_sha'],inventories=modes,syntactic_positions=2*sum(__import__('math').perm(16,2+len(m))for m in modes),predicate='TOTALboardpieces<=4, monotoneundercapture-remove; ALLparentrowsinpredicate, noWDL/pricefilter.',parent_census='results/dev_aux/task2097',parent_labels='results/dev_aux/task2098',parent_audit='results/dev_aux/task2099',scope='Closedsubgraphsamecompletelegalfrontier/freshcanonicalWDL/rank. Derivationcostfromalreadypaid593sfullgraph; NOTmeasuredfrom-scratchCorebuildsaving. Onlineviewonly, no2105policychange.');write(CEN/'plan.json',plan)
 ids={};rows=[];h=hashlib.sha256();edges=0
 with (CEN/'states.jsonl').open('xb')as out,Path('results/dev_aux/task2097/states.jsonl').open('rb')as f:
  for i,raw in enumerate(f):
   row=json.loads(raw)
   if sum(ch!='.'for ch in row['board'][:-1])>4:continue
   assert row['inventory'][2:]in modes;ids[i]=len(rows);rows.append(row);edges+=len(row['children']);out.write(raw);h.update(raw.rstrip(b'\r\n')+b'\n')
 write(CEN/'result.json',dict(status='COMPLETE',complete_inventory_and_all_edges=True,processed=len(rows),actual_legal_edges=edges,records_sha=h.hexdigest(),scope=plan['scope'],source='Byte-exactstructuralfilterofparentCorecensus, NOTnewCoreexecution.'))
 labels=[];labelhash=hashlib.sha256();counts=Counter();maxrank=0
 with (LAB/'labels.jsonl').open('xb')as out,Path('results/dev_aux/task2098/labels.jsonl').open('rb')as f:
  for old,raw in enumerate(f):
   if old not in ids:continue
   l=json.loads(raw);i=ids[old];assert l['index']==old and l['board']==rows[i]['board'];l['index']=i
   for e in l['actions']:assert e['child']in ids;e['child']=ids[e['child']]
   counts[l['label']]+=1;maxrank=max(maxrank,l['rank']or 0);text=json.dumps(l,separators=(',',':')).encode()+b'\n';out.write(text);labelhash.update(text);labels.append(l)
 summary=dict(status='COMPLETE_CAPTURE_CLOSED_SUBSET_PENDING_INDEPENDENT_AUDIT',states=len(rows),edges=edges,maximum_decisive_rank=maxrank,ranks_over96=sum(l['rank']is not None and l['rank']>96 for l in labels),labels_sha=labelhash.hexdigest(),WDL=dict(counts),seconds=time.perf_counter()-start,scope=plan['scope']);write(LAB/'result.json',summary);write(LAB/'plan.json',dict(census=str(CEN),parent='results/dev_aux/task2098',scope=plan['scope']));print(json.dumps(summary))
if __name__=='__main__':main()
