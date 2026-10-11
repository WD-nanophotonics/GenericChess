"""Private aligned evaluator adapter; specialized conversion is charged."""
from pathlib import Path
from types import SimpleNamespace
import sys,time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.search_backend_comparison import CoreBoard,ChessBoard,ShogiBoard,VALUES
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig,config_hash
from generic_chess.ai.evaluation.profile import PieceValueProfile,RuleSetEvaluationProfile

def weighted(compiled,values):
 cfg=EvaluationConfig(dynamic_mobility_weight=2,anchor_escape_weight=5,promotion_potential_weight=3)
 gains={pt.type_id:max(0,max((values[t] for t in pt.promotion_target_ids),default=0)-values[pt.type_id]) for pt in compiled.piece_types}
 profile=RuleSetEvaluationProfile(compiled.ruleset_fingerprint,1,'frozen-attribution-values',config_hash(cfg),{pt.type_id:PieceValueProfile(pt.type_id,'fixed-control',0.,values[pt.type_id],values[pt.type_id],gains[pt.type_id],0.,0.,pt.is_anchor,pt.is_promotable) for pt in compiled.piece_types},3000,values,values,gains)
 return Evaluator(compiled,profile,cfg)

def position_from_snapshot(snapshot,compiled):
 cells,hands,side,aux,ply=snapshot
 pos=Position(tuple(None if x is None else Piece(*x) for x in cells),tuple(Hands(h) for h in hands),side,compiled.ruleset_fingerprint,aux)
 return SimpleNamespace(position=pos,ply_count=ply)

class WeightedMixin:
 def __init__(self,case,evaluator,*,measure=False):
  super().__init__(case);self.evaluator=evaluator;self.measure=measure;self.eval_calls=0;self.adapter_seconds=0.;self.eval_seconds=0.
 def evaluate(self):
  if not self.measure:return self.evaluator.evaluate(position_from_snapshot(self.snapshot(),self.evaluator._compiled))
  start=time.perf_counter();state=position_from_snapshot(self.snapshot(),self.evaluator._compiled);prepared=time.perf_counter();value=self.evaluator.evaluate(state);end=time.perf_counter();self.eval_calls+=1;self.adapter_seconds+=prepared-start;self.eval_seconds+=end-prepared;return value
class WeightedChess(WeightedMixin,ChessBoard):pass
class WeightedShogi(WeightedMixin,ShogiBoard):pass

class PiecePool(dict):
 def __missing__(self,key):
  piece=Piece(*key);self[key]=piece;return piece
def pooled_state(snapshot,compiled,pool):
 cells,hands,side,aux,ply=snapshot
 return SimpleNamespace(position=Position(tuple(None if x is None else pool[x] for x in cells),tuple(Hands(h) for h in hands),side,compiled.ruleset_fingerprint,aux),ply_count=ply)
class PooledMixin:
 def __init__(self,case,evaluator,*,measure=False):
  super().__init__(case,evaluator,measure=measure);self.piece_pool=PiecePool()
 def evaluate(self):
  if not self.measure:return self.evaluator.evaluate(pooled_state(self.snapshot(),self.evaluator._compiled,self.piece_pool))
  start=time.perf_counter();state=pooled_state(self.snapshot(),self.evaluator._compiled,self.piece_pool);prepared=time.perf_counter();value=self.evaluator.evaluate(state);end=time.perf_counter();self.eval_calls+=1;self.adapter_seconds+=prepared-start;self.eval_seconds+=end-prepared;return value
class PooledChess(PooledMixin,WeightedChess):pass
class PooledShogi(PooledMixin,WeightedShogi):pass
