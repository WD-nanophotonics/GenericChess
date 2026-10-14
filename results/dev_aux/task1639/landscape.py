from pathlib import Path
import json,collections,random
R=Path.cwd();O=R/'results/dev_aux/task1670';O.mkdir(exist_ok=False);studies=[]
for task in [1641,1652,1661,1667]:
 run=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());field='lower' if task==1641 else 'finite_net';grid={}
 for phase in ['TRAIN1','TRAIN2']:
  grid[phase]={tuple(x['price']):x[field] for x in run['TRAIN'] if x['phase']==phase}
 grid['POOLED']={p:(grid['TRAIN1'][p]+grid['TRAIN2'][p])/2 for p in grid['TRAIN1']}
 landscapes=[]
 for phase,score in grid.items():
  rr=sorted({p[0] for p in score});bb=sorted({p[2] for p in score});paths=[];endcounts=collections.Counter()
  for initial in sorted(score):
   p=initial;path=[p]
   while True:
    i=rr.index(p[0]);j=bb.index(p[2]);neighbors=[(rr[k],720,p[2]) for k in [i-1,i+1] if 0<=k<len(rr)]+[(p[0],720,bb[k]) for k in [j-1,j+1] if 0<=k<len(bb)];best=min(neighbors,key=lambda q:(-score[q],q))
    if score[best]<=score[p]:break
    p=best;path.append(p)
   endcounts[str(p)]+=1;paths.append({'initial':initial,'end':p,'score':score[p],'path':path})
  maximum=max(score.values());maxpoints=[p for p,v in score.items() if v==maximum];landscapes.append({'phase':phase,'global_max_points':maxpoints,'maximum':maximum,'strict_adjacent_path_global_arrivals':sum(x['score']==maximum for x in paths),'path_count':len(paths),'end_counts':dict(endcounts),'paths':paths})
 studies.append({'task':task,'objective':field,'landscapes':landscapes})
out={'status':'COMPLETED_ZERO_QUERY_OPTIMIZER_PLATFORM_DIAGNOSTIC','studies':studies,'actual_go':0,'scope':'All12initialgridpoints reuseoneobservedlandscape perTRAIN/POOLED, not12independenttrainingreplications. Strictimprovement stopsplateaus, nohumanpricefit/DEVchoice. Globalargmax repeatability byconstruction isnot optimizerconvergence.'};(O/'result.json').write_text(json.dumps(out,indent=2));print([{'task':s['task'],'arrivals':[(x['phase'],x['strict_adjacent_path_global_arrivals'],x['global_max_points']) for x in s['landscapes']]} for s in studies])

