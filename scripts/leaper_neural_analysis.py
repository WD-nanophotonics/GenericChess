"""Analyze frozen Leaper predictions and exact-label selection, without new queries.

Cheap comparator fits reconstruct the ORIGINAL deterministic fit because the
initial caller saved metrics but not their coefficients. No GNN is retrained.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import time

import torch
from torch import nn
from scripts.leaper_neural_experiment import replay, baseline_features, LABELS, metrics
from scripts.leaper_neural_model import graph_from_session, batch_graphs, LeaperValueNet
from scripts.research_record import write_record


def features(rows):
    graphs=[];material=[];structure=[]
    for row in rows:
        rules,s=replay(row);g=graph_from_session(rules,s)
        a,b=baseline_features(rules,s,g)
        graphs.append(g);material.append(a);structure.append(b)
    return graphs,{'material':torch.stack(material),'structure':torch.stack(structure)}


def paired_intervals(predictions, baseline, y, repetitions=2000):
    # Resample the same labelled roots in each paired prediction; stratify WDL
    # to retain the actual finite validation class support. Not a population CI
    # across unseen rules or UNKNOWN teacher outcomes.
    gen=torch.Generator().manual_seed(20261111)
    ids=[torch.where(y==k)[0] for k in range(3)]
    ids=[x for x in ids if len(x)]
    differences=[];decisive=[]
    for _ in range(repetitions):
        samples=[x[torch.randint(len(x),(len(x),),generator=gen)] for x in ids]
        differences.append(torch.stack([(predictions[:,ix]==y[ix]).float().mean()-(baseline[ix]==y[ix]).float().mean() for ix in samples]).mean())
        ix=torch.cat(samples);ix=ix[y[ix]!=1]
        if len(ix):decisive.append((predictions[:,ix]==y[ix]).float().mean()-(baseline[ix]==y[ix]).float().mean())
    def interval(values):
        return torch.quantile(torch.stack(values),torch.tensor([.025,.5,.975])).tolist() if values else None
    return dict(roots=len(y),repetitions=repetitions,balanced_difference_95=interval(differences),decisive_difference_95=interval(decisive),
                scope='Paired class-stratified bootstrap conditional on exact saved roots, averaging seed accuracies; excludes teacher-UNKNOWN and rule-distribution uncertainty.')


def run(base, factor):
    tick=time.perf_counter();base=Path(base);factor=Path(factor);torch.set_num_threads(2)
    data=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))
    rows=[r for r in data['rows'] if r['status']=='EXACT']
    graphs,feat=features(rows)
    y=torch.tensor([LABELS[r['label']] for r in rows])
    train=[i for i,r in enumerate(rows) if r['size']==4 and r['split']=='train']
    weights=torch.bincount(y[train],minlength=3).float()
    weights=torch.where(weights>0,len(train)/(3*weights.clamp_min(1)),0.)
    old=json.loads((base/'learning-result.json').read_text())
    baselines={}
    for name,x in feat.items():
        torch.manual_seed(17);m=nn.Linear(x.shape[1],3);opt=torch.optim.Adam(m.parameters(),lr=.03)
        for _ in range(300):
            opt.zero_grad();loss=nn.functional.cross_entropy(m(x[train]),y[train],weight=weights);loss.backward();opt.step()
        baselines[name]=m.eval()
    models=[]
    for seed in (0,1,2):
        saved=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(saved['hidden'],saved['rounds']);m.load_state_dict(saved['state_dict']);models.append(m.eval())
    def logits(gs):
        result=[]
        with torch.no_grad():
            for m in models:
                result.append(torch.cat([m(batch_graphs(gs[start:start+32])) for start in range(0,len(gs),32)]))
        return torch.stack(result)
    all_logits=logits(graphs)
    comparisons=[]
    for size,split in ((4,'validation'),(5,None)):
        ix=[i for i,r in enumerate(rows) if r['size']==size and (split is None or r['split']==split)]
        truth=y[ix];pred=all_logits[:,ix].argmax(-1)
        for name,m in baselines.items():
            with torch.no_grad():b=m(feat[name][ix])
            match=old['baselines'][name]['validation4' if size==4 else 'zero_shot5']
            actual=metrics(b,truth)
            if abs(actual['balanced_accuracy']-match['balanced_accuracy'])>1e-6:
                raise ValueError('original comparator reconstruction did not reproduce original metric')
            comparisons.append(dict(size=size,baseline=name,baseline_reproduced=True,
                                    intervals=paired_intervals(pred,b.argmax(-1),truth)))
    raw=[json.loads(line) for line in (factor/'results.jsonl').read_text().splitlines()]
    exact=[dict(r,label=r['teacher']['label'],size=4) for r in raw if r['status']=='EXACT']
    fgraphs,ffeat=features(exact);fy=torch.tensor([LABELS[r['label']] for r in exact])
    frozen=torch.tensor([r['logits'] for r in exact]).transpose(0,1)
    factor_results=[]
    for original in (True,False,None):
        ix=[i for i,r in enumerate(exact) if original is None or r['original_combination']==original]
        if not ix:continue
        condition=dict(original_combination=original,labels=torch.bincount(fy[ix],minlength=3).tolist(),
                       models=[metrics(frozen[k,ix],fy[ix]) for k in range(3)],baselines={},intervals={})
        for name,m in baselines.items():
            with torch.no_grad():b=m(ffeat[name][ix])
            condition['baselines'][name]=metrics(b,fy[ix])
            condition['intervals'][name]=paired_intervals(frozen[:,ix].argmax(-1),b.argmax(-1),fy[ix])
        factor_results.append(condition)
    selection=[]
    for size in (4,5):
        for family in range(6):
            subset=[r for r in data['rows'] if r['size']==size and r['family']==family]
            selection.append(dict(size=size,family=family,total=len(subset),labels=dict(Counter(r['label'] or 'UNKNOWN' for r in subset))))
    errors=[]
    for r in exact:
        predicted=[int(torch.tensor(x).argmax()) for x in r['logits']]
        if any(p!=LABELS[r['label']] for p in predicted):
            errors.append(dict(slot=r['slot'],family=r['family'],initial_pieces=r['initial_pieces'],extra_owner=r['extra_owner'],prefix=r['prefix'],
                               original_combination=r['original_combination'],label=r['label'],predicted_LDW=predicted))
    report=dict(seconds=time.perf_counter()-tick,original_comparisons=comparisons,factor_results=factor_results,teacher_selection=selection,factor_errors=errors,
                hypothesis='Old slot coupling may exaggerate within-distribution value quality. This check changes only heldout factor sampling, freezing networks and teacher budget.',
                limitations=['Exact labels are selected by finite solver budget, not missing at random.','Six exposed families only; no heldout movement or cross-rule generalization evidence.','Finite8-ply WDL is not full-length strength.','Bootstrap conditions on saved roots and does not make seed repetitions independent datasets.'])
    write_record(factor/'analysis.json',report)
    print(json.dumps(dict(seconds=report['seconds'],original_comparisons=comparisons,factor_results=factor_results)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--factor',required=True)
    a=p.parse_args();run(a.base,a.factor)
