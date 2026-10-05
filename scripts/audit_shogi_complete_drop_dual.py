"""One complete semantic parent table with proved inventory deltas; no events."""
from dataclasses import asdict,replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts.resource_mode_context import resource_ledger
from scripts.material_leaf_choice import inventory_features
from scripts.shogi_contact_interval_choice import shogi_contact_intervals
from scripts.shogi_board_hand_gap import board_hand_gap
from scripts.material_interval_choice import certified_ongoing_material_choice
from scripts.coupled_material_choice import coupled_material_choice
OUT=ROOT/'docs/research/data/shogi_complete_drop_dual_20261005.json'
SOURCES=('scripts/audit_shogi_complete_drop_dual.py','scripts/coupled_material_choice.py',
 'docs/research/SHOGI_COMPLETE_DROP_DUAL_PROTOCOL.md','scripts/shogi_board_hand_gap.py',
 'scripts/shogi_contact_interval_choice.py','scripts/coupled_linear_bounds.py',
 'generic_chess/rules/standard_shogi.py','generic_chess/core/semantic_executor.py')

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen full table never rerun')
    start=monotonic();out=dict(complete=False,enumerated=0,virtual_materializations=0,goal_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec table cap')
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());e=semantic_engine_for(c)
        board=[None]*81
        for sq,owner,t in ((0,0,'K'),(27,0,'P'),(72,1,'K')):board[sq]=Piece(owner,t,t)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0,
          hands=(Hands((('P',1),)),Hands((('B',2),('G',4),('L',4),('N',4),('P',16),('R',2),('S',4)))))
        out['root']=asdict(p);out['ledger']=resource_ledger(c,p,'shogi')
        if any(e.in_check(p,owner) for owner in (0,1)):raise ValueError('checked root')
        actions=e.legal_actions(p,checkpoint=check);out['enumerated']=len(actions)
        if len(actions)>128:raise ValueError('action cap')
        base=inventory_features(p,{'K'});features={};drops=[];quiet=[]
        out['rows']=[]
        for action in actions:
            check();key=str(action);pattern=c.ir.patterns[action.pattern_id]
            kinds=tuple(x.kind for x in pattern.effects)
            if action.promotion_target_id is not None:raise ValueError('unexpected promotion')
            feature=dict(base)
            if action.source is None:
                if action.actor_type!='P' or kinds!=('drop',):raise ValueError('unexpected drop effect')
                feature['board','P']=feature.get(('board','P'),0)+1;feature['hand','P']-=1;drops.append(key)
            else:
                if action.actor_type not in ('K','P') or kinds!=('move',):raise ValueError('unexpected move effect')
                quiet.append(key)
            if key in features:raise ValueError('lossy action IDs')
            features[key]=feature;out['rows'].append(dict(key=key,action=asdict(action),effect_kinds=kinds))
        out['drop_count']=len(drops);out['quiet_count']=len(quiet);out['by_law']={}
        if not drops or not quiet:raise ValueError('missing action class')
        for law in ('geometric_half','linear_mixture'):
            check();boxes=shogi_contact_intervals(law);gap=board_hand_gap(law,normalized=True)['P']['lower']
            constraints={'P_board_hand':({('board','P'):F(1),('hand','P'):F(-1)},gap)}
            witnesses={(a,b):{'P_board_hand':F(1)} for a in drops for b in quiet}
            coupled=coupled_material_choice(features,boxes,constraints,witnesses,owner=0,complete=True)
            out['by_law'][law]=dict(box_only=certified_ongoing_material_choice(features,boxes,owner=0,complete=True),
                                   coupled=coupled,gap=gap)
        out['complete']=all(r['coupled']['selected']==min(drops) and r['box_only']['selected'] is None for r in out['by_law'].values())
    except Exception as error:out['error']=f'{type(error).__name__}: {error}'
    out['seconds']=monotonic()-start
    out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,default=str,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('root','rows','by_law','source_sha256','ledger')}))
