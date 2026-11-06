"""Root-value-only teacher comparison on fixed existing inputs; no NN training."""
import argparse
from collections import Counter
import json
from pathlib import Path
import time
from scripts.leaper_neural_experiment import replay
from scripts.leaper_neural_teacher import solve_session
from scripts.leaper_neural_value_solver import solve_value
from scripts.research_record import write_record


def run(source,output,seconds=180):
    source,output=Path(source),Path(output);output.mkdir(parents=True,exist_ok=False)
    slots=[json.loads(x) for x in source.read_text().splitlines()][:72]
    write_record(output/'plan.json',dict(question='Can root-only interval proof obtain more exact WDL at comparable total cost than all-action threshold proof?',
                slots=72,selection='first72 randomized factorial slots, without outcome selection',nodes=1500,seconds=seconds,
                model_changes=0,training=0,player_search_changes=0,
                stop='Any conflicting exact labels invalidates candidate; retain censored/not-run. No old label replacement or panel refill.'))
    rows=[];tick=time.perf_counter();stop=None
    for i,row in enumerate(slots):
        if time.perf_counter()-tick>=seconds:stop='batch_cap';break
        rules,s=replay(row)
        order=('reference','root_value') if i%2==0 else ('root_value','reference')
        returns={}
        for method in order:
            start=time.perf_counter()
            result=solve_session(rules,s,1500) if method=='reference' else solve_value(rules,s,1500)
            returns[method]=dict(result,outer_seconds=time.perf_counter()-start)
        ref,cand=returns['reference'],returns['root_value']
        conflict=ref['label'] is not None and cand['label'] is not None and ref['label']!=cand['label']
        result=dict(slot=row['slot'],family=row['family'],initial_pieces=row['initial_pieces'],order=order,**returns,conflict=conflict)
        rows.append(result)
        with (output/'results.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(result,separators=(',',':'))+'\n')
        if conflict:stop='conflicting_exact_labels';break
    summary=dict(seconds=time.perf_counter()-tick,calls=len(rows),not_run=len(slots)-len(rows),stop=stop,
                 methods={name:dict(labels=dict(Counter(r[name]['label'] or 'UNKNOWN' for r in rows)),seconds=sum(r[name]['outer_seconds'] for r in rows),nodes=sum(r[name]['nodes'] for r in rows)) for name in ('reference','root_value')},
                 conflicts=sum(r['conflict'] for r in rows),extra_exact=sum(r['reference']['label'] is None and r['root_value']['label'] is not None for r in rows),
                 lost_exact=sum(r['reference']['label'] is not None and r['root_value']['label'] is None for r in rows),
                 limitation='Diagnostic reuses saved inputs for a new teacher comparison, not independent fitness data; equal node budgets do not imply equal wall cost or identical proof goals. Candidate does not certify all optimal actions. No NN retraining or player change.')
    write_record(output/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.source,a.output)
