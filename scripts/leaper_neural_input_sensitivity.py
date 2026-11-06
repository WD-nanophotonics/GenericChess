"""Frozen-input sensitivity only, not legal counterfactual games or new models.

At 4x4, explicit size channels are constant and their effect on a new size is
not identified by training. Test three channel groups separately, holding the
actual Core graph and learned weights fixed. These altered tensors do NOT
represent complete legal game inputs and their accuracy is not a deployment
or transfer result.
"""
import argparse
from dataclasses import replace
import gzip
import json
from pathlib import Path
import time
import torch
from scripts.leaper_neural_experiment import replay,LABELS,metrics
from scripts.leaper_neural_model import graph_from_session,batch_graphs,LeaperValueNet
from scripts.research_record import write_record


def intervention(g,size,kind):
    nodes=g.nodes.clone();offsets=g.offsets.clone();relations=g.relations.clone();globals_=g.globals.clone()
    if kind=='explicit_size_at4':
        nodes[:,4:6]=4/19;globals_[:3]=torch.tensor([4/19,4/19,16/361])
    elif kind=='relative_leaps_at4':
        offsets[:,2:4]*=(size-1)/3;relations[:,2:4]*=(size-1)/3
    elif kind=='absolute_coordinates_in_training_range':
        nodes[:,:2]*=3/(size-1)
    elif kind!='actual':raise ValueError(kind)
    return replace(g,nodes=nodes,offsets=offsets,relations=relations,globals=globals_)


def run(base):
    base=Path(base);destination=base/'input-sensitivity.json'
    if destination.exists():raise FileExistsError('keep original sensitivity results')
    tick=time.perf_counter();torch.set_num_threads(2)
    data=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    rows=[r for r in data if r['status']=='EXACT' and (r['size']==5 or r['split']=='validation')]
    gs=[graph_from_session(*replay(r)) for r in rows];y=torch.tensor([LABELS[r['label']] for r in rows]);result=[]
    for seed in (0,1,2):
        saved=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(saved['hidden'],saved['rounds']);m.load_state_dict(saved['state_dict']);m.eval()
        actual=None
        for kind in ('actual','explicit_size_at4','relative_leaps_at4','absolute_coordinates_in_training_range'):
            inputs=[intervention(g,r['size'],kind) for g,r in zip(gs,rows)]
            with torch.no_grad():logits=torch.cat([m(batch_graphs(inputs[start:start+32])) for start in range(0,len(inputs),32)])
            if actual is None:actual=logits
            for size in (4,5):
                ix=[i for i,r in enumerate(rows) if r['size']==size]
                if size==4 and not torch.equal(logits[ix],actual[ix]):raise ValueError('4x4 control changed')
                result.append(dict(seed=seed,size=size,intervention=kind,metrics=metrics(logits[ix],y[ix]),
                                   changed_predictions=int((logits[ix].argmax(-1)!=actual[ix].argmax(-1)).sum()),
                                   mean_probability_shift=float((logits[ix].softmax(-1)-actual[ix].softmax(-1)).abs().sum(-1).mean())))
    report=dict(seconds=time.perf_counter()-tick,results=result,training=0,solver_queries=0,
                interpretation='Mechanistic sensitivity of frozen predictions ONLY: three isolated altered-input groups; no tensor intervention is a valid substitute for board size/rule metadata or a tested new network.',
                limitation='Existing5x5development roots already exposed; finite exact subset; changes can be out of distribution; do not choose best perturbation and call it transfer success.')
    write_record(destination,report)
    print(json.dumps(dict(seconds=report['seconds'],results=[dict(seed=r['seed'],intervention=r['intervention'],balanced=r['metrics']['balanced_accuracy'],decisive=r['metrics']['decisive_accuracy'],changed=r['changed_predictions']) for r in result if r['size']==5])),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);a=p.parse_args();run(a.base)
