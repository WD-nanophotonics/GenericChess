import json,hashlib,re,collections,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task655';start=time.perf_counter();d=json.loads((R/'results/dev_aux/task624/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task624/result.json').read_bytes());audit=json.loads((R/'results/dev_aux/task625/result.json').read_bytes());gs={t:[json.loads(x) for x in (R/f'results/dev_aux/task{t}/games.jsonl').open(encoding='utf-8')] for t in [614,624]};lookup={}
for x in r['rows']:
 t=614 if x['reused'] else 624;lookup[(x['profile'],x['nodes'],x['root'],x['color'])]=(gs[t][x['source']['line']-1],x['source'])
def info(q):
 ss=[s for s in q['lines'] if ' nodes ' in s and ' score ' in s];a=ss[-1];out=dict(bestmove=q['bestmove'],history=q['history'],state=q['state'],raw_info=a,requested_nodes=q['nodes_limit'])
 for k in ['nodes','depth','seldepth']:m=re.search(r'\b'+k+r' (\d+)',a);out[k]=int(m[1]) if m else None
 m=re.search(r'score (cp|mate) (-?\d+)',a);out.update(score_kind=m[1],score=int(m[2]),lowerbound='lowerbound' in a,upperbound='upperbound' in a);return out
rows=[]
for pi in range(6):
 for f in d['roots']:
  for c in [0,1]:
   (a,asrc),(b,bsrc)=[lookup[(pi,n,f['index'],c)] for n in [1024,8192]];assert a['weights']==b['weights'] and a['root']==b['root'] and a['color']==b['color'];aa=a['actions'];bb=b['actions'];n=0
   while n<min(len(aa),len(bb)) and aa[n]['move']==bb[n]['move']:
    assert aa[n]['before_sfen']==bb[n]['before_sfen'] and aa[n]['after_sfen']==bb[n]['after_sfen'];n+=1
   changed=n<min(len(aa),len(bb));assert changed or len(aa)==len(bb)
   rec=dict(profile=pi,root=f['index'],phase=f['phase'],family=f['source_family'],color=c,common_actual_actions=n,changed=changed,low_source=asrc,high_source=bsrc,terminations_same=a['termination']==b['termination'],low_termination=a['termination'],high_termination=b['termination'])
   if changed:
    assert aa[n]['actor']==bb[n]['actor']==c;assert aa[n]['before_sfen']==bb[n]['before_sfen'];q=[next(q for q in g['queries'] if q['ply']==n) for g in [a,b]];assert q[0]['history']==q[1]['history'] and q[0]['state']==q[1]['state'];rec.update(first_divergence_ply=n,first_divergence_queries=list(map(info,q)),same_full_root_and_history=True,warm_prior_candidate_calls=sum(qi['ply']<n for qi in a['queries']))
   else:assert a['termination']==b['termination']
   rows.append(rec)
summ=[]
for pi in range(6):
 for phase in ['train','development']:
  x=[a for a in rows if a['profile']==pi and a['phase']==phase];y=[a for a in x if a['changed']];summ.append(dict(profile=pi,phase=phase,cells=len(x),changed=len(y),terminal_changed=sum(not a['terminations_same'] for a in x),first_divergence_ply=dict(collections.Counter(a['first_divergence_ply'] for a in y)),at_first_candidate_call=sum(a['warm_prior_candidate_calls']==0 for a in y),either_mate_score=sum(any(q['score_kind']=='mate' for q in a['first_divergence_queries']) for a in y),both_mate_score=sum(all(q['score_kind']=='mate' for q in a['first_divergence_queries']) for a in y)))
out=dict(status='ALL864_BUDGET_COMMON_PARENT_PAIRS_PASS',logical_pairs=len(rows),rows=rows,summary=summ,new_go=0,seconds=time.perf_counter()-start,scope='Every6price/72root/bothcolor old1024-vs8192pair, exactcommonactualprefix/fullhistory/state/cache material andfirstchangedcandidatequery. Alloriginaldata625audited/source controls preserved. Firstdifferentaction cannot beuniformrandomonidenticalhistory/draw, actualassertchecked. Latercommonparent histories donotimplysamewarmTT/historyheuristics: previoussearchbudget differs. Mate scores descriptive notall-defensecertificates. Newpolicywork/depth allretained, nofilteredcompletion/postdepthsubset/equalactualnodes/globalqualityclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(summ))
