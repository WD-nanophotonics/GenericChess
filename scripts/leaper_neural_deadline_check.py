"""Clock-deadline diagnostic on already-labelled heldout decisive roots.

Conditioning on known decisive examples is explicit: this is NOT a fresh
representative data panel, training dataset or estimate of strength.
"""
from dataclasses import replace
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import time
import torch
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_neural_teacher import solve_session
from scripts.leaper_neural_model import LeaperValueNet,graph_from_session,batch_graphs
from scripts.research_record import write_record
from scripts.leaper_neural_experiment import LABELS


def run(base,output):
    base,output=Path(base),Path(output);output.mkdir(parents=True,exist_ok=False)
    data=json.loads(gzip.decompress((base/'dataset.json.gz').read_bytes()))['rows']
    selected=[r for r in data if r['label'] in ('WIN','LOSS') and (r['size']==5 or r['split']=='validation')]
    write_record(output/'plan.json',dict(question='Are5x5decisive prediction errors associated with longer required terminal deadlines than4x4?',
                selection='all45heldout4x4+19zero-shot5x5previouslyexact decisive roots; outcome-conditioned diagnosis only',
                shorter_remaining_clocks=[2,4,6],nodes=1500,seconds=120,training=0,
                decision='Compare earliest proven decisive deadline among correct/incorrect frozen predictions; preserve UNKNOWN and do not equate absence of proof with no winning strategy. No inference that larger GNN depth will fix errors.'))
    models=[];torch.set_num_threads(2)
    for seed in (0,1,2):
        ck=torch.load(base/f'value4-seed{seed}.pt',map_location='cpu',weights_only=True)
        m=LeaperValueNet(ck['hidden'],ck['rounds']);m.load_state_dict(ck['state_dict']);models.append(m.eval())
    tick=time.perf_counter();rows=[];stop=None
    for row in selected:
        if time.perf_counter()-tick>=120:stop='batch_cap';break
        original=ruleset_from_dict(row['rules']);c=compile_ruleset(original)
        s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
        with torch.no_grad():
            graph=batch_graphs([graph_from_session(original,s)])
            predictions=[int(m(graph).argmax(-1)[0]) for m in models]
        deadlines=[]
        original_remaining=original.max_ply-s.state.ply_count
        for remaining in (2,4,6):
            if remaining>=original_remaining:continue
            rules=replace(original,max_ply=s.state.ply_count+remaining);cc=compile_ruleset(rules)
            record=dict(row['record'],ruleset_fingerprint=cc.ruleset_fingerprint)
            session=GameSession.replay(cc,deserialize_game_record(json.dumps(record)))
            result=solve_session(rules,session,1500)
            if result['label'] not in (None,'DRAW',row['label']):raise ValueError('opposite decisive label under shorter clock')
            deadlines.append(dict(remaining=remaining,**result))
        deadlines.append(dict(remaining=original_remaining,label=row['label'],status='EXACT',basis='retained_original'))
        earliest=min(x['remaining'] for x in deadlines if x['label']==row['label'])
        result=dict(size=row['size'],slot=row['slot'],family=row['family'],label=row['label'],predictions=predictions,
                    correct=[p==LABELS[row['label']] for p in predictions],earliest_proven_deadline=earliest,deadlines=deadlines)
        rows.append(result)
        with (output/'results.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(result,separators=(',',':'))+'\n')
    summary=dict(seconds=time.perf_counter()-tick,roots=len(rows),not_run=len(selected)-len(rows),stop=stop,
                 strata=[dict(size=size,seed=seed,correct=correct,deadlines=dict(Counter(str(r['earliest_proven_deadline']) for r in rows if r['size']==size and r['correct'][seed]==correct)))
                         for size in (4,5) for seed in range(3) for correct in (True,False)],
                 limitation='Earliest of sampled proven deadlines, not exact distance-to-mate. Node-cap UNKNOWN can conceal earlier proof; original full histories retained. Outcome-conditioned diagnostic, no new representative accuracy claim.')
    write_record(output/'summary.json',summary);print(json.dumps(summary),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.base,a.output)
