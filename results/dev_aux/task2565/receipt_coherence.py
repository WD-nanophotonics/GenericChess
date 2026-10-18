"""ALL complete root targets must equal their selected PV leaf's material/terminal."""
from pathlib import Path
from math import isfinite
from collections import Counter
import json,time
D=Path('results/dev_aux/task2565')
def run():
 began=time.perf_counter();rows={};total=Counter()
 for domain,name in [('chess','queries.jsonl'),('generic','queries.jsonl'),('chess','eval-queries.jsonl'),('chess-curve','eval-queries.jsonl'),('generic','eval-queries.jsonl')]:
  path=D/domain/name;c=Counter()
  for l in path.open():
   q=json.loads(l);c['queries']+=1;c['nodes']+=q['nodes'];assert q['nodes']>=0
   if q['complete']:
    assert q['nodes']>0 and isfinite(q['value'])and all(map(isfinite,q['weights']))
    if q['pv_terminal']:assert q['pv_phi']is None and q['value']in(-1000000.,0.,1000000.);c['terminal_PV']+=1
    else:
     assert len(q['pv_phi'])==len(q['weights']);raw=sum(x*w for x,w in zip(q['pv_phi'],q['weights']));assert raw==q['value'],(str(path),q.get('gameid',q.get('slot')),q['ply'],raw,q['value']);c['material_PV']+=1
   else:
    assert q['value']is None and q['pv_phi']is None and not q['pv_terminal'];c['failed_queries']+=1;c['failed_nodes']+=q['nodes']
    if 'effective_nodes'in q:c['full_configured_query_limit_failures']+=q['effective_nodes']==8192
  rows[str(path)]=dict(c);total.update(c)
 result=dict(status='PASS_ALL_ROOT_VALUE_PV_COHERENCE',counts=dict(total),journals=rows,seconds=time.perf_counter()-began,scope='ALL complete root scores equal actual recorded selected PV material dot/terminalconstant; no derivative computed from another leaf. ALLfailedreceipts have NOtarget/PV. This does not prove unobserved subtrees/minimax correctness, externalrules or calibrated WDL. Root/action/PV optimality sampled separately; fullhistory/math replay separate.')
 (D/'receipt-coherence.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status=result['status'],counts=result['counts'],seconds=result['seconds'])))
if __name__=='__main__':run()
