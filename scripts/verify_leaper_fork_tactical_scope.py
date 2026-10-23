"""Replay the closed natural corpus for the bounded tactical mechanism table."""
import argparse,json,time
from pathlib import Path
from scripts.leaper_fork_tactical_scope import source_truth,classify,add_floor_summary
from scripts.leaper_explorer_truth import load,save,digest
from scripts.verify_leaper_single_parity import without_cost


def verify(path):
    start=time.perf_counter();expected=load(path);truth=source_truth()
    context=load('docs/research/data/leaper_explorer_truth_20261023/source-context.json.gz')
    actual=add_floor_summary(classify(truth,context),truth)
    if without_cost(actual)!=without_cost(expected):raise ValueError('natural fork/FLOOR reconstruction differs')
    return dict(verified=True,source_truth_digest=digest(truth),histories=len(actual['histories']),
        record_actions=len(actual['events']),summary=actual['summary'],
        uniform_known_fork_mu_FLOOR=actual['uniform_known_fork_mu_FLOOR'],cost=actual['cost'],
        seconds=time.perf_counter()-start,
        scope='Fresh public record/Core replay through the maintained classification and exact arithmetic. Reproduces this retrospective table,not an independent game engine or new proof of all imported WDL labels. Parenttruth/caps remain qualified.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--packet',type=Path,default=Path('docs/research/data/leaper_single_parity_20261023/natural-fork-scope.json.gz'));cli.add_argument('--output',required=True)
    args=cli.parse_args();r=verify(args.packet);save(args.output,r);print(json.dumps(r))
