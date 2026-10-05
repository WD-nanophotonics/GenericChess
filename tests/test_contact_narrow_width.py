import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(name):return json.loads((ROOT/'docs/research/data'/name).read_text())
def test_preserved_full_width_precedes_selection_and_no_budget_shrink():
    pre=read('contact_narrow_preflight_20261005.json');r=read('contact_narrow_width_20261005.json')
    assert pre['complete'] and len(pre['rows'])==13 and len(pre['accepted'])==2
    assert pre['public_transitions']==pre['source_queries']==0 and pre['enumerated']==13
    assert r['complete'] and len(r['rows'])==2 and r['public_transitions']==8
    assert r['required_full_depth2_events']==130 and not r['depth2_fits']
    count=0
    for root,accepted in zip(r['rows'],pre['accepted']):
        assert root['root']==accepted['root'] and root['all_root_actions']==accepted['actions']
        assert set(root['branches'])==set(root['all_root_actions']) and len(root['branches'])==4
        assert 'selections_before_ply3' not in root
        for branch in root['branches'].values():
            count+=len(branch['all_enemy_actions']);assert branch['leaves']=={}
    assert count==122 and r['source_queries']==0 and r['enumerated']==162

def test_new_contract_and_all_saved_inputs_remain_frozen():
    for name in ('contact_narrow_preflight_20261005.json','contact_narrow_width_20261005.json'):
        r=read(name)
        assert r['source_hashes_unchanged'] and r['seconds']<15
        for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
