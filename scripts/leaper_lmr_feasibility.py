"""Research-only one-ply late quiet reduction; no product/default activation.

The nominal depth of this selective tree is NOT a full-width value guarantee.
TTs belong to one arm and retain complete existing history/clock guards.
"""
import ast
import inspect
import textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S
from generic_chess.core.actions import action_is_board, action_target_square, action_promotion_target_id
from generic_chess.core.coordinates import square_to_index


def transform(source):
    original = textwrap.dedent(source)
    old = 'def child_search(window_alpha, window_beta, child_pv):'
    new = 'def child_search(window_alpha, window_beta, child_pv, reduction=0):'
    assert original.count(old) == 1
    changed = original.replace(old, new)
    # Both runtime and portable child routes use the SAME explicit reduced depth.
    assert changed.count('depth - 1, window_alpha, window_beta') == 2
    changed = changed.replace('depth - 1, window_alpha, window_beta',
                              'depth - 1 - reduction, window_alpha, window_beta')
    needle = '        if ctx.tuning.use_pvs and move_index > 0:'
    block = '''        if _research_lmr.parent_eligible(state, depth, ply, pv_node, move_index, action, ctx):
            reduced = child_search(-alpha - 1, -alpha, False, 1)
            reduced_score = -reduced.score
            if reduced_score > alpha:
                _research_lmr.counts['full_researches'] += 1
                child_result = child_search(-beta, -alpha, pv_node)
                score = -child_result.score
            else:
                _research_lmr.counts['accepted_reduced_fail_lows'] += 1
                child_result = reduced
                score = reduced_score
        elif ctx.tuning.use_pvs and move_index > 0:'''
    assert changed.count(needle) == 1
    changed = changed.replace(needle, block)
    # A checking/terminal child is never reduced. Query the pushed runtime view,
    # not the parent alias (RuntimeSearchState is mutable).
    needle2 = '                with ctx.runtime.pushed(action, checkpoint=ctx.checkpoint):\n'
    replacement = needle2 + '''                    if reduction:
                        reduction = _research_lmr.child_reduction(ctx.runtime.state, ctx)
'''
    assert changed.count(needle2) == 1
    changed = changed.replace(needle2, replacement)
    needle3 = '            return negamax(\n                child, depth - 1 - reduction'
    replacement3 = '''            if reduction:
                reduction = _research_lmr.child_reduction(child, ctx)
            return negamax(
                child, depth - 1 - reduction'''
    assert changed.count(needle3) == 1
    changed = changed.replace(needle3, replacement3)
    # Exact reverse guards against accidentally changing another source path.
    reverse = changed.replace(replacement3, needle3).replace(replacement, needle2)
    reverse = reverse.replace(block, needle).replace(new, old)
    reverse = reverse.replace('depth - 1 - reduction, window_alpha, window_beta',
                              'depth - 1, window_alpha, window_beta')
    assert ast.dump(ast.parse(reverse), include_attributes=False) == ast.dump(ast.parse(original), include_attributes=False)
    return ast.parse(changed)


class LateQuietReduction:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.counts = Counter()

    def parent_eligible(self, state, depth, ply, pv_node, move_index, action, ctx):
        if not self.enabled or ply == 0 or pv_node or depth < 3 or move_index < 3:
            return False
        if not action_is_board(action) or action_promotion_target_id(action) is not None:
            return False
        pos = state.position
        if pos.board[square_to_index(action_target_square(action), pos.board_shape)] is not None:
            return False
        self.counts['parent_check_queries'] += 1
        checked = (ctx.runtime.in_check(pos.side_to_move, checkpoint=ctx.checkpoint)
                   if ctx.runtime is not None else S.is_in_check(pos, pos.side_to_move, ctx.compiled))
        if checked:
            self.counts['parent_check_exclusions'] += 1
            return False
        self.counts['eligible_probes'] += 1
        return True

    def child_reduction(self, child, ctx):
        if child.terminal_status.is_terminal:
            self.counts['terminal_exclusions'] += 1
            return 0
        checked = (ctx.runtime.in_check(child.position.side_to_move, checkpoint=ctx.checkpoint)
                   if ctx.runtime is not None else S.is_in_check(child.position, child.position.side_to_move, ctx.compiled))
        if checked:
            self.counts['checking_exclusions'] += 1
            return 0
        self.counts['reduced_calls'] += 1
        return 1

    def __enter__(self):
        assert not hasattr(S, '_research_lmr')
        self.original = S.negamax
        tree = transform(inspect.getsource(self.original))
        S._research_lmr = self
        try:
            exec(compile(tree, '<research-leaper-lmr>', 'exec'), S.__dict__)
        except BaseException:
            del S._research_lmr
            raise
        return self

    def __exit__(self, *args):
        S.negamax = self.original
        del S._research_lmr
