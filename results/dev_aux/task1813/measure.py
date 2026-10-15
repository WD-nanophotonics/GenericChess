"""Immediate real claim boundary cost; zero Native/training game calls."""
import json,time,statistics,hashlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from generic_chess.rules import build_western_chess_ruleset,build_standard_shogi_ruleset
from generic_chess.rules.schema import RuleDeclaration
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
import scripts.generic_session_win_proof as m

def fixtures():
    for name,rs in [('KRK4',krk_ruleset(4)),('CHESS8',build_western_chess_ruleset()),('SHOGI9',build_standard_shogi_ruleset())]:
        claim=RuleDeclaration('actual_win',0,require_not_in_check=False,failure_outcome='WIN')
        yield name,GameSession(compile_ruleset_for_execution(replace(rs,declarations=(claim,))))

def run(destination):
    result={'repetitions':20,'order':'alternating fixture order each repetition; proof then verifier; after comparison counterbalanced',
      'new_native_go':0,'training_games':0,'scope':'actual immediate declaration WIN, root record replay and actual public execution; not a mate-search speedup',
      'source_sha256':hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest(),'rows':[]}
    cases=list(fixtures());original=GameSession.legal_actions
    for repeat in range(result['repetitions']):
        for name,s in cases[::(-1 if repeat%2 else 1)]:
            counts={'calls':0,'seconds':0.}
            def measured(current):
                start=time.perf_counter();out=original(current)
                counts['calls']+=1;counts['seconds']+=time.perf_counter()-start
                return out
            before=s.to_record()
            with patch.object(GameSession,'legal_actions',measured):
                t=time.perf_counter();proof=m.prove_session_win(s,max_depth=1,seconds=3.);ps=time.perf_counter()-t
                pc=counts.copy();counts.update(calls=0,seconds=0.)
                assert proof.status=='PROVEN_WIN' and proof.certificate.tree.rank==1
                t=time.perf_counter();verify=m.verify_session_certificate(s,proof.certificate,seconds=3.);vs=time.perf_counter()-t
                vc=counts.copy()
                assert verify['verified'] and s.to_record()==before
            result['rows'].append(dict(repeat=repeat,fixture=name,proof_seconds=ps,proof_frontier=pc,verification_seconds=vs,verification_frontier=vc,proof_nodes=proof.nodes,verification_nodes=verify['nodes']))
    result['summary']={name:{key:statistics.median(r[key] for r in result['rows'] if r['fixture']==name) for key in ['proof_seconds','verification_seconds']} for name,_ in cases}
    Path(destination).write_text(json.dumps(result,indent=2),encoding='utf-8')

if __name__=='__main__':
    import sys
    run(sys.argv[1])
