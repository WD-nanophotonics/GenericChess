from dataclasses import replace
import json
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.core.pieces import Piece
from generic_chess.core.coordinates import Square
r=build_standard_shogi_ruleset(); n=r.board_size
def rot(s): return Square(n-1-s.file,n-1-s.rank)
def rot_mask(mask):
    out=[False]*(n*n)
    for idx,value in enumerate(mask):
        rank,file=divmod(idx,n); out[(n-1-rank)*n+(n-1-file)]=value
    return tuple(out)
drop={tid:(rot_mask(owners[1]),rot_mask(owners[0])) for tid,owners in r.drop_allowed.items()}
promote={tid:(frozenset((rot(a),rot(b)) for a,b in owners[1]),frozenset((rot(a),rot(b)) for a,b in owners[0])) for tid,owners in r.promotion_allowed.items()}
forced={tid:(frozenset(rot(s) for s in owners[1]),frozenset(rot(s) for s in owners[0])) for tid,owners in r.promotion_forced.items()}
board=[[None]*n for _ in range(n)]
for rank,row in enumerate(r.initial_position):
    for file,p in enumerate(row):
        if p is not None: board[n-1-rank][n-1-file]=Piece(1-p.owner,p.base_type_id,p.current_type_id,p.promoted)
rr=replace(r,initial_position=tuple(tuple(row) for row in board),drop_allowed=drop,promotion_allowed=promote,promotion_forced=forced)
a=build_ruleset_profile(compile_ruleset_for_execution(r),EvaluationConfig())
b=build_ruleset_profile(compile_ruleset_for_execution(rr),EvaluationConfig())
fields=('raw_capability_score','movement_signature','normalized_board_value','normalized_hand_value','promotion_option_value','drop_freedom_ratio','drop_mobility','is_anchor','is_promotable')
rows={}
for tid,p in a.piece_profiles.items():
    q=b.piece_profiles[tid]
    rows[tid]={name:{'original':getattr(p,name),'rotated':getattr(q,name),'equal':getattr(p,name)==getattr(q,name)} for name in fields}
print(json.dumps({'board_size':n,'drop_mask_counts':{tid:[sum(mask) for mask in owners] for tid,owners in r.drop_allowed.items() if any(any(mask) for mask in owners)},'promotion_pair_counts':{tid:[len(mask) for mask in owners] for tid,owners in r.promotion_allowed.items()},'forced_promotion_counts':{tid:[len(mask) for mask in owners] for tid,owners in r.promotion_forced.items()},'profile_median_original':a.median_non_anchor_value,'profile_median_rotated':b.median_non_anchor_value,'profile_median_equal':a.median_non_anchor_value==b.median_non_anchor_value,'per_type':rows,'all_fields_equal':all(item['equal'] for row in rows.values() for item in row.values())},sort_keys=True))
