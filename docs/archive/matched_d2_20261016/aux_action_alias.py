from pathlib import Path
import sys,json,dataclasses,hashlib
R=Path.cwd();P=R/".local_agent/matched-d2-20261016";sys.path[:0]=[str(R),str(R/"tests/product"),str(R/"tests")]
from test_native_main_order_pv_witness import phase_graph
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import serialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.transition import apply_action
from generic_chess.learning.policy_v1 import action_v1_components
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import pack_semantic_action
from generic_chess.native import semantic as sem
from scripts.research_record import record_value,write_record
rs=phase_graph();geom=next(x.geometry for x in rs.semantic_actions if x.name=="aV");actions=tuple(dataclasses.replace(x,geometry=geom)if x.name=="aU"else x for x in rs.semantic_actions);rs=dataclasses.replace(rs,semantic_actions=actions)
c=compile_ruleset_for_execution(rs);s=GameSession(c);s.submit(s.legal_actions()[0]);nr=compile_native_semantic_rules(c);rows=[];error=None
for ac in s.legal_actions():
 base,cats=action_v1_components(c,s.state.position,ac);child=apply_action(s.state,ac,c);np=sem.make_checked(nr,pack_semantic_search_position(c,nr,s),pack_semantic_action(nr,s.state.position,ac));snap=sem.snapshot(nr,np)
 rows.append(dict(action=record_value(ac),base=base.tolist(),categories=list(cats),child=record_value(child),native_aux=record_value(snap["aux_state"])))
out=dict(complete=True,ruleset=json.loads(serialize_ruleset(rs)),game_record=json.loads(serialize_game_record(s.to_record())),state=record_value(s.state),rows=rows,queries=0,games=0,training=0,scope="Explicitonefieldgeometrycounterfactual onexistingprogrammablephasegraph regression; not generatedfrequency, trainedpolicydefect, generalaliasrate orpermissiontonewarchitecture. Sameactor/destination/geometry butdistinctauxeffects; actualNative/Corechildbindingretained.")
assert len(rows)==2;out.update(v1_input_equal=rows[0]["base"]==rows[1]["base"]and rows[0]["categories"]==rows[1]["categories"],full_children_different=rows[0]["child"]!=rows[1]["child"])
write_record(P/"aux-action-alias.json",out);print("AUX_ALIAS",out["v1_input_equal"],out["full_children_different"],[(x["action"]["pattern_id"],x["categories"],x["child"]["position"]["aux_state"])for x in rows],flush=True)
