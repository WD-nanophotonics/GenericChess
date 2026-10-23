from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_h6_adjacent_pairs import physical_action,analyze
from scripts.leaper_explorer_truth import load


def test_semantic_action_ids_are_not_cross_rule_physical_identity():
    p=Path('docs/research/data/leaper_h6_initial_truth_20261023')
    t=load(p/'truth.json.gz');a=next(r['action_bounds'][0]['action']for r in t['roots']if r['action_bounds'])
    b=deepcopy(a);b['pattern_id']='different_source_pattern';b['geometry_id']='different_source_geometry'
    assert physical_action(a)==physical_action(b)
    b['actor_type_id']='B'if a['actor_type_id']=='A'else'A'
    assert physical_action(a)!=physical_action(b)


def test_onebit_common_support_and_capture_escape_are_actual():
    r=analyze(Path('docs/research/data/leaper_h6_initial_truth_20261023'))
    assert len(r['pairs'])==1
    p=r['pairs'][0]
    assert p['left_masks']==[6,27]and p['right_masks']==[22,27]
    assert p['common_roots']==128 and len(p['left_only'])==8 and not p['right_only']
    changes=[q for q in p['rows']if q['left_WDL']!=q['right_WDL']]
    assert len(changes)==16
    assert all(q['left_WDL']==-1 and q['right_WDL']==0 and q['common_action_WDL_changes']==0 for q in changes)
    assert all(e['captured']==1 and e['remaining_ordinary']==[(0,'A')]and e['closed_no_decisive_path']for q in changes for e in q['new_best_escapes'])
