from collections import Counter
from pathlib import Path
from scripts.leaper_saved_child_bounds import current_truth,propagate
from scripts.leaper_explorer_truth import load,save
t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
q=load('artifacts/saved-child-bounds-d19a/edges.json.gz');u,_=propagate(t,q);roots={r['id']:r for r in u['roots']}
clauses=[];stats=Counter()
for r in q['rows']:
    parent=roots[r['id']]
    if parent['cooperative_decisive']is not True:continue
    candidates=[];known_true=False;external=False
    for e in r['children']:
        if e['terminal']not in ('ongoing','no_contest'):
            known_true|=e['terminal_winner']is not None
        elif e['terminal']=='no_contest':external=True
        elif e['child_id']in roots:
            c=roots[e['child_id']]['cooperative_decisive']
            if c is True:known_true=True
            elif c is None:candidates.append(e['child_id'])
        else:external=True
    if known_true:stats['already_satisfied']+=1
    elif external:stats['external_escape_no_saved_label_constraint']+=1
    else:
        assert candidates
        clauses.append(dict(parent=r['id'],candidates=sorted(set(candidates))));stats['unsatisfied_saved_only_clauses']+=1
save('artifacts/saved-child-bounds-d19a/residual-clauses.json',dict(counts=dict(stats),clauses=clauses))
print(stats);print('clause_sizes',Counter(len(r['candidates'])for r in clauses))
