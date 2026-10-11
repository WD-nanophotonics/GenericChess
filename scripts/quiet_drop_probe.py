"""Scoped research-only quiet-drop exclusion; no second history runtime."""
from collections import Counter
from generic_chess.core.actions import action_is_drop
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.ai.alphabeta.quiescence import enemy_board_count, material_inventory, noisy_child

class QuietDropProbe:
    def __init__(self, shadow=False):
        self.shadow=shadow; self.counts=Counter()
    def prepare(self, ctx):
        rt=ctx.runtime; c=ctx.compiled; support=getattr(c,'support',c)
        engine=semantic_engine_for(c)
        if engine is None:return None
        next_ply=rt.ply_count+1
        # Unknown or history-sensitive terminal boundaries retain the original push.
        if getattr(c,'repeated_cycle_target_conditions',()):self.counts['decline_target']+=1;return None
        if getattr(c,'consecutive_action_adjudications',()):self.counts['decline_consecutive']+=1;return None
        if getattr(c,'no_progress_draw',None) is not None:self.counts['decline_progress']+=1;return None
        if next_ply>=support.max_ply:self.counts['decline_maxply']+=1;return None
        if any(next_ply>=a.trigger_ply for a in getattr(c,'automatic_adjudications',())):self.counts['decline_automatic']+=1;return None
        if rt._opaque_imported_keys:self.counts['decline_opaque']+=1;return None
        # Any one child can increase one exact occurrence by at most one.
        # No identity/hash/history mutation is needed to prove this upper bound.
        if any(entry.count>=support.repetition_limit-1 for bucket in rt._occurrences.values() for entry in bucket):
            self.counts['decline_repetition']+=1;return None
        self.counts['eligible_qparents']+=1
        return engine
    def exclude(self, ctx, action, engine, parent_enemies, parent_inventory):
        if engine is None or not action_is_drop(action):return False
        self.counts['drop_trials']+=1;ctx.checkpoint()
        rt=ctx.runtime; parent=rt.position; side=parent.side_to_move
        semantic,binding=rt._bindings[action]
        child=engine._transition(parent,semantic,binding,checkpoint=ctx.checkpoint)
        self.counts['mechanical_transitions']+=1
        if enemy_board_count(child,side)<parent_enemies or material_inventory(child)!=parent_inventory:
            self.counts['retain_material']+=1;return False
        if not ctx.tuning.use_capture_only_qsearch and engine.in_check(child,1-side,checkpoint=ctx.checkpoint):
            self.counts['retain_check']+=1;return False
        provider=rt.availability_provider
        has_legal=None if provider is None else provider(child,checkpoint=ctx.checkpoint)
        if has_legal is None:has_legal=engine.has_legal_action(child,checkpoint=ctx.checkpoint)
        if type(has_legal) is not bool:raise TypeError('availability must be bool or None')
        if not has_legal:self.counts['retain_no_legal']+=1;return False
        # Full Core child mechanics preserved; guards prove all remaining
        # terminal rules inactive. This is exclusion only, never a child identity.
        self.counts['proved_exclusions']+=1
        if self.shadow:
            with rt.pushed(action,checkpoint=ctx.checkpoint):
                assert rt.position==child and not rt.terminal_status.is_terminal
                assert not noisy_child(action,rt.state,side,parent_enemies,parent_inventory,
                    lambda:rt.in_check(1-side,checkpoint=ctx.checkpoint),capture_only=ctx.tuning.use_capture_only_qsearch)
            self.counts['shadow_verified']+=1
            return False
        if not ctx.tuning.use_capture_only_qsearch:
            ctx.stats.nonchecking_drop_excluded+=1
        return True
