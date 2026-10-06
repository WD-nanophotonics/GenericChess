import hashlib,json
from pathlib import Path
from collections import Counter
from scripts.research_state_replay import read_game_state
ROOT=Path(__file__).resolve().parents[1]


def load(name):return json.loads((ROOT/f'docs/research/data/{name}_20261006.json').read_text())


def test_distinct_controller_admission_and_original_failure_preserved():
    p=load('multitype_qtree_preflight');r=load('multitype_qtree_v2');f=load('multitype_qtree_import_failure')
    assert p['complete'] and r['complete'] and not f['complete']
    for item in (p,r,f):
        for path,pin in item['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
    assert p['author_pushes']==p['author_entries']==69
    assert p['noisy_edges']==3 and p['evasion_edges']==17 and p['repeated_cached_runtime_D_upper']==129
    assert r['public_transitions']==69 and r['entries']==138 and r['score_terms']==375
    assert f['public_transitions']==r['new_author_pushes']==r['runtime_pushes']==0


def test_full_saved_history_counts_and_local_edge_prefixes():
    r=load('multitype_qtree_v2');states={k:read_game_state(row['state']) for k,row in r['nodes'].items()}
    assert len(states)==70 and all(not s.terminal_status.is_terminal for s in states.values())
    for path,s in states.items():
        assert dict(s.repetition_counts)==dict(Counter(h.position_key for h in s.history))
        assert len(s.history)==s.ply_count+1
    for path,row in r['edges'].items():
        p=states[path]
        for e in row.values():
            c=states[e['child']]
            assert c.history[:-1]==p.history and c.history[-1].actor==p.position.side_to_move
            assert c.history[-1].gave_check==e['checking']


def test_actual_check_evasions_and_all_price_ties_retained():
    r=load('multitype_qtree_v2')
    for law,p in r['policies'].items():
        assert p['scores']==p['static_scores'] and p['full_ties']==p['static_full_ties']
        checks=[(k,x) for k,x in p['trace'].items() if x['in_check']]
        assert len(checks)==3
        for k,t in checks:
            assert 'stand_pat_approximation' not in t['branch_scores']
            assert set(t['branch_scores'])==set(r['edges'][k])
        assert p['canonical']=='b1a2'
    assert r['policies']['unit']['full_ties']==['b1a2','b1c2']
    assert r['policies']['geometric_half']['full_ties']==['b1a2']
