"""Select existing event frontier by largest saved q0 pushes, inspect q2 cost.

One Native-authority D2/8192node/5sec/q2-hard8 call, TT/order on, root/PVS/ordered
q off. Profiling overhead is within5sec, caps retained unknown. This is hotspot
localization, not a timing, strength or frozen-population extension comparison.
"""
import sys,json,time,cProfile,pstats,hashlib
from pathlib import Path
from unittest.mock import patch
root=Path.cwd();sys.path[:0]=[str(root)]
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.actions import action_from_dict
from generic_chess.session.session import GameSession
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.ai.limits import SearchLimits
from scripts.research_record import record_value,write_record
from scripts.unfamiliar_search import validate_pv
p=Path(__file__).parent;out=p/'event-qprofile.json';assert not out.exists()
prior=json.loads((p/'event-query-replay.json').read_bytes());selected=max(prior['cases'],key=lambda x:(x['searches'][0]['runtime_work']['runtime_pushes'],-x['seed'],-x['ply']))
inp=json.loads((root/'.local_agent/generated6-20261008/coverage.json').read_bytes());case=next(x for x in inp['cases'] if x['seed']==selected['seed']);c=compile_ruleset_for_execution(ruleset_from_dict(case['rules']));s=GameSession(c)
for step in case['route'][:selected['ply']]:s.submit(action_from_dict(step['action']))
cfg=EvaluationConfig(dynamic_mobility_weight=2,anchor_escape_weight=5,promotion_potential_weight=0);ev=SemanticAttackEvaluator(c,build_ruleset_profile(c,cfg),cfg,backend='native')
player=AlphaBetaPlayer(c,evaluator_override=ev,use_native_semantic_legality=True,tuning=SearchTuning(use_root_tactical=False));before=s.state;stats=[]
def make_stats():
 z=SearchStatistics();stats.append(z);return z
pr=cProfile.Profile();t=time.perf_counter()
with patch('generic_chess.ai.alphabeta.player.SearchStatistics',make_stats):
 pr.enable();dec=player.choose_action(s,SearchLimits(max_depth=2,max_nodes=8192,max_time_seconds=5,quiescence_max_depth=2,quiescence_hard_max_depth=8));pr.disable()
elapsed=time.perf_counter()-t;validate_pv(s,dec);assert s.state==before;assert stats[0].runtime_depth_balanced and stats[0].runtime_pushes==stats[0].runtime_pops
pr.dump_stats(str(p/'event-qprofile-private.prof'));ps=pstats.Stats(pr);top=[]
for (filename,line,name),(primitive,total,own,cumulative,callers) in sorted(ps.stats.items(),key=lambda x:x[1][3],reverse=True)[:25]:
 path=Path(filename)
 try:display=path.relative_to(root).as_posix()
 except ValueError:display=path.name
 top.append(dict(file=display,line=line,name=name,primitive_calls=primitive,total_calls=total,own_seconds=own,cumulative_seconds=cumulative))
write_record(out,dict(complete=True,declaration=__doc__,selected=dict(seed=selected['seed'],ply=selected['ply'],event=selected['event'],q0_pushes=selected['searches'][0]['runtime_work']['runtime_pushes']),decision=record_value(dec),seconds=elapsed,work=dict(pushes=stats[0].runtime_pushes,pops=stats[0].runtime_pops,balanced=True),top_cumulative=top,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),scope='Derived function paths exclude personal absolute paths; original binary profile retained privately. Cumulative times overlap; do not sum as independent percentages.'))
print(selected['seed'],selected['ply'],dec.completed_depth,dec.termination_reason,elapsed,[(z['name'],round(z['own_seconds'],3),round(z['cumulative_seconds'],3)) for z in top[:12]])
