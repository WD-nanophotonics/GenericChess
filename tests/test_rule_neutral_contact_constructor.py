from dataclasses import replace
from fractions import Fraction as F
import hashlib,json
from pathlib import Path
import pytest
from scripts.audit_rule_neutral_contact_constructor import build,kernel_distance
from scripts.rule_neutral_contact_constructor import construct_contact,ContactUnsupported
from scripts.shared_contact_prefix import Profile
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
ROOT=Path(__file__).resolve().parents[1]
def test_new_micro_worldwise_qualification_and_name_invariance():
    r=json.loads((ROOT/'docs/research/data/rule_neutral_contact_constructor_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==6 and r['canonical_candidates']==114
    for row in r['rows']:
        assert row['worlds']==504 and row['first_mismatch'] is None
        assert row['ordered_kernel_sha256']==row['ordered_oracle_sha256']
        assert sum(row['census']['histogram'].values())+row['census']['unreachable']==504
        assert row['algorithm']==('target_free' if row['family']=='S' else 'target_aware')
    assert r['renamed']['census']==r['rows'][2]['census']
    assert r['public_transitions']==r['source_queries']==r['enumerated']==0 and r['seconds']<15
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_minimum_range_prefix_failure_changes_the_distance():
    r=construct_contact(compile_semantic_ruleset(build('M')),(Profile('opaque_actor','opaque_actor'),))
    assert r.algorithm=='target_aware'
    p=Profile('opaque_actor','opaque_actor')
    assert kernel_distance(r.kernel,p,2,1,4,target_free=True)==2
    assert kernel_distance(r.kernel,p,2,1,4)==0

def test_none_contract_must_not_inject_global_promotion():
    c=compile_semantic_ruleset(build_standard_shogi_ruleset())
    patterns=tuple(replace(p,promotion_mode='none') if p.type_ids==('P',) and p.target.kind=='target_empty' else p for p in c.ir.patterns)
    changed=replace(c,ir=replace(c.ir,patterns=patterns))
    with pytest.raises(ContactUnsupported,match='unpromoted promotable origin'):
        construct_contact(changed,(Profile('P','P'),))
