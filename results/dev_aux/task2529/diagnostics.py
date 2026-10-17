from pathlib import Path
import json,math,itertools,time
D=Path('results/dev_aux/task2527');O=Path('results/dev_aux/task2529')
def rank(rows):
 a=[list(map(float,r))for r in rows];n=0
 for c in range(len(a[0])if a else 0):
  pivot=next((i for i in range(n,len(a))if abs(a[i][c])>1e-10),None)
  if pivot is None:continue
  a[n],a[pivot]=a[pivot],a[n];v=a[n][c];a[n]=[x/v for x in a[n]]
  for i in range(len(a)):
   if i!=n:
    v=a[i][c];a[i]=[x-v*y for x,y in zip(a[i],a[n])]
  n+=1
  if n==len(a):break
 return n

def summarize(rows):
 pairs=list(itertools.combinations(rows,2));rms=math.sqrt(sum((a[j]-b[j])**2 for a,b in pairs for j in range(1,len(a)))/max(1,len(pairs)*(len(rows[0])-1)))if rows else None
 signs=lambda w:[(w[i]>w[j])-(w[i]<w[j])for i,j in itertools.combinations(range(len(w)),2)]
 agreement=sum(x==y for a,b in pairs for x,y in zip(signs(a),signs(b)))/max(1,len(pairs)*len(signs(rows[0])))if rows else None
 return dict(free_coordinate_pairwise_RMS=rms,all_channel_pairwise_order_agreement=agreement,models=len(rows))

def run():
 start=time.perf_counter();p=json.loads((D/'registration.json').read_text());r=json.loads((D/'result.json').read_text());bins={};eps={};bykey={(a['generator_seed'],a['seed']):a for a in r['arms']};out=[]
 for line in(D/'queries.jsonl').open():
  q=json.loads(line)
  if not q['complete']:continue
  key=q['generator_seed'],q['seed'],min(3,max(0,(q['total_nodes']-1)//62500));b=bins.setdefault(key,dict(queries=0,nonzero_gradient_queries=0,terminal_PV_queries=0,gradient_square=0.,gram=[[0.]*5 for _ in range(5)]));g=q['gradient'][1:];b['queries']+=1;b['nonzero_gradient_queries']+=any(g);b['terminal_PV_queries']+=q['pv_terminal'];b['gradient_square']+=sum(x*x for x in g)
  for i in range(5):
   for j in range(5):b['gram'][i][j]+=g[i]*g[j]
 for line in(D/'episodes.jsonl').open():
  e=json.loads(line);key=e['generator_seed'],e['seed'],min(3,max(0,(e['total_nodes']-1)//62500));b=eps.setdefault(key,dict(episodes=0,zero_queries=0,one_query=0,nonzero_updates=0,actual_terminal=0,unknown=0,loss_terms=0,half_square_sum=0.,episode_step_l2_sum=0.));b['episodes']+=1;b['zero_queries']+=e['queries']==0;b['one_query']+=e['queries']==1;b['nonzero_updates']+=e['initial_weights']!=e['weights'];b['actual_terminal']+=e['outcome']is not None;b['unknown']+=e['outcome']is None;b['loss_terms']+=e['stats']['samples'];b['half_square_sum']+=e['stats']['samples']*e['stats']['loss'];b['episode_step_l2_sum']+=math.sqrt(sum((x-y)**2 for x,y in zip(e['initial_weights'],e['weights'])))
 for key in sorted(set(bins)|set(eps)):
  b=dict(bins.get(key,{}));gram=b.pop('gram',[]);b['gradient_span_rank']=rank(gram);b['all_query_gradient_RMS']=math.sqrt(b.get('gradient_square',0)/max(1,5*b.get('queries',0)));out.append(dict(generator_seed=key[0],seed=key[1],node_bin=key[2],queries=b,episodes=eps.get(key,{})))
 curves=[]
 for gs in p['generator_seeds']:
  aa=[bykey[gs,s]for s in p['initial_seeds']if(gs,s)in bykey]
  for level in ['initial']+['n'+str(t)for t in p['checkpoints']]:
   weights=[];details=[]
   for a in aa:
    snap=dict(nodes=0,game=-1,weights=a['initial'])if level=='initial'else next((x for x in a['snapshots']if 'n'+str(x['target_nodes'])==level),None)
    if snap is None:continue
    weights.append(snap['weights']);details.append(dict(seed=a['seed'],raw_P=snap['weights'][0],weight_L2_norm=math.sqrt(sum(x*x for x in snap['weights'])),**snap))
   curves.append(dict(generator_seed=gs,level=level,channels=aa[0]['channels']if aa else[],summary=summarize(weights),all_models=details))
 result=dict(status='CLOSED_RECEIPT_DIAGNOSTICS',bins=out,curves=curves,scope='Eachrule separately/ALLmodels/checkpoints; boardPscale1 only, generatedPnotChesspawn. ALLchannelordering includesboard-current andhand-base contexts, notintrinsicuniversalpieceordering. Gramrank=observedgradientspan, noidentifiability/proof/strengthclaim. Lossbins underchangingonpolicytraining are NOTfixedvalidationloss; eta/unit/horizonfixed. No newsearch/fitness/modelselection.',seconds=time.perf_counter()-start);(O/'learning-diagnostics.json').write_text(json.dumps(result,indent=2));print(json.dumps(dict(status=result['status'],bins=len(out),curves=len(curves),seconds=result['seconds'])))
if __name__=='__main__':run()
