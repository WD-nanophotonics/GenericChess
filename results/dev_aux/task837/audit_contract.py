import json,sys,re,math,collections,hashlib,time
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task839';O.mkdir(exist_ok=False)
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import audit as V
rows=[json.loads(s) for s in (R/'results/dev_aux/task838/queries.jsonl').open(encoding='utf-8')];assert len(rows)==64;counts=collections.Counter();events=[];pairs=[]
for q in rows:
 V.query(q);counts['validated_queries']+=1;b=C.Board(q['initial_sfen'])
 for u in q['history']:m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
 rt=b.turn
 for line in q['lines']:
  if not line.startswith('info string auxreturn '):continue
  a=line.split(' ',8);site,ply,value,turn,material=map(int,a[3:8]);sfen=a[8];raw,_=V.literal(sfen,q['weights']);assert raw==material,(line,raw);assert C.Board(sfen).turn==turn;stm=material if turn==0 else -material;counts['trace_events']+=1;counts['nonmaterial_return_events']+=value!=stm;counts['royal_or_decisive_events']+=abs(value)>30000
  events.append(dict(case_index=q['case_index'],nodes=q['nodes_limit'],site=site,ply=ply,value=value,material_stm=stm,material_root=material if rt==0 else -material,sfen=sfen))
for i in range(0,len(rows),2):
 a,b=rows[i:i+2];assert a['mode']=='original' and b['mode']=='trace';filterlines=lambda q:[l for l in q['lines'] if not l.startswith('info string auxreturn ')];ia=[l for l in filterlines(a) if ' score ' in l];ib=[l for l in filterlines(b) if ' score ' in l];aa=ia[-1];bb=ib[-1];cp=lambda l:int(re.search(r' score cp (-?\d+)',l)[1]) if ' score cp ' in l else None
 eqbest=a['bestmove']==b['bestmove'];eqscore=cp(aa)==cp(bb);counts['paired_bestmove_equal']+=eqbest;counts['paired_final_cp_equal']+=eqscore
 rb=C.Board(b['initial_sfen'])
 for u in b['history']:rb.push_usi(u)
 rt=rb.turn;pv=bb.split(' pv ',1)[1].split() if ' pv ' in bb else []
 for u in pv:m=rb.move_from_usi(u);assert rb.is_legal(m);rb.push(m)
 raw,_=V.literal(rb.sfen(),b['weights']);leaf=raw if rt==0 else -raw;leafcp=math.trunc(100*leaf/90);mismatch=cp(bb)!=leafcp;counts['trace_final_cp_PV_mismatch']+=mismatch
 root=[e for e in events if e['case_index']==b['case_index'] and e['nodes']==b['nodes_limit'] and e['ply']==0];pairs.append(dict(case_index=b['case_index'],nodes=b['nodes_limit'],bestmove_equal=eqbest,final_cp_equal=eqscore,original_final=aa,trace_final=bb,PV_leaf_cp=leafcp,PV_score_mismatch=mismatch,root_return_events=root))
result=dict(status='PASS_ALL64_QUERY_PV_AND_TRACE_MATERIAL_OBSERVATIONS',counts=dict(counts),pairs=pairs,events_by_site=dict(collections.Counter(e['site'] for e in events)),scope='Telemetryobserves7explicitreturn sites, notallsearchreturns/TTprovenance/selectedleafpropagation. Returnobservedstateisnotnecessarilyexactscore-producingleaf. Node-limitedwallpoll/printoverhead means equality is measured, notassumed. Colddiagnosticnotoldwarmreproduction.')
(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');(O/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='pairs'}))
