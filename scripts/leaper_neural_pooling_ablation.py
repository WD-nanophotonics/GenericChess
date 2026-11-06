"""Single frozen-weight readout ablation: mean versus sum/16.

4x4 readout is mathematically unchanged. On5x5 this tests dilution of features
by averaging25rather than16nodes, without new size-specific trainable weights.
It is an exposed development ablation, not accepted transfer evidence.
"""
import argparse
import gzip
import json
from pathlib import Path
import time
import torch
from scripts.leaper_neural_experiment import replay,LABELS,metrics
from scripts.leaper_neural_model import graph_from_session,batch_graphs,LeaperValueNet
from scripts.research_record import write_record


def run(base):
    base=Path(base);destination=base/'pooling-ablation.json'
    if destination.exists():raise FileExistsError('do not overwrite original ablation')
    tick=time.perf_counter();torch.set_num_threads(2)
    rows=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    rows=[r for r in rows if r['status']=='EXACT' and (r['size']==5 or r['split']=='validation')]
    graphs=[graph_from_session(*replay(r)) for r in rows];truth=torch.tensor([LABELS[r['label']] for r in rows])
    result=[]
    for seed in (0,1,2):
        ck=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(ck['hidden'],ck['rounds']);m.load_state_dict(ck['state_dict']);m.eval()
        actual=[];ablation=[]
        with torch.no_grad():
            for start in range(0,len(rows),32):
                gs=graphs[start:start+32];b=batch_graphs(gs);actual.append(m(b))
                scale=torch.tensor([len(g.nodes)/16 for g in gs]).unsqueeze(1)
                def rescale_pooled(module,args):
                    x=args[0]
                    return (torch.cat((x[:,:m.hidden]*scale,x[:,m.hidden:]),dim=1),)
                hook=m.value_head.register_forward_pre_hook(rescale_pooled)
                try:ablation.append(m(b))
                finally:hook.remove()
        actual=torch.cat(actual);ablation=torch.cat(ablation)
        for size in (4,5):
            ix=[i for i,r in enumerate(rows) if r['size']==size]
            if size==4 and not torch.equal(actual[ix],ablation[ix]):raise ValueError('4x4control changed')
            result.append(dict(seed=seed,size=size,actual=metrics(actual[ix],truth[ix]),fixed_reference_sum=metrics(ablation[ix],truth[ix]),
                               changed_predictions=int((actual[ix].argmax(-1)!=ablation[ix].argmax(-1)).sum())))
    report=dict(seconds=time.perf_counter()-tick,results=result,training=0,solver_queries=0,
                question='Does the mean readout dilute learned4x4features on5x5?',
                intervention='Only global pooled hidden-vector multiplier changes from1to(nodecount/16). Globals, graph, weights and all layers unchanged.16is the fixed pretraining reference area, not a learned size weight.',
                limitation='Exposed finite8-ply exact subset, only19decisive5x5roots. One development ablation selected after observing mean-pooling model failure, not untouched zero-shot/transfer-vs-scratch or strength evidence. No candidate adoption.')
    write_record(destination,report)
    print(json.dumps(dict(seconds=report['seconds'],results=[dict(seed=r['seed'],size=r['size'],actual_balanced=r['actual']['balanced_accuracy'],new_balanced=r['fixed_reference_sum']['balanced_accuracy'],actual_decisive=r['actual']['decisive_accuracy'],new_decisive=r['fixed_reference_sum']['decisive_accuracy'],changed=r['changed_predictions']) for r in result])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);a=p.parse_args();run(a.base)
