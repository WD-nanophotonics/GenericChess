"""Research-only finite union of the two declared duration boxes."""
from scripts.native_chess_contact_intervals import contact_interval_choice

MODELS = ('geometric_half', 'linear_mixture')


def duration_union_choice(children, game, *, owner, complete=False):
    """Keep disjoint model boxes, without sampling or changing either law.

    Incompleteness dominates; a stable choice in only one model is insufficient.
    The existing interface enforces the same complete child/semantic contract.
    """
    results = {model: contact_interval_choice(children, game, owner=owner,
                duration=model, complete=complete) for model in MODELS}
    if any(not r['complete'] for r in results.values()):
        return dict(complete=False, selected=None, classification='incomplete', models=results)
    choices = [r['selected'] for r in results.values()]
    if any(c is None for c in choices):
        return dict(complete=True, selected=None, classification='within_model_uncertainty', models=results)
    if len(set(choices)) != 1:
        return dict(complete=True, selected=None, classification='duration_disagreement', models=results)
    return dict(complete=True, selected=choices[0], classification='union_stable', models=results)
