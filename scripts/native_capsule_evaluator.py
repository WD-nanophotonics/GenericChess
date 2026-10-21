"""Explicit runtime-bound semantic attack experiment; never legacy authority.

The caller binds its own CapsulePathRuntime. A stale/foreign Position view is
rejected. Existing evaluator weights/promotion/anchor equations are retained.
"""
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from generic_chess.native.semantic import attacked_squares


class RuntimeSemanticAttackEvaluator(SemanticAttackEvaluator):
    def __init__(self, compiled, profile, config):
        super().__init__(compiled, profile, config, backend='native')
        self._runtime = None
        self.attack_queries = 0

    def bind_runtime(self, runtime):
        if runtime.compiled is not self._compiled:
            raise ValueError('runtime evaluator compiled source mismatch')
        self._runtime = runtime

    def _attack_maps(self, state):
        rt = self._runtime
        if rt is None or state.position is not rt.position or state.ply_count != rt.ply_count:
            raise ValueError('runtime evaluator requires current bound view')
        maps = tuple(attacked_squares(rt.native, rt.capsule, owner) for owner in (0, 1))
        self.attack_queries += 2
        return tuple(frozenset(self._attack_squares[i] for i in indices) for indices in maps)
