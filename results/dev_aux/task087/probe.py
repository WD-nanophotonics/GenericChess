import json,hashlib,sys
from pathlib import Path
R=Path.cwd();B=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'.local_agent/pinned_bebe'))
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.core.position import Position,Hands
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import semantic as ns
source=(R/'results/dev_aux/task057/result.json').read_bytes();old=json.loads(source);rows=[]
def tuples(x):return tuple(tuples(v) for v in x) if isinstance(x,list) else x
for r in old['rows']:
 c=compile_semantic_ruleset(ruleset_from_dict(r['ruleset']));assert c.ruleset_fingerprint==r['ruleset_fingerprint'];v=r['position'];pos=Position(tuple(None if p is None else Piece(**p) for p in v['board']),tuple(Hands(tuples(h['counts'])) for h in v['hands']),v['side_to_move'],v['ruleset_fingerprint'],tuples(v['aux_state']),v.get('board_width'),v.get('board_height'));engine=semantic_engine_for(c);native=compile_native_semantic_rules(c);packed=ns.pack_current_position(native,pos,ply_count=0);before=ns.snapshot(native,packed)
 for owner in (0,1):
  core=engine.attacked_squares(pos,owner);nat=ns.attacked_squares(native,packed,owner);queries=[]
  for target in range(len(pos.board)):
   a=engine.is_square_attacked(pos,target,owner);z=ns.is_square_attacked(native,packed,target,owner);assert a==(target in core) and z==(target in nat);queries.append({'target':target,'Core':a,'Native':z})
  rows.append({'case':r['case'],'owner':owner,'Core_maps':sorted(core),'Native_maps':sorted(nat),'map_equal':core==nat,'scalar_mismatches':[q for q in queries if q['Core']!=q['Native']],'scalar_checks':len(queries),'provider_supported':NativeSemanticLegalityProvider.try_create(c,strict=True) is not None,'root_unchanged':ns.snapshot(native,packed)==before})
out={'complete':True,'source_old_fixture_sha256':hashlib.sha256(source).hexdigest(),'rows':rows,'scalar_checks':sum(r['scalar_checks'] for r in rows),'map_mismatches':sum(not r['map_equal'] for r in rows),'scope':'Distinctsemanticpseudoattackcontract ignores transition removefilter eligibility bydefinition;no oldfrontier rerun,Nativeprovider refusal unchanged'}
(B/'result.json').write_bytes((json.dumps(out,indent=2)+'\n').encode());print(json.dumps(out))
