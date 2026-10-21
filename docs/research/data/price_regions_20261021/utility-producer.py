"""Posthoc four-slot utility check on one already exposed price-region root."""
from dataclasses import replace
from pathlib import Path
import json,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from scripts.price_regions import CONFIG
from scripts.research_record import write_record,record_value

source=json.loads(Path('artifacts/price-regions-20261021/d3-mechanism.json').read_text())['cases'][0]
compiled=compile_ruleset_for_execution(ruleset_from_dict(source['rule']))
root=source['roots'][2]
record=deserialize_game_record(json.dumps(root['record']))
profile,_=build_semantic_opportunity_profile(compiled,CONFIG)
output=Path('artifacts/price-regions-20261021/utility-four-slots.json')
report=dict(posthoc=True,question='Does the D3 action-region difference versus Unit change an actual terminal on the exposed ply8 root?',
    declaration=dict(slots=4,root_seed=732005,prefix=8,candidate_tables=['profile','unguarded_profile'],
        candidate_owners=[0,1],fixed_foe=dict(K=0,H=1000,B=1000),depth=3,nodes=4096,
        move_seconds=.1,total_seconds=90,absolute_ply_cap=72,q=0,tt=False,ordering=False,
        decision='Exploratory mechanism only. Any unresolved slot stays UNKNOWN; no extension, holdout/strength claim or adoption.'),
    games=[])
write_record(output,report)
deadline=time.perf_counter()+90

class BoundedPlayer:
    def __init__(self,table):
        p=replace(profile,board_value_by_type=table,hand_value_by_base_type={t:0 for t in table},
                  promotion_gain_by_type={t:0 for t in table})
        self.player=AlphaBetaPlayer(compiled,evaluator_override=Evaluator(compiled,p,CONFIG),
            use_disk_cache=False,use_tt=False,use_ordering=False,use_native_semantic_legality=False,
            tuning=SearchTuning(use_root_tactical=False))
        self.session=None
    def choose_action(self,session,limits):
        if time.perf_counter()>=deadline:raise TimeoutError('global90sec utility cap')
        self.session=session
        return self.player.choose_action(session,replace(limits,max_depth=3,quiescence_max_depth=0,
            quiescence_hard_max_depth=0,max_time_seconds=min(.1,max(0.,deadline-time.perf_counter()))))

start=time.perf_counter()
for label in ('profile','unguarded_profile'):
    for owner in (0,1):
        slot=dict(table=label,owner=owner)
        report['games'].append(slot)
        if time.perf_counter()>=deadline:
            slot['result']='missing';continue
        candidate=BoundedPlayer(source[label]);foe=BoundedPlayer({'K':0,'H':1000,'B':1000})
        try:
            outcome,events=play_game(compiled,record.actions,'exposed732005-ply8',f'{label}-{owner}',owner,
                candidate,foe,RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=.1,nodes=4096,max_plies=72))
            final=candidate.session or foe.session
            assert final is not None
            replay=GameSession.replay(compiled,final.to_record())
            assert replay.state==final.state
            slot.update(outcome=record_value(outcome),events=record_value(events),
                record=json.loads(serialize_game_record(final.to_record())),
                terminal=record_value(final.state.terminal_status),replay_equal=True)
        except TimeoutError as exc:
            slot.update(result='interrupted_unknown',error=str(exc))
        write_record(output,report)
report['wall_seconds']=time.perf_counter()-start
write_record(output,report)
print([(g['table'],g['owner'],g.get('outcome',g).get('result'),g.get('terminal')) for g in report['games']])
print({'seconds':report['wall_seconds']})
