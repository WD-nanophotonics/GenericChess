"""Recompute saved default static request integers; no search/source capsules."""
from pathlib import Path
from types import SimpleNamespace
from collections import deque
from scripts.verify_leaper_forced_continuation import load,key
from scripts import leaper_design as L
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig,config_hash
from generic_chess.ai.evaluation.profile import RuleSetEvaluationProfile,PieceValueProfile
from scripts.leaper_eval_cache_feasibility import frozen_profile

def position(x):
 return Position(board=tuple(None if p is None else Piece(**p)for p in x['board']),hands=tuple(Hands(tuple(tuple(v)for v in h['counts']))for h in x['hands']),side_to_move=x['side_to_move'],ruleset_fingerprint=x['ruleset_fingerprint'],aux_state=tuple((tuple(v[0]),tuple(v[1])if isinstance(v[1],list)else v[1])for v in x.get('aux_state',[])),board_width=x.get('board_width'),board_height=x.get('board_height'))

def assess(directory):
 d=Path(directory);data=load(d/'inputs.json');plan=load(d/'plan.json');cases={c['key']:c for c in data['cases']};out=[]
 for name,c in cases.items():
  trace=load(d/(name+'-sequence.json'));compiled=L.compile_rule(L.ruleset_from_dict(data['rules'][c['rule_sha256']]));p=dict(trace['profile']);p['piece_profiles']={k:PieceValueProfile(**v)for k,v in p['piece_profiles'].items()};config=EvaluationConfig(**{k:tuple(v)if isinstance(v,list)else v for k,v in trace['config'].items()});profile=RuleSetEvaluationProfile(**p);assert profile.ruleset_fingerprint==compiled.ruleset_fingerprint and profile.config_hash==config_hash(config);e=Evaluator(compiled,frozen_profile(profile),config);pp=[position(x)for x in trace['positions']];assert len(set(pp))==len(pp);values=[e.evaluate(SimpleNamespace(position=p))for p in pp];cache=set();fifo=deque();hits=evictions=0
  for r in trace['requests']:
   i=r['id'];assert 0<=i<len(values)and values[i]==r['raw']
   if i in cache:hits+=1
   else:
    if len(cache)>=plan['capacity']:cache.remove(fifo.popleft());evictions+=1
    cache.add(i);fifo.append(i)
  out.append(dict(key=name,requests=len(trace['requests']),unique_positions=len(pp),finite_hits=hits,evictions=evictions,raw_integers_recomputed=True))
 return dict(queries=0,unique_static_evaluations=sum(x['unique_positions']for x in out),rows=out,scope='Recomputed static integers with frozen published profiles/Core geometry; no search, all-defense solver or strength claim.')
