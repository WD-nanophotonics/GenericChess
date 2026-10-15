"""Freeze a NEW public-session KRN root law, not a conversion of old roots."""
from dataclasses import replace
from pathlib import Path
import json,random,hashlib
from generic_chess.core.pieces import Piece,PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset,deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record,deserialize_game_record
from scripts.generic_proof_fixtures import krk_ruleset
from scripts.generic_proof_rnb_bridge import orbit,actor_state,uci
from scripts.generic_royal_actor import RoyalActor
from scripts.generic_win_proof import _same_state

OUT=Path('results/dev_aux/task1822')
def freeze():
    rng=random.Random(2026101559);actor=RoyalActor(4);roots=[];seen=set();attempts=0
    while len(roots)<32 and attempts<10000:
        attempts+=1;board=['.']*16
        for square,piece in zip(rng.sample(range(16),6),'KkRrNn'):board[square]=piece
        raw=tuple(board)+(0,)
        # Input-only legality/geometric filter, neither prices nor proof/WDL.
        if not all(actor.valid(tuple(board)+(side,)) for side in (0,1)):continue
        if any(actor.attacked(raw,actor.king(raw,side),1-side) for side in (0,1)):continue
        if len(actor.moves(raw))<4 or raw in seen:continue
        seen.update(orbit(raw));roots.append(raw)
    assert len(roots)==32
    n=PieceType('N','Leaper',tuple(LeapAtom(d) for d in ((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1))))
    def rows(raw):
        board=tuple(None if x=='.' else Piece(int(x.islower()),x.upper(),x.upper()) for x in raw[:-1])
        return tuple(tuple(board[i:i+4]) for i in range(0,16,4))
    rs=krk_ruleset(4);mask=(False,)*16
    rs=replace(rs,piece_types=rs.piece_types+(n,),initial_position=rows(roots[0]),
        initial_setup_options=tuple(RuleInitialSetupOption('family-'+str(i),rows(raw)) for i,raw in enumerate(roots[1:],1)),
        drop_allowed={'R':(mask,mask),'N':(mask,mask)},max_ply=96)
    text=serialize_ruleset(rs);c=compile_ruleset_for_execution(deserialize_ruleset(text));qualified=[]
    for i,raw in enumerate(roots):
        s=GameSession(c,None if i==0 else 'family-'+str(i));record=s.to_record()
        rebuilt=GameSession.replay(c,deserialize_game_record(serialize_game_record(record)))
        assert _same_state(s.state,rebuilt.state) and _same_state(s.result,rebuilt.result)
        assert actor_state(s.state)==raw and len(s.legal_actions())>=4
        assert sorted(uci(a) for a in s.legal_actions())==[a for a,_ in actor.moves(raw)]
        qualified.append(dict(family=i,phase='TRAIN' if i<16 else 'DEV',setup=record.initial_setup_key,
            root=list(raw),record=json.loads(serialize_game_record(record)),state_sha=hashlib.sha256(repr(s.state).encode()).hexdigest(),legal=len(s.legal_actions())))
    plan=dict(status='NEW_ROOT_LAW_QUALIFIED_NO_GAMES',seed=2026101559,attempts=attempts,
        source_base='5e374434bd64a993b531d3da9f1fa1a3ecc0368c',fingerprint=c.ruleset_fingerprint,
        rules_sha256=hashlib.sha256(text.encode()).hexdigest(),roots=qualified,
        mu='NEW uniform six-square KkRrNn placements, both kings uncheck, >=4side0 actions, D4+color orbit unique. Initialside0 only; roles TO_MOVE/OTHER equally weighted. No oldpaired-law equivalence or human-price claim.',
        changes='Explicit new six-piece default inventory and named layouts; old KRN imported-history plan unchanged. No invented prefix, turn1 or history reset.',
        exclusions='No drops/promotion/declarations in this scoped learning law; full-session semantic fixtures separately qualify those mechanisms.',
        labels_or_price_filter=False,native_go=0,games=0)
    with (OUT/'rules.json').open('x',encoding='utf-8') as f:f.write(text)
    with (OUT/'qualification.json').open('x',encoding='utf-8') as f:json.dump(plan,f,indent=2)
    print(json.dumps(dict(qualified=len(qualified),attempts=attempts,fingerprint=c.ruleset_fingerprint)))
if __name__=='__main__':freeze()
