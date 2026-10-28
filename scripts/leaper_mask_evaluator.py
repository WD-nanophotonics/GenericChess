"""Research-only exact default evaluation using existing compiled Leap targets.

The tables/geometry are BASELINE. This replaces per-atom Square-set unions in
static evaluation with integer unions and one board pass; it changes no moves,
Core adjudication, search tree, TT bound, price or evaluation weight.
"""
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.movement import LeapAtom
from generic_chess.core.errors import ensure_ruleset_match

class PureLeaperMaskEvaluator:
 def __init__(self,compiled,base,*,shadow=False):
  n=compiled.board_size;cells=n*n;types=compiled.piece_types
  if type(base) is not Evaluator or base._compiled is not compiled or _plain_leaper_hash_patterns(compiled) is None:raise ValueError('certified plain-Leaper default evaluator required')
  if cells>256 or 2*len(types)*cells>65536:raise ValueError('scoped mask memory admission exceeded')
  if any(not isinstance(a,LeapAtom) for t in types for a in t.movement_atoms) or base._zones:raise ValueError('all-Leap atoms/no promotion bonus required')
  self.base=base;self.compiled=compiled;self.shadow=shadow;self.n=n;self.cells=cells;self.anchors={t.type_id for t in types if t.is_anchor};self.metrics=dict(requests=0,fast_calls=0,fallback_calls=0,reference_checks=0,mask_unions=0)
  def mask(squares):
   result=0
   for sq in squares:result|=1<<(sq.rank*n+sq.file)
   return result
  self.attacks={t.type_id:tuple(tuple(mask(xs) for xs in rows) for rows in compiled.empty_mobility[t.type_id]) for t in types}
  self.steps={tid:tuple(tuple(mask(xs) for xs in rows) for rows in owners) for tid,owners in base._anchor_steps.items()}
 def __getattr__(self,name):return getattr(self.base,name)
 def evaluate(self,state):
  m=self.metrics;m['requests']+=1;pos=state.position
  if len(pos.board)!=self.cells:m['fallback_calls']+=1;return self.base.evaluate(state)
  cfg=self.base._config;profile=self.base._profile;need=bool(cfg.dynamic_mobility_weight or cfg.anchor_escape_weight)
  if need:ensure_ruleset_match(pos,self.compiled)
  score=0;attacks=[0,0];anchor=[None,None];occupied=0
  for idx,p in enumerate(pos.board):
   if p is None:continue
   owner=p.owner;tid=p.current_type_id;v=profile.board_value_by_type[tid];score+=v if owner==0 else -v
   if need:attacks[owner]|=self.attacks[tid][owner][idx];m['mask_unions']+=1
   if cfg.anchor_escape_weight:
    occupied|=1<<idx
    if tid in self.anchors and anchor[owner] is None:anchor[owner]=idx
  for owner,hand in enumerate(pos.hands):
   for tid,count in hand.counts:
    v=count*profile.hand_value_by_base_type[tid];score+=v if owner==0 else -v
  if cfg.dynamic_mobility_weight:score+=cfg.dynamic_mobility_weight*(attacks[0].bit_count()-attacks[1].bit_count())
  if cfg.anchor_escape_weight:
   for owner,idx in enumerate(anchor):
    if idx is None:continue
    sign=1 if owner==0 else -1;opponent=attacks[1-owner];tid=pos.board[idx].current_type_id
    score+=sign*cfg.anchor_escape_weight*(self.steps[tid][owner][idx]&~(occupied|opponent)).bit_count()
    if opponent&(1<<idx):score-=sign*cfg.anchor_escape_weight*10
  value=score if pos.side_to_move==0 else -score;m['fast_calls']+=1
  if self.shadow:
   expected=self.base.evaluate(state);m['reference_checks']+=1
   if value!=expected:raise AssertionError('mask/default raw static evaluation mismatch')
  return value
