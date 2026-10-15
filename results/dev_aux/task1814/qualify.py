"""Existing input-only1803root bridge qualification; no Native or learning."""
import json,hashlib
from dataclasses import replace
from pathlib import Path
from generic_chess.rules.schema import RuleSet
from generic_chess.session.session import GameSession
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,actor_state
from scripts.generic_session_setup import fresh_setup_session

def run():
    path=Path('results/dev_aux/task1803/plan.json');plan=json.loads(path.read_text(encoding='utf-8'))
    compiled=compile_rnb();base=replace(krk_ruleset(4),piece_types=compiled.piece_types,drop_allowed=compiled.drop_allowed,max_ply=96,repetition_limit=3)
    # Only first existing input family, not selected on outcome or price.
    roots=plan['families'][0]['roots'];rows=[]
    for color,raw in enumerate(roots):
        state=from_actor(compiled,tuple(raw))
        try:
            extended,session=fresh_setup_session(base,state,setup_key='existing1803_family0_color'+str(color))
        except ValueError as error:
            rows.append(dict(color=color,source_side=state.position.side_to_move,status='UNSUPPORTED_EXACT_FRESH_SETUP',reason=str(error)));continue
        record=session.to_record();replayed=GameSession.replay(session.compiled,record)
        assert actor_state(session.state)==tuple(raw) and replayed.state==session.state and record.schema_version==3
        assert session.state.ply_count==0 and len(session.state.history)==1
        rows.append(dict(color=color,source_side=state.position.side_to_move,status='EXACT_PUBLIC_RECORD_REPLAY',schema=record.schema_version,key=record.initial_setup_key,source_fingerprint=compiled.ruleset_fingerprint,new_fingerprint=session.compiled.ruleset_fingerprint,history_records=len(session.state.history),actions=len(record.actions)))
    result=dict(source=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),first_input_family=0,rows=rows,new_native_go=0,training_games=0,interpretation='both existing KRN roots are rejected because named options must preserve default KRK inventory; no bypass or default rewrite. Separately schema cannot encode fresh turn1. Existing immutable-state platform remains valid, this optional Session bridge is not admitted for the balanced1803 distribution.')
    Path(__file__).with_name('qualification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':run()
