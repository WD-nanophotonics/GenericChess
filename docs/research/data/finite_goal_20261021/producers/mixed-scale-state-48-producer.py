"""48 frozen diagnostic slots: material scale x existing state terms, six rules.

No training, WDL reference, new rule sample, Elo or activation. External40ply
truncation remains UNKNOWN. Static hand/board ratio.9 is a control, not endorsed.
"""
from pathlib import Path
from dataclasses import replace
from itertools import product
import json,random,time
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.benchmark.runner import play_game,RunConfig
from generic_chess.ai.benchmark.profiles import PROFILES
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from scripts.price_regions import CONFIG
from scripts.research_record import record_value,write_record
output=Path('artifacts/price-regions-20261021/mixed-scale-state-48.json')
if output.exists():raise FileExistsError(output)
source=json.loads(Path('docs/research/data/finite_roster_20261021/calibration-result.json').read_text())
seeds=[r['seed'] for r in source['rules']];plan=list(product(seeds,('A','B','C','D'),(0,1)));random.Random(2026102107).shuffle(plan)
report=dict(scope=__doc__,declaration=dict(planned_slots=48,slots=plan,shuffle_seed=2026102107,depth=2,q=0,tt=False,ordering=False,
    cells={'A':[1000,900,0,0],'B':[10,9,0,0],'C':[1000,900,2,5],'D':[10,9,2,5]},
    foe='AlwaysA,D2',backend='Core legality and Core semantic attacks, no Native requested',query_nodes=4096,query_seconds=.2,
    external_absolute_ply_cap=40,global_seconds=180,global_paid_nodes=2000000,
    decision='Exploratory cost/behavior/actual terminal bounds only; no refill, frozen cap extension or selecting coefficients from outcomes.'),setup=[],games=[])
write_record(output,report);start=time.perf_counter();deadline=start+180;paid=0;compiled={};profiles={}
for r in source['rules']:
    t=time.perf_counter();c=compile_ruleset_for_execution(ruleset_from_dict(r['definition']));p,_=build_semantic_opportunity_profile(c,CONFIG)
    compiled[r['seed']]=c;profiles[r['seed']]=p
    report['setup'].append(dict(seed=r['seed'],definition=r['definition'],seconds=time.perf_counter()-t))
class Bounded:
    def __init__(self,c,p,cell):
        scale,hand,mob,escape=report['declaration']['cells'][cell]
        table={t:0 if m.is_anchor else scale for t,m in c.support.type_metadata.items()};hands={t:0 if m.is_anchor else hand for t,m in c.support.type_metadata.items()}
        p=replace(p,board_value_by_type=table,hand_value_by_base_type=hands,promotion_gain_by_type={t:0 for t in table})
        cfg=replace(CONFIG,dynamic_mobility_weight=mob,anchor_escape_weight=escape)
        self.inner=AlphaBetaPlayer(c,evaluator_override=SemanticAttackEvaluator(c,p,cfg,backend='core'),use_disk_cache=False,use_tt=False,
            use_ordering=False,use_native_semantic_legality=False,tuning=SearchTuning(use_root_tactical=False));self.session=None
    def choose_action(self,s,limits):
        global paid
        if time.perf_counter()>=deadline or paid>=2000000:raise TimeoutError('declared global diagnostic cap')
        self.session=s;d=self.inner.choose_action(s,replace(limits,max_depth=2,max_time_seconds=min(.2,max(0.,deadline-time.perf_counter())),
            quiescence_max_depth=0,quiescence_hard_max_depth=0));paid+=d.nodes;return d
for seed,cell,owner in plan:
    row=dict(seed=seed,cell=cell,owner=owner);report['games'].append(row)
    if time.perf_counter()>=deadline or paid>=2000000:row['result']='missing';continue
    c=compiled[seed];p=profiles[seed];candidate=Bounded(c,p,cell);foe=Bounded(c,p,'A');t=time.perf_counter()
    try:
        outcome,events=play_game(c,(),f'{seed}-opening',f'{cell}-{owner}',owner,candidate,foe,
            RunConfig(PROFILES['baseline'],PROFILES['baseline'],(),seconds=.2,nodes=4096,max_plies=40))
        final=candidate.session or foe.session;assert final is not None
        assert GameSession.replay(c,final.to_record()).state==final.state
        row.update(outcome=record_value(outcome),events=record_value(events),record=json.loads(serialize_game_record(final.to_record())),
            terminal=record_value(final.state.terminal_status),replay_equal=True)
    except TimeoutError as exc:
        final=candidate.session or foe.session
        row.update(result='interrupted_unknown',error=str(exc),record=None if final is None else json.loads(serialize_game_record(final.to_record())))
    row['wall_seconds']=time.perf_counter()-t;write_record(output,report)
    print(len(report['games']),seed,cell,owner,row.get('outcome',row).get('result'),round(row['wall_seconds'],3),flush=True)
report.update(wall_seconds=time.perf_counter()-start,paid_nodes=paid);write_record(output,report)
print('done',len(report['games']),report['wall_seconds'],paid,flush=True)
