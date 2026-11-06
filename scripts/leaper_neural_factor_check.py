"""Frozen-model check on independently crossed family/count/owner/prefix factors.

This is a new heldout distribution diagnostic, not a refill of either pilot.
No training, model/loss changes, product integration or outcome selection.
"""
from collections import Counter
from pathlib import Path
import argparse
import gzip
import json
import random
import time

import torch
from generic_chess.core.attacks import is_in_check
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_to_dict
from generic_chess.rules.validation import RuleValidationError
from generic_chess.session.session import GameSession
from scripts.leaper_neural_experiment import make_rules, canonical_group, LABELS, metrics
from scripts.leaper_neural_model import LeaperValueNet, graph_from_session, batch_graphs
from scripts.leaper_neural_teacher import solve_session
from scripts.research_record import record_value, write_record


def run(base, output, seconds=180):
    base, output = Path(base), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    plan = dict(question='Does frozen 4x4 value survive independent sampling of factors previously tied to slot?',
                size=4, max_ply=8, seed=20261110, nodes=1500, seconds=seconds,
                factors=dict(family=list(range(6)), pieces=[3,4,5], extra_owner=[0,1], prefix=[0,1,2], replicates=2),
                slots=216, training=0, no_refill=True,
                decisions='Report exact coverage and decisive/balanced accuracy on seen versus new family/count/owner combinations. No transfer or strength claim; unsupported labels stay UNKNOWN.')
    write_record(output/'plan.json', plan)
    previous = json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    seen = {r['group'] for r in previous if r['size']==4 and 'group' in r}
    models=[]
    for seed in (0,1,2):
        checkpoint=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(checkpoint['hidden'],checkpoint['rounds'])
        m.load_state_dict(checkpoint['state_dict']);m.eval();models.append(m)
    torch.set_num_threads(2)
    factors=[(f,count,owner,prefix,rep) for f in range(6) for count in (3,4,5)
             for owner in (0,1) for prefix in (0,1,2) for rep in range(2)]
    rng=random.Random(plan['seed']);rng.shuffle(factors)
    tick=time.perf_counter();rows=[];stop=None
    for slot,(family,count,owner,prefix,rep) in enumerate(factors):
        if time.perf_counter()-tick>=seconds:
            stop='batch_cap';break
        session=None
        for attempt in range(200):
            cells=rng.sample(range(16),count)
            pieces=[(cells[0],0,'K'),(cells[1],1,'K'),(cells[2],owner,'A')]
            if count>=4:pieces.append((cells[3],1-owner,'B'))
            if count>=5:pieces.append((cells[4],owner,'B'))
            rules=make_rules(4,family,pieces,max_ply=8)
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
            row=dict(slot=slot,family=family,initial_pieces=count,extra_owner=owner,prefix=prefix,replicate=rep,status='NO_INPUT')
        else:
            start=time.perf_counter();teacher=solve_session(rules,session,1500)
            with torch.no_grad():
                graph=batch_graphs([graph_from_session(rules,session)])
                logits=[m(graph)[0].tolist() for m in models]
            row=dict(slot=slot,family=family,initial_pieces=count,extra_owner=owner,prefix=prefix,replicate=rep,
                     original_combination=(count==3+family%3 and owner==family//3),
                     rules=ruleset_to_dict(rules),record=record_value(session.to_record()),group=group,
                     teacher=teacher,status=teacher['status'],logits=logits,seconds=time.perf_counter()-start)
        rows.append(row)
        with (output/'results.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(row,separators=(',',':'))+'\n')
        if slot%36==0:print(json.dumps(dict(done=slot+1,seconds=time.perf_counter()-tick)),flush=True)
    conditions=[]
    for original in (True,False):
        subset=[r for r in rows if r.get('original_combination')==original]
        exact=[r for r in subset if r['status']=='EXACT']
        conditions.append(dict(original_combination=original,total=len(subset),
                               labels=dict(Counter(r['teacher']['label'] or 'UNKNOWN' for r in subset)),
                               models=[metrics(torch.tensor([r['logits'][seed] for r in exact]),torch.tensor([LABELS[r['teacher']['label']] for r in exact])) for seed in range(3)] if exact else []))
    result=dict(seconds=time.perf_counter()-tick,calls=len(rows),not_run=len(factors)-len(rows),stop=stop,conditions=conditions,
                limitation='Finite8-ply exact subset only; UNKNOWN selection is not random;216fresh slots across108factor cells give small class support. Frozen model diagnostic, no retraining/transfer/play.')
    write_record(output/'summary.json',result);print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--output',required=True);p.add_argument('--seconds',type=float,default=180)
    a=p.parse_args();run(a.base,a.output,a.seconds)
