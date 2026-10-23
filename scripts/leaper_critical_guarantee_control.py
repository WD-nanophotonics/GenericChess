"""One new literal Session control: guarantee loss is not irreversible result.

Inputs are exposed diagnostic histories; no training or new physical game.
No previous certificate cap is continued. A failed new proof stays UNKNOWN.
"""
import argparse
import json
import time
from pathlib import Path

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_explorer_truth import load, save, digest
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested
from scripts.generic_session_win_proof import prove_session_win, verify_session_certificate
from scripts.generic_session_certificate_json import export_session_certificate


def run(truth):
    candidates=sorted((r for r in truth['critical_observed']if r['chosen_wdl']==-1 and r['eventual_mover_payoff']==1),key=lambda r:(r['id'],r['record_id']))
    chosen=candidates[0]
    source=truth['records'][chosen['record_id']]
    record=source|dict(actions=source['actions'][:chosen['ply']+1])
    c=compile_rule(ruleset_from_dict(truth['rules'][source['ruleset_fingerprint']]))
    session=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
    old=next(r for r in truth['roots']if r['id']==state_sha(session.state))
    assert old['wdl_bounds']==[1,1]
    target=session.state.position.side_to_move
    last=0.
    def cancel():
        nonlocal last
        now=time.perf_counter()
        if now-last>=.2:
            last=now
            return role_stop_requested()
        return False
    spec=dict(question='Can the opponent force WIN after an actual bad move whose actual subsequent record nevertheless wins for the original mover?',
              selection='Lexicographically first existing critical-history SHA with chosenLOSS but actual moverWIN; exposed diagnostic, never TRAIN.',
              caps=dict(nodes=50000,seconds=300,depth=9),cheaper_alternative='Use existing scoped graph rank9 label; this separate finite Session proof tests literal history binding.',
              stop='One query; no refill or enlargement if UNKNOWN. No new physical game.')
    proof=prove_session_win(session,target=target,max_nodes=50000,seconds=300,max_depth=9,cancel=cancel)
    result=dict(format='leaper-critical-guarantee-control-v1',spec=spec,source_truth_digest=digest(truth),chosen=chosen,
                child_id=old['id'],child_record=record,target=target,status=proof.status,reason=proof.reason,
                nodes=proof.nodes,seconds=proof.seconds,completed_depth=proof.completed_depth,certificate=None,verification=None,
                source_code=Path(__file__).read_text(encoding='utf-8'))
    if proof.certificate is not None:
        result['certificate']=export_session_certificate(session,proof.certificate,max_nodes=65536)
        result['verification']=verify_session_certificate(session,proof.certificate,max_nodes=65536,seconds=120,cancel=cancel)
        assert result['verification']['verified']
    # The retained complete record establishes an actual continuation with
    # the opposite winner; a complete all-defense proof establishes that it
    # was avoidable. Neither is a new policy trial or piece-price benefit.
    final=GameSession.replay(c,deserialize_game_record(json.dumps(source)))
    assert final.result.winner==1-target
    result['observed_opposite_terminal']=dict(status=final.result.status.value,winner=final.result.winner)
    return result


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--truth',required=True);cli.add_argument('--output',required=True);args=cli.parse_args()
    out=run(load(args.truth));save(args.output,out)
    print(json.dumps({k:out[k]for k in ('status','reason','nodes','seconds','completed_depth')}))


if __name__=='__main__':main()
