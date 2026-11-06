"""Small resident-model cost check; excludes replay and reports it separately."""
import gzip,json,time
from pathlib import Path
import torch
from scripts.leaper_neural_experiment import replay
from scripts.leaper_neural_model import LeaperValueNet,graph_from_session,batch_graphs
from scripts.research_record import write_record


def run(base):
    base=Path(base);raw=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    rows=[r for n in (4,5) for r in [x for x in raw if x['size']==n][32:48]]
    ck=torch.load(base/'value4-seed0.pt',map_location='cpu',weights_only=True)
    m=LeaperValueNet(ck['hidden'],ck['rounds']);m.load_state_dict(ck['state_dict']);m.eval();torch.set_num_threads(2)
    results=[]
    for row in rows:
        start=time.perf_counter();r,s=replay(row);replay_seconds=time.perf_counter()-start
        start=time.perf_counter();g=graph_from_session(r,s);b=batch_graphs([g]);graph_seconds=time.perf_counter()-start
        with torch.no_grad():
            start=time.perf_counter();m(b);forward_seconds=time.perf_counter()-start
            start=time.perf_counter();m.probabilities(r,s);value_seconds=time.perf_counter()-start
        results.append(dict(size=row['size'],slot=row['slot'],replay_seconds=replay_seconds,graph_seconds=graph_seconds,resident_forward_seconds=forward_seconds,full_value_seconds=value_seconds))
    summary={str(n):{k:dict(median=float(torch.tensor([x[k] for x in results if x['size']==n],dtype=torch.float64).median()),max=max(x[k] for x in results if x['size']==n))
                    for k in ('replay_seconds','graph_seconds','resident_forward_seconds','full_value_seconds')} for n in (4,5)}
    report=dict(contexts=results,summary=summary,python='3.12.14',torch=str(torch.__version__),
                scope='Resident CPU model,2torchthreads,fresh Core replay per context; full_value_seconds includes graph/batch/forward/Core terminal check but excludes replay.32fixed slots32..47per size. Warmup outliers retained. Not ABP choose_action cost or strength.',
                prior_failure='Initial64costcalls onslots0..31per size were measured but serialization rejected TorchVersion(strsubclass); timing returns not preserved and remainUNKNOWN. These32newcontexts are disjoint, not replacement measurements.')
    write_record(base/'standalone-cost.json',report);print(json.dumps(summary))

if __name__=='__main__':
    import sys;run(sys.argv[1])
