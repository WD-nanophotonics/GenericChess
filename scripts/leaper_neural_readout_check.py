"""One fresh5x5qualification of a frozen GNN readout hypothesis; no training.

All candidate tensors describe the actual Core game. The only intervention is
mean versus fixed-reference sum/16 at the global readout. Rules and histories,
model weights, legal graph, labels and cheap comparators are paired and fixed.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import random
import time
import torch
from torch import nn
from generic_chess.core.attacks import is_in_check
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.session import GameSession
from scripts.leaper_neural_experiment import make_rules,canonical_group,LABELS,metrics,replay,baseline_features
from scripts.leaper_neural_model import LeaperValueNet,graph_from_session,batch_graphs
from scripts.leaper_neural_teacher import solve_session
from scripts.research_record import record_value,write_record


def run(base,output):
    base,output=Path(base),Path(output);output.mkdir(parents=True,exist_ok=False)
    plan=dict(question='Does fixed-reference sum readout improve frozen4x4GNN value on fresh5x5roots?',
              seed=20261113,size=5,max_ply=8,nodes=1500,slots=2160,batch_seconds=600,
              factors='6families x3initialpiececounts x2extraowners x3prefixlengths x20replicates, randomized before labels',
              changes='one readout only: mean vs sum/16; same three4x4checkpoints, no training/fine-tuning/search/default changes',
              gate='Atleast30exact decisive roots; all3seed decisive accuracies nondecreasing; mean decisive gain>=.10 and mean balanced gain>=.05. This qualifies only the readout mechanism, not transfer-vs-scratch or playing strength.',
              label_scope='finite8-ply exact subset, UNKNOWN not DRAW; no outcome-based input replacement or budget refill',
              cost_forecast='roughly7-10minutes including teacher+inference; hard600second dispatch bound plus one1500node in-flight call; preserve all NOT_RUN')
    write_record(output/'plan.json',plan)
    old=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    seen={r['group'] for r in old if r['size']==5 and 'group' in r}
    # Reconstruct the original deterministic cheap fits, not new comparators.
    train=[r for r in old if r['size']==4 and r['status']=='EXACT' and r['split']=='train']
    fs=[[],[]]
    for row in train:
        r,s=replay(row);g=graph_from_session(r,s);a,b=baseline_features(r,s,g);fs[0].append(a);fs[1].append(b)
    y=torch.tensor([LABELS[r['label']] for r in train]);count=torch.bincount(y,minlength=3).float();weights=len(train)/(3*count)
    torch.set_num_threads(2);baselines=[]
    for values in fs:
        x=torch.stack(values);torch.manual_seed(17);m=nn.Linear(x.shape[1],3);opt=torch.optim.Adam(m.parameters(),lr=.03)
        for _ in range(300):
            opt.zero_grad();loss=nn.functional.cross_entropy(m(x),y,weight=weights);loss.backward();opt.step()
        baselines.append(m.eval())
    models=[]
    for seed in (0,1,2):
        ck=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(ck['hidden'],ck['rounds']);m.load_state_dict(ck['state_dict']);models.append(m.eval())
    factors=[(f,n,o,p,k) for f in range(6) for n in (3,4,5) for o in (0,1) for p in (0,1,2) for k in range(20)]
    rng=random.Random(plan['seed']);rng.shuffle(factors)
    tick=time.perf_counter();rows=[];stop=None
    with gzip.open(output/'results.jsonl.gz','wt',encoding='utf-8',newline='\n') as archive:
        for slot,(family,n,owner,prefix,k) in enumerate(factors):
            if time.perf_counter()-tick>=plan['batch_seconds']:stop='batch_cap';break
            session=None
            for attempt in range(200):
                cells=rng.sample(range(25),n);pieces=[(cells[0],0,'K'),(cells[1],1,'K'),(cells[2],owner,'A')]
                if n>=4:pieces.append((cells[3],1-owner,'B'))
                if n>=5:pieces.append((cells[4],owner,'B'))
                rules=make_rules(5,family,pieces,max_ply=8)
                try:c=compile_ruleset(rules)
                except RuleValidationError:continue
                candidate=GameSession(c)
                if candidate.result.status.value!='ongoing' or is_in_check(candidate.state.position,1,c):continue
                for _ in range(prefix):
                    if candidate.result.status.value!='ongoing':break
                    candidate.submit(rng.choice(candidate.legal_actions()))
                if candidate.result.status.value!='ongoing':continue
                group=canonical_group(rules,candidate)
                if group in seen:continue
                seen.add(group);session=candidate;break
            if session is None:
                row=dict(slot=slot,family=family,initial_pieces=n,extra_owner=owner,prefix=prefix,replicate=k,status='NO_INPUT')
            else:
                start=time.perf_counter();teacher=solve_session(rules,session,1500)
                g=graph_from_session(rules,session);b=batch_graphs([g]);mean=[];fixed=[]
                with torch.no_grad():
                    for m in models:
                        mean.append(m(b)[0].tolist())
                        def pool(module,args):
                            x=args[0];return (torch.cat((x[:,:m.hidden]*(25/16),x[:,m.hidden:]),dim=1),)
                        hook=m.value_head.register_forward_pre_hook(pool)
                        try:fixed.append(m(b)[0].tolist())
                        finally:hook.remove()
                    a,bb=baseline_features(rules,session,g)
                    cheap=[m(x[None])[0].tolist() for m,x in zip(baselines,(a,bb))]
                row=dict(slot=slot,family=family,initial_pieces=n,extra_owner=owner,prefix=prefix,replicate=k,status=teacher['status'],
                         rules=ruleset_to_dict(rules),record=record_value(session.to_record()),group=group,teacher=teacher,
                         mean_logits=mean,fixed_logits=fixed,baseline_logits=cheap,seconds=time.perf_counter()-start)
            rows.append(row);archive.write(json.dumps(row,separators=(',',':'))+'\n');archive.flush()
            if slot%108==0:print(json.dumps(dict(done=slot+1,seconds=time.perf_counter()-tick,labels=dict(Counter(r['teacher']['label'] or 'UNKNOWN' for r in rows if 'teacher' in r)))),flush=True)
    exact=[r for r in rows if r['status']=='EXACT'];yy=torch.tensor([LABELS[r['teacher']['label']] for r in exact]);pairs=[]
    for seed in (0,1,2):
        pairs.append(dict(seed=seed,mean=metrics(torch.tensor([r['mean_logits'][seed] for r in exact]),yy),
                          fixed=metrics(torch.tensor([r['fixed_logits'][seed] for r in exact]),yy)))
    decisive=int((yy!=1).sum())
    gain=sum(x['fixed']['decisive_accuracy']-x['mean']['decisive_accuracy'] for x in pairs)/3 if decisive else None
    balanced=sum(x['fixed']['balanced_accuracy']-x['mean']['balanced_accuracy'] for x in pairs)/3
    passed=decisive>=30 and gain>=.1 and balanced>=.05 and all(x['fixed']['decisive_accuracy']>=x['mean']['decisive_accuracy'] for x in pairs)
    summary=dict(status='READOUT_MECHANISM_SUPPORTED' if passed else 'NO_GO_OR_INCONCLUSIVE',seconds=time.perf_counter()-tick,slots=len(rows),not_run=2160-len(rows),stop=stop,
                 labels=dict(Counter(r['teacher']['label'] or 'UNKNOWN' for r in rows if 'teacher' in r)),decisive_exact=decisive,pairs=pairs,
                 baselines={name:metrics(torch.tensor([r['baseline_logits'][i] for r in exact]),yy) for i,name in enumerate(('material','structure'))},
                 mean_decisive_gain=gain,mean_balanced_gain=balanced,
                 limitation='Only paired readout qualification on6exposed movement families and finite8-ply exact teacher subset. No5x5training, transfer-vs-scratch, independent rules or playing-strength result. No adoption/default change.')
    write_record(output/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.base,a.output)
