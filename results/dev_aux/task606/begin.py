import json,collections,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task606';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task596/declaration.json').read_bytes());rows=[]
for f in d['roots']:
 b=C.Board(f['initial_sfen'])
 for u in f['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 assert b.sfen()==f['expected_sfen'];present=collections.Counter(pc%16 for pc in b.pieces if pc);handtypes=[1,2,3,4,7,5,6]
 for hand in b.pieces_in_hand:
  for t,count in zip(handtypes,hand):present[t]+=count
 rows.append(dict(index=f['index'],family=f['source_family'],phase=f['phase'],offset=f['offset'],counts=dict(present)))
summ=[dict(phase=p,roots=sum(x['phase']==p for x in rows),type_presence={str(a):sum(x['phase']==p and x['counts'].get(a,0)>0 for x in rows) for a in d['axes']},rook_belowpawn_scope='Observedendpointwrongratio motivatesALLtypecoverage, presence isnotpriceidentifiability') for p in ['train','development']]
result=dict(status='BEGIN_NEXT_TASK_ROOT_COVERAGE_PASS',roots=72,rows=rows,summary=summ,new_go=0,prior_declaration_sha256=hashlib.sha256((R/'results/dev_aux/task596/declaration.json').read_bytes()).hexdigest(),next_action='StreamALL597598599actualpaths signedownership/hand/promotion/capture/moving types andnode/depthcompletion counters byfamily/allprices; rootpresence alone doesnotdiagnose target orsearch.',scope='Initialcoverageonly; no physicaltraining replay audit/feature rank orhumanfit claim. 8train3eligibledevelopmentfamilies original4thunavailable retained. SourcefreeALL12axes, no targetedrankfitting.');(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(summ))