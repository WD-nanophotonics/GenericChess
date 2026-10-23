"""Represent existing frozen sampling supports; no new openings or forecasts."""
from copy import deepcopy
from collections import defaultdict
from scripts.leaper_explorer_truth import digest


def initial_history_view(truth):
    """A proposed evaluation view, not a PRIMARY-selected prediction target.

    Exactly the original default initial history of each already frozen rule.
    No new layout is generated and no oracle chooses a new research start.
    mu IDs change because a point history is not uniform over all decisions.
    """
    roots=deepcopy([r for r in truth['roots']if r['ply']==0])
    by_rule=defaultdict(list)
    for r in roots:by_rule[r['fingerprint']].append(r)
    if set(by_rule)!=set(truth['rules'])or any(len(rs)!=1 for rs in by_rule.values()):
        raise ValueError('exactly one original initial history per frozen rule required')
    mus={fp:digest(sorted(r['id']for r in rs))for fp,rs in by_rule.items()}
    for r in roots:
        r['parent_mu_id']=r['mu_id'];r['mu_id']=mus[r['fingerprint']]
    return dict(format='leaper-explorer-truth-view-v1',roots=roots,
                rules=deepcopy(truth['rules']),mu_ids=mus,parent_truth_digest=digest(truth),
                law='one_original_frozen_initial_history_per_rule',
                status='PROPOSED_MATCHED_TRUTH_VIEW_NOT_A_PREDICTION_FREEZE',
                scope='Only the ten original already-exposed histories; no new layout, opening distribution, rule, game, TRAIN root or holdout. This changes the evaluation support/mu identifiers, not full-history identity or truth. PRIMARY still chooses/fixes the actual E0 target and information set. A rule-level prevalence at this singleton mu equals that initial history binary property; it is not existence over every legal history/layout.')
