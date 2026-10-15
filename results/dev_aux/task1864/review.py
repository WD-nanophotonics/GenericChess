"""Read exact licensed Native source; no inferred runtime ablation claim."""
from pathlib import Path
import json,zipfile,hashlib
with zipfile.ZipFile('results/dev_aux/task1831/MATERIAL_ENGINE_SOURCE_59.zip') as z:
 m=json.loads(z.read('manifest.json'));snippets=[]
 for name,ranges in {'search.cpp':[(69,72),(91,94),(425,430),(928,933),(935,945),(985,990),(1165,1169),(1188,1192),(1620,1624)],'evaluate.cpp':[(1608,1617)],'uci.cpp':[(406,436)],'types.h':[(349,368)]}.items():
  data=z.read('source/'+name);assert hashlib.sha256(data).hexdigest()==m['files'][name]['sha256'];lines=data.decode().splitlines()
  for a,b in ranges:snippets.append(dict(file=name,sha256=m['files'][name]['sha256'],first=a,last=b,text='\n'.join(lines[a-1:b])))
 result=dict(status='EXACT_PINNED_SOURCE_REVIEW',archive='results/dev_aux/task1831/MATERIAL_ENGINE_SOURCE_59.zip',upstream=m['upstream'],pin=m['upstream_pin'],binary_sha=m['original_binary_sha256'],snippets=snippets,question='Does common positive scaling preserve the mature material player, so a learned ratio alone identifies its policy?',deduction='No scale invariance is promised by this Native search: fixed score margins214/17/155/SEE and +/-1 draw jitter coexist with variable leaf/native/capture prices. Uniform scale preserves ideal material minimax ordering below clipping, but can change selective search, aspiration and fixed-node completion. Source alone does not measure action changes or attribute them uniquely to a threshold. Next freeze same fullSession states and ratios at four unit scales, samego controls, exactACK and completelegal checks; no fitting/DEVselection/default alteration.',scope='Material-only leaf does not mean scale-free search. Mate values are fixed, but all planned finite leaf sums remain far below mate bounds; no assertion of one cause without ablation.')
 with Path('results/dev_aux/task1864/source_review.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps(dict(status=result['status'],snippets=len(snippets))))
