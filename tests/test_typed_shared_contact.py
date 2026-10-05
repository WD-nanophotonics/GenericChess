import hashlib,json
from pathlib import Path
from scripts.typed_shared_contact_prefix import actor_bound_view
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
ROOT=Path(__file__).resolve().parents[1]
def test_actor_binding_precedes_mask_equivalence_no_new_observations():
    r=json.loads((ROOT/'docs/research/data/typed_shared_contact_20261005.json').read_text())
    assert r['complete'] and len(r['rows'])==8 and r['old_mismatches']==4
    assert all(row['typed']==row['actual'] for row in r['rows'])
    assert r['public_transitions']==r['enumerated']==r['source_queries']==0
    assert r['candidates']<=5000 and r['seconds']<15
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_existing_game_patterns_have_no_cross_actor_geometry_leak():
    # Metadata only: do not rerun any distance population or materialize events.
    for build in (build_western_chess_ruleset,build_standard_shogi_ruleset):
        c=compile_semantic_ruleset(build());view=actor_bound_view(c)
        def incidence(ir):
            return {(p.pattern_id,t,g) for p in ir.patterns for t in p.type_ids for g in p.geometry_ids}
        assert incidence(view.ir)==incidence(c.ir)
