"""Additional static-contract cases, not legal-game/truth/strength samples."""
import gzip,json
from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.pieces import Piece
from scripts.leaper_mask_evaluator import PureLeaperMaskEvaluator


def test_asymmetric_owner_frames_duplicates_long_leaps_and_anchor_short_subset():
 sources=[json.loads(gzip.decompress(Path('docs/research/data/leaper_quiet_witness_20261029/candidate.json.gz').read_bytes()))['RuleSet'],json.loads(gzip.decompress(Path('docs/research/data/leaper_check_extension_20261028/initial/inputs.json.gz').read_bytes()))['rows'][0]['RuleSet']]
 for source in sources:
  rule=json.loads(json.dumps(source));rule.pop('initial_setup_options',None);rule['metadata']={};n=rule['board_size'];board=[[None]*n for _ in range(n)]
  for owner,tid,x,y in ((0,'K',0,0),(1,'K',n-1,n-1),(0,'A',0,1)):board[y][x]=dict(owner=owner,base_type_id=tid,current_type_id=tid,promoted=False)
  rule['initial_position']=board
  for t in rule['piece_types']:
   if t['type_id']=='A':t['movement_atoms']=[dict(kind='leap',offset=[1,0]),dict(kind='leap',offset=[1,0]),dict(kind='leap',offset=[40,17])]
   if t['type_id']=='K':t['movement_atoms']=[dict(kind='leap',offset=[1,0]),dict(kind='leap',offset=[2,1])]
  c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule));cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);base=Evaluator(c,profile,cfg);fast=PureLeaperMaskEvaluator(c,base)
  for owner in (0,1):
   for tid in ('K','A'):
    for square in range(c.board_size**2):
     board=[None]*(c.board_size**2);board[square]=Piece(owner,tid,tid);pos=replace(c.initial_position,board=tuple(board),side_to_move=owner);state=SimpleNamespace(position=pos)
     assert fast.evaluate(state)==base.evaluate(state),(c.board_size,owner,tid,square)
  assert fast.metrics['fallback_calls']==0
