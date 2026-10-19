from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json
ROOT=Path('results/dev_aux')
A=ROOT/'task2609'
B=ROOT/'task2610/attempt-2'
# Inputs are byte-identical to the pre-registered plan and root panel.
assert (ROOT/'task2610/eval-plan.json').read_bytes()==(B/'eval-plan.json').read_bytes()
assert (ROOT/'task2610/root-manifest.json').read_bytes()==(B/'root-manifest.json').read_bytes()
reg=json.loads((B/'registration.json').read_text())
assert hashlib.sha256((B/'eval-plan.json').read_bytes()).hexdigest()==reg['eval_plan_sha256']
assert hashlib.sha256((B/'root-manifest.json').read_bytes()).hexdigest()==reg['root_manifest_sha256']

def panel(directory):
    p=json.loads((directory/'eval-plan.json').read_text())
    games=[json.loads(x) for x in (directory/'eval-games.jsonl').read_text().splitlines()]
    out={}
    for g in games:
        rule,seed,family,color,endpoint,_=g['slot']
        key=(rule,seed,family,color,endpoint)
        reward=g['reward']
        assert reward is None or reward in (-1,0,1)
        out[key]=reward
    assert len(out)==1536
    return p,out
p1,o1=panel(A); p2,o2=panel(B)
m1=json.loads((A/'root-manifest.json').read_text())
m2=json.loads((B/'root-manifest.json').read_text())
def root_identities(m):
    return {(int(key.split(':',1)[0]),json.dumps(record,sort_keys=True,separators=(',',':'))) for key,record in m['roots'].items()}
roots1=root_identities(m1); roots2=root_identities(m2)
assert len(roots1)==len(roots2)==64 and roots1.isdisjoint(roots2)
assert p1['rules']==p2['rules'] and p1['seeds']==p2['seeds']
assert set(o1).isdisjoint(set(o2)) # distinct family IDs make full paired keys disjoint
# Verify only root family IDs differ, and endpoints/arms match.
project=lambda o:{(r,s,c,e) for (r,s,f,c,e) in o}
assert project(o1)==project(o2)

def compare(out,left,right,rule=None):
    diffs=[]; unknown=0
    for (r,s,f,c,e),a in out.items():
        if e!=left or (rule is not None and r!=rule): continue
        b=out[(r,s,f,c,right)]
        if a is None or b is None:
            diffs.append((-2,2)); unknown+=1
        else: diffs.append((a-b,a-b))
    lo=sum(x[0] for x in diffs); hi=sum(x[1] for x in diffs); n=len(diffs)
    return {'n':n,'unknown_pairs':unknown,'mean_bound':[lo/n,hi/n]}
rows=[]
for label, out in [('task2609',o1),('task2610',o2)]:
    for contrast,left,right in [('TD95-initial','TD95','initial'),('LocalLambda-initial','LocalLambda','initial'),('LocalLambda-TD95','LocalLambda','TD95')]:
        rows.append({'panel':label,'contrast':contrast,**compare(out,left,right)})
report={
 'task':'DEV_AUX2610',
 'attempt2_audit':json.loads((B/'audit.json').read_text()),
 'panels':rows,
 'root_identity_audit':{'task2609_roots':len(roots1),'task2610_roots':len(roots2),'exact_rule_full_history_intersections':len(roots1 & roots2)},
 'per_rule_local_lambda_vs_td95':[
  {'panel':label,'rule':r,**compare(out,'LocalLambda','TD95',r)}
  for label,out in [('task2609',o1),('task2610',o2)] for r in p1['rules']
 ],
 'limits':['Two finite pre-outcome-selected 64-root panels; not a random-sample confidence interval.','Four frozen parameter seeds are crossed with each root in each panel, not independent seed replication.','Descendant-state/history nonoverlap and broad rule/population transfer are not established.','99 UNKNOWN outcomes in the new panel remain censored; each affected pair widens to [-2,+2].','LocalLambda vs TD95 spans zero in both panels; the learner-method contrast is unresolved.'],
 'hashes':{
  'task2609_audit_sha256':hashlib.sha256((A/'audit.json').read_bytes()).hexdigest(),
  'attempt2_eval_plan_sha256':reg['eval_plan_sha256'],
  'attempt2_root_manifest_sha256':reg['root_manifest_sha256'],
  'attempt2_audit_sha256':hashlib.sha256((B/'audit.json').read_bytes()).hexdigest(),
 }
}
(ROOT/'task2610/panel-comparison.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
lines=['# DEV_AUX task2610 — Second root-panel result','',
       '## Result and audit','',
       'The frozen task2606 models were evaluated on a second outcome-blind, pre-classified root panel. Attempt 2 completed all 1,536 registered slots in 702.419 seconds (2,201,293 search nodes; 39,958 queries), below the frozen 1,200-second cap. Independent slot/query/history replay passed: 64 distinct full start histories, 1,437 actual terminals and 99 censored UNKNOWN horizons; all 39,958 searches completed. Attempt 1 remains a preserved pre-output schema failure; attempt 2 changes only the required registration hash alias, not models, roots, plan, conditions, or cap.','',
       'Endpoint totals for task2610: initial 234W/8D/244L/26 UNKNOWN; TD95 297W/2D/174L/39 UNKNOWN; LocalLambda 299W/5D/174L/34 UNKNOWN.','Provenance reconciliation PASS: attempt 2 binds the preserved attempt-1 failure and unchanged model/plan/root hashes; all 23 source pins match. See provenance-audit.json.','',
       '## Paired finite-panel bounds','',
       '| Panel | TD95 − initial | LocalLambda − initial | LocalLambda − TD95 |','|---|---:|---:|---:|']
for lab in ['task2609','task2610']:
    r={x['contrast']:x for x in rows if x['panel']==lab}
    def fmt(x): return f"[{x['mean_bound'][0]:+.4f}, {x['mean_bound'][1]:+.4f}] (UNKNOWN pairs {x['unknown_pairs']}/{x['n']})"
    lines.append(f"| {lab} | {fmt(r['TD95-initial'])} | {fmt(r['LocalLambda-initial'])} | {fmt(r['LocalLambda-TD95'])} |")
lines += ['', 'LocalLambda-minus-initial has positive conservative lower bounds in both panels. TD95-minus-initial is positive on the second panel, but its first-panel bound includes zero. LocalLambda-minus-TD95 includes zero in both panels, so the learner-method contrast remains unresolved and there is no reproduced ranking. These are paired finite-panel bounds, not confidence intervals or independent replicates.', '', '## Reproducibility artifacts','',
          'The exact query/game streams are retained locally and published as deterministic gzip files. compressed-streams.json records original/archive sizes and SHA-256; both archives decompress byte-for-byte, and credential-pattern scans pass. Cross-task archive verification reproduced task2606/task2609 archive hashes and decompressed originals; see archive-verification.json.','',
          '| Stream | Rows | Raw bytes | Gzip bytes | Gzip SHA-256 |','|---|---:|---:|---:|---|',
          '| eval-queries | 39,958 | 237,337,652 | 3,276,835 | e9132bae4390b44c6e2d48de4bbead169545640c7ba716cbe45309b2036ae45a |',
          '| eval-games | 1,536 | 4,181,646 | 118,677 | a8750001aa0b36b8bec15c4fb1a3a9bbfe7adc9c4c971352cad9b6d487c9e264 |',
          '', '## Scope and preserved limitations','',
          'task2609 and task2610 use disjoint exact rule-plus-full-history roots (64 each; zero intersections), while each panel crosses the same frozen model seeds across roots. The panel comparison is a root-sensitivity check on one frozen trained model set, not seed replication, a descendant-history holdout, or population/generalization evidence. Do not select the more favorable panel. The 99 new UNKNOWNs remain censored, never draws.', '',
          'Attempt 1 failure, registration repair, both frozen root panels, complete JSONL streams, and independent audits remain separate evidence. No engine defaults, UI, primary checkout, or other role state changed.', '',
          'Machine-readable panel table and audit hashes: `results/dev_aux/task2610/panel-comparison.json`. Attempt-2 replay audit: `results/dev_aux/task2610/attempt-2/audit.json`.']
(ROOT/'task2610/REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# Correct the inherited task2609 wording in the adapted auditor's generated report.
r=(B/'REPORT.md').read_text(encoding='utf-8')
r=r.replace('This corrected registration explicitly includes the four-ply prefix omitted from task2608.','The frozen four-ply prefix and root manifest are byte-identical to the registered plan.').replace('This preserves the failed first attempt and schema-only correction as separate evidence. It evaluates the already frozen task2606 models on exact-start-history-disjoint roots; no model or parameter selection was performed using these outcomes. UNKNOWN was not converted to a draw.','This is attempt 2 after a schema-only registration repair; attempt 1 remains a preserved pre-output failure. The frozen task2606 models were evaluated on the second exact-start-history-disjoint root panel; no model or parameter selection was performed using these outcomes. UNKNOWN was not converted to a draw.').replace('The 93 UNKNOWN outcomes','The 99 UNKNOWN outcomes')
(B/'REPORT.md').write_text(r,encoding='utf-8')
print(json.dumps(report,indent=2))
