"""Source-bound default-generator endpoint premise; pure coordinate model."""
import hashlib,json,math
from collections import Counter
from pathlib import Path
B=Path(__file__).parent;ROOT=B.resolve().parents[2]
files=['generic_chess/generation/config.py','generic_chess/generation/piece_generator.py',
 'generic_chess/generation/generator.py','generic_chess/rules/compiler.py','generic_chess/rules/ir.py']
sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
lists=[
 ('unique_leaps',[('leap',1,1),('leap',-1,1),('leap',0,2)]),
 ('unique_primitive_rays',[('ray',1,0),('ray',0,1),('ray',1,1)]),
 ('duplicate_leap_dedup',[('leap',0,1),('leap',0,1)]),
 ('collinear_hybrid',[('leap',0,1),('ray',0,1)])]
rows=[]
for n in (4,8):
 for owner in (0,1):
  sign=1 if owner==0 else -1
  for label,raw in lists:
   atoms=list(dict.fromkeys(raw));max_rows=0;multi=0
   for x in range(n):
    for y in range(n):
     counts=Counter()
     for kind,df,dr in atoms:
      if kind=='ray':assert math.gcd(abs(df),abs(dr))==1
      for step in (range(1,n) if kind=='ray' else (1,)):
       tx=x+sign*step*df;ty=y+sign*step*dr
       if 0<=tx<n and 0<=ty<n:counts[(tx,ty)]+=1
     max_rows=max(max_rows,max(counts.values(),default=0))
     multi+=sum(c>1 for c in counts.values())
   assert max_rows==(2 if label=='collinear_hybrid' else 1)
   assert bool(multi)==(label=='collinear_hybrid')
   rows.append(dict(board=n,owner=owner,case=label,atoms=atoms,max_rows_per_source_target=max_rows,
    duplicate_endpoint_pairs=multi))
out=dict(complete=True,source_sha256=sources,model_rows=rows,project_engine_generator_compiler_calls=0,
 source_implication='Default allow_hybrid=False generates each ordinary current type as unique leaps or unique unbounded primitive rays; mirroring deduplicates by atom value. Legacy lowering has one capture pattern per atom and incoming rows are atom endpoints. Thus each active source/current-type tuple has at most one row per target on this generated legacy-only branch while incoming metadata exists. Promotion inherits masks and does not duplicate pseudo-attack patterns.',
 changed_premises='allow_hybrid=True can retain a collinear leap and ray as distinct atoms; custom semantic actions can also add rows, as Task037/039 already execute. Source result does not cover arbitrary hand-authored pieces, bounded-ray variants, external IR mutation or metadata fallback.',
 decision='Default generated games do not supply a new row-retrieval-saving premise merely by changing seeds. DEFER default-generator caller timing for this mechanism; any renewed review must declare hybrid or semantic multirow workload and use inspected-row/rank-layout accounting.',
 limits='16small pure coordinate-model cells are not production compiler execution or search. Source implication is conditional on the reviewed generator and legacy-lowering branch, not a proof of all supported generated-domain deployment or wall-time savings.')
(B/'generator_scope.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('generator source premise: default homogeneous endpoints singleton;16coordinate cells pass;hybrid overlap retained;no project execution')
