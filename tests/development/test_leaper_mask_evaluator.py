"""Compare mask arithmetic with the independent Square-set default evaluator."""
import gzip,json,random
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.cache import EvaluationProfileCache
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.errors import RuleSetMismatchError
from generic_chess.core.movement import RayAtom
from scripts.leaper_pvs_quality_pilot import make_session
from scripts.leaper_mask_evaluator import PureLeaperMaskEvaluator

@pytest.mark.parametrize('weights',[(2,5,3),(0,0,0),(0,5,3),(2,0,3),(-2,-5,3)])
def test_generated_occupancies_hands_sides_and_multiple_anchors(weights):
 rows=json.loads(gzip.decompress(Path('docs/research/data/leaper_check_extension_20261028/initial/inputs.json.gz').read_bytes()))['rows'];rng=random.Random(20261029)
 for index in (0,4,8,12,16,20):
  c,s=make_session(rows[index]);cfg=EvaluationConfig(dynamic_mobility_weight=weights[0],anchor_escape_weight=weights[1],promotion_potential_weight=weights[2]);profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);base=Evaluator(c,profile,cfg);fast=PureLeaperMaskEvaluator(c,base);ids=[x.type_id for x in c.piece_types];handids=[x for x in ids if not c.types_by_id[x].is_anchor]
  for k in range(48):
   board=[]
   for j in range(c.board_size**2):
    tid=rng.choice(ids);board.append(None if rng.random()<(k%6)/6 else Piece(rng.randrange(2),tid,tid))
   hands=tuple(Hands(tuple((tid,rng.randrange(4)) for tid in handids)) for _ in range(2))
   pos=replace(s.state.position,board=tuple(board),hands=hands,side_to_move=k%2);state=SimpleNamespace(position=pos)
   assert fast.evaluate(state)==base.evaluate(state),(index,weights,k)
  assert fast.metrics['fast_calls']==48 and fast.metrics['fallback_calls']==0


def test_source_history_positions_and_fingerprint_error():
 rows=json.loads(gzip.decompress(Path('docs/research/data/leaper_check_extension_20261028/resource/inputs.json.gz').read_bytes()))['rows']
 c,s=make_session(rows[0]);cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);base=Evaluator(c,profile,cfg);fast=PureLeaperMaskEvaluator(c,base,shadow=True)
 assert fast.evaluate(s.state)==base.evaluate(s.state)
 for a in s.legal_actions():
  child=type(s).replay(c,s.to_record());child.submit(a)
  assert fast.evaluate(child.state)==base.evaluate(child.state)
 assert fast.metrics['reference_checks']==fast.metrics['requests']
 foreign=SimpleNamespace(position=replace(s.state.position,ruleset_fingerprint='foreign'))
 with pytest.raises(RuleSetMismatchError):fast.evaluate(foreign)
 with pytest.raises(RuleSetMismatchError):base.evaluate(foreign)


def test_reject_ray_atoms_even_if_executable_IR_was_plain():
 rows=json.loads(gzip.decompress(Path('docs/research/data/leaper_check_extension_20261028/resource/inputs.json.gz').read_bytes()))['rows'];c,s=make_session(rows[0]);legacy=replace(c._legacy_compiled,piece_types=tuple(replace(t,movement_atoms=t.movement_atoms+(RayAtom((1,0)),)) if i==0 else t for i,t in enumerate(c.piece_types)));changed=replace(c,_legacy_compiled=legacy);cfg=EvaluationConfig();profile,_=EvaluationProfileCache(use_disk=False).get_or_build(c,cfg);base=Evaluator(changed,profile,cfg)
 with pytest.raises(ValueError,match='Leap'):PureLeaperMaskEvaluator(changed,base)
