"""Bounded all-continuation truth on frozen near-clock canonical histories.

Streams complete GameStates, without a Position quotient, graph expansion,
policy rollout or oracle-selected experiential training start. Exact outcome
sets are emitted only after all Core legal continuations close. Partial trees
remain UNKNOWN and the batch has one cumulative work budget.
"""
from __future__ import annotations

import argparse
from collections import Counter
import time
from pathlib import Path

from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_explorer_truth import load, save, digest, materialize
from scripts.leaper_microgames import role_stop_requested


class Limit(RuntimeError):
    pass


class SuffixTree:
    def __init__(self, *, nodes=1000000, seconds=900):
        self.limit=nodes;self.seconds=seconds;self.began=time.perf_counter()
        self.nodes=0;self.edges=0;self.last_stop=0.;self.terminals=Counter()

    def solve(self,state,compiled):
        now=time.perf_counter()
        if self.nodes>=self.limit:raise Limit('NODE_CAP_UNKNOWN')
        if now-self.began>=self.seconds:raise Limit('TIME_CAP_UNKNOWN')
        if now-self.last_stop>=.2:
            self.last_stop=now
            if role_stop_requested():raise Limit('USER_STOP')
        self.nodes+=1
        terminal=state.terminal_status
        if terminal.is_terminal:
            self.terminals[terminal.status.value]+=1
            v=0 if terminal.winner is None else 1 if terminal.winner==0 else -1
            return frozenset((v,)),v,None
        outcomes=set();values=[];branches=[];witness=None
        for ac,ch in legal_successors(state,compiled):
            self.edges+=1
            future,v,path=self.solve(ch,compiled)
            outcomes.update(future);values.append(v)
            branches.append(dict(action=action_to_dict(ac),wdl_player0=v,
                                 terminal_outcomes_player0=sorted(future)))
            if witness is None and future-{0}:
                # A terminal decisive child uses an empty suffix.
                witness=[action_to_dict(ac)]+(path or [])
        if not branches:raise ValueError('ongoing Core state has no legal successors')
        value=(max if state.position.side_to_move==0 else min)(values)
        return frozenset(outcomes),value,witness


def run(folder,output):
    p=Path(folder);out=Path(output);out.mkdir(parents=True,exist_ok=False)
    original=load(p/'truth.json.gz')
    truth=materialize(original,load(p/'cooperative.json'),load(p/'observed-suffixes.json.gz'))
    candidates=sorted((r for r in truth['roots'] if r['cooperative_decisive'] is None
                      and 8<=r['rule_remaining']<=12),key=lambda r:r['id'])[:24]
    spec=dict(format='leaper-suffix-truth-v1',source_truth_digest=digest(original),
          materialized_digest=digest(truth),source_sha='c7e7b84101ee286a4d3bc98a19a33463afd2809d',
          selection='First24 full-history SHA order among existing cooperative-UNKNOWN histories with8..12 actual ruleplies remaining, after free suffix/nonzero-WDL/certificate consequences. No output/adaptive extension; diagnostics only.',
          selected=[r['id'] for r in candidates],caps=dict(nodes=1000000,seconds=900),
          question='Can finite clock suffixes give claim-sufficient universal outcome truth without graph closure or minimax-DRAW conflation?',
          memory='Streaming DFS depth at most12; no full history/Position cache.',
          stop='One cumulative node/time budget for all24; unfinished and unstarted roots stay UNKNOWN, no refill or replacement.')
    save(out/'spec.json',spec)
    tree=SuffixTree(**spec['caps']);rows=[];compiled={};status='COMPLETE'
    for r in candidates:
        fp=r['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        c=compiled[fp];_,s=root_session(truth,r['id'],c)
        start=time.perf_counter();before=tree.nodes;edges=tree.edges
        try:future,value,witness=tree.solve(s.state,c)
        except Limit as error:
            status=str(error)
            rows.append(dict(id=r['id'],status=status,cooperative_decisive=None,
                             universal_draw=None,nodes=tree.nodes-before,edges=tree.edges-edges,
                             seconds=time.perf_counter()-start))
            break
        sign=1 if s.state.position.side_to_move==0 else -1
        if r['wdl_bounds'][0]==r['wdl_bounds'][1]:
            assert sign*value==r['wdl_bounds'][0]
        if witness is not None:
            from generic_chess.core.actions import action_from_dict
            _,check=root_session(truth,r['id'],c)
            for ac in witness:check.submit(action_from_dict(ac))
            assert check.result.winner is not None
        rows.append(dict(id=r['id'],fingerprint=fp,status='COMPLETE',
             remaining=r['rule_remaining'],terminal_outcomes_player0=sorted(future),
             wdl_player0=value,cooperative_decisive=bool(future-{0}),
             universal_draw=future=={0},singleton_outcome=len(future)==1,witness=witness,
             nodes=tree.nodes-before,edges=tree.edges-edges,seconds=time.perf_counter()-start))
        save(out/'partial.json',dict(spec=spec,rows=rows,status='RUNNING'))
    result=dict(format='leaper-suffix-truth-result-v1',spec=spec,status=status,rows=rows,
          nodes=tree.nodes,edges=tree.edges,terminal_reason_visits=dict(tree.terminals),
          seconds=time.perf_counter()-tree.began,
          unstarted=spec['selected'][len(rows):],
          scope='All continuations of COMPLETE roots only. Repeated visits are computation counts, not independent samples or global history coverage. No new graph, games, E0, training or source-label replacement.')
    save(out/'result.json',result)
    return result


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--folder',default='docs/research/data/leaper_explorer_truth_20261023');cli.add_argument('--output',required=True)
    args=cli.parse_args();r=run(args.folder,args.output)
    print(__import__('json').dumps({k:r[k]for k in('status','nodes','edges','seconds','unstarted')}))
