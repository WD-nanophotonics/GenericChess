"""Qualify the saved probe without rerunning or changing failed evidence."""
import sys,json
from pathlib import Path
root=Path.cwd();sys.path[:0]=[str(root/'tests'),str(root/'tests/product'),str(root)]
from test_qsearch_semantic_effects import transform_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.core.transition import legal_successors
from scripts.research_record import record_value,write_record
p=Path(__file__).parent;out=p/'encoding-order-analysis.json';assert not out.exists()
raw=json.loads((p/'encoding-order-probe.json').read_bytes());children=[]
for encoding in ('effect','explicit'):
 c=compile_ruleset_for_execution(transform_rules(encoding=encoding));s=GameSession(c)
 child=next(n.position for a,n in legal_successors(s.state,c) if getattr(a,'pattern_id','').startswith('sem_'))
 children.append(record_value(child))
different={k:(children[0][k],children[1][k]) for k in children[0] if children[0][k]!=children[1][k]}
assert set(different)=={'ruleset_fingerprint'},different
rows=[]
for row in raw['cases']:
 assert len(row['searches'])==4
 assert all(z['decision']['completed_depth']==3 and z['decision']['score']==row['reference_score'] for z in row['searches'])
 nodes={str(staged):[z['decision']['nodes'] for z in row['searches'] if z['staged']==staged] for staged in (False,True)}
 assert all(v[0]==v[1] for v in nodes.values())
 rows.append(dict(encoding=row['encoding'],reference_score=row['reference_score'],nodes=nodes,root_order=row['ordering']))
result=dict(complete=True,original_probe_complete=raw['complete'],correction='Original cross-rule Position equality includes different ruleset fingerprints. Failed assertion is retained. Reconstructed successors differ only in fingerprint; no TT identity merge across rules is permitted. All eight saved searches/fullwidth controls completed before that assertion.',different_position_fields=list(different),rows=rows,decision='Ordering costs may depend on metadata; compare saved sorted/staged traces before considering any actual-effect scoring change. No speed/strength/default conclusion, no new budget or search rerun.')
write_record(out,result);print([(z['encoding'],z['reference_score'],z['nodes']) for z in rows])
