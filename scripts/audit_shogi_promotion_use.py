"""New complete partial-stock public tree, global affine custody uncertainty."""
from dataclasses import replace
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import initial_state
from scripts.audit_exchange_custody import synthetic_state
from scripts.public_goal_intervals import PublicGame
from scripts.shogi_exact_contact_family import exact_board_means
from scripts.material_leaf_choice import inventory_features
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/shogi_promotion_use_20261005.json';PRE=OUT.with_suffix('.selections.json')
SOURCES=('scripts/audit_shogi_promotion_use.py','docs/research/SHOGI_PROMOTION_USE_PROTOCOL.md','scripts/shogi_exact_contact_family.py','docs/research/data/shogi_full_contact_distance_20261005.json','docs/research/data/shogi_coordinate_comparison_20261005.json','scripts/material_leaf_choice.py','scripts/public_goal_intervals.py','scripts/audit_exchange_custody.py','generic_chess/rules/standard_shogi.py')
def affine(features,weights):
    value=F(0);hand={}
    for (location,kind),number in features.items():
        if location=='board':value+=number*weights[kind]
        elif kind in ('P','R'):hand[kind]=number
        else:raise ValueError('unqualified encountered hand mode')
    return value,hand
def margin(first,second):
    lo=hi=first[0]-second[0]
    for kind in first[1].keys()|second[1].keys():
        d=first[1].get(kind,0)-second[1].get(kind,0);lo+=min(0,d);hi+=max(0,d)
    return lo,hi
def minimizer(leaves,weights):
    scores={key:affine(features,weights) for key,features in leaves.items()}
    for key,value in sorted(scores.items()):
        if all(margin(value,other)[1]<=0 for other in scores.values()):return key,value
    raise ValueError('shared-box branch minimum not certified')
def selections(branches,weights):
    minima={key:minimizer(leaves,weights) for key,leaves in branches.items()}
    winners=[key for key,(_,value) in minima.items() if all(margin(value,other)[0]>=0 for _,other in minima.values())]
    if not winners:raise ValueError('no global-box maximizing branch')
    first=min(winners);best=minima[first][1]
    ties=sorted(key for key,(_,value) in minima.items() if margin(best,value)==(0,0))
    if any(margin(best,value)[0]<=0 for key,(_,value) in minima.items() if key not in ties):raise ValueError('tie set can change with shared parameters')
    return dict(selected=first,tie_set=ties,branch_minima={k:dict(witness=x,constant=v[0],hand_parameters=v[1]) for k,(x,v) in minima.items()},margins={k:margin(best,v) for k,(_,v) in minima.items()})
if __name__=='__main__':
    if OUT.exists() or PRE.exists():raise FileExistsError('fixed promotion use root never rerun')
    start=monotonic();r=dict(complete=False,branches={},public_transitions=0,enumerated=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec whole promotion-use study')
    def actions(state):
        check();table={str(a):a for a in game.actions(state,check)};r['enumerated']+=len(table)
        if len(table)>128 or r['enumerated']>5000:raise ValueError('unchanged enumeration cap')
        return table
    def apply(state,action,width):
        check();r['enumerated']+=width
        if r['public_transitions']>=128 or r['enumerated']>5000:raise ValueError('unchanged transition/membership cap')
        r['public_transitions']+=1;return game.successor(state,action)
    def save():write_record(OUT,r)
    try:
        c=compile_ruleset_for_execution(build_standard_shogi_ruleset());game=PublicGame(c);engine=semantic_engine_for(c);board=[None]*81
        for square,owner,kind in ((45,0,'K'),(54,0,'P'),(65,1,'K'),(63,1,'R')):board[square]=Piece(owner,kind,kind)
        p=replace(initial_state(c).position,board=tuple(board),side_to_move=0);root=synthetic_state(c,p);r['root']=record_value(root)
        if game.terminal(root).is_terminal or engine.in_check(p,1):raise ValueError('fresh root admission fails')
        # Previous promotion population is virtual; this is a new full public root.
        oldpaths=tuple((ROOT/'docs/research/data').glob('shogi_*20261005.json'));old_boards=[]
        def collect(x):
            if isinstance(x,dict):
                if 'position' in x and isinstance(x['position'],dict) and 'board' in x['position']:old_boards.append(x['position']['board'])
                for y in x.values():collect(y)
            elif isinstance(x,list):
                for y in x:collect(y)
        for old in oldpaths:
            if old!=OUT:collect(json.loads(old.read_text()))
        if record_value(p.board) in old_boards:raise ValueError('old observed board equality')
        r['old_board_equality_checked']=True;r['old_board_files']=[str(x.relative_to(ROOT)).replace('\\','/') for x in oldpaths]
        for path in r['old_board_files']:r['source_sha256'][path]=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
        table=actions(root);r['all_root_actions']=list(table);states={};features={};save()
        for key,action in table.items():
            child=apply(root,action,len(table));terminal=game.terminal(child)
            if terminal.is_terminal:raise ValueError('this affine nonterminal contract rejects whole terminal tree')
            replies=actions(child);branch=dict(state=record_value(child),all_enemy_actions=list(replies),leaves={});r['branches'][key]=branch;states[key]={};features[key]={};save()
            for reply,enemy_action in replies.items():
                leaf=apply(child,enemy_action,len(replies))
                if game.terminal(leaf).is_terminal:raise ValueError('terminal leaf requires separate qualified envelope')
                states[key][reply]=leaf;features[key][reply]=inventory_features(leaf.position,{'K'});branch['leaves'][reply]=dict(state=record_value(leaf),features=features[key][reply]);save()
            if not replies:raise ValueError('ongoing child cannot lack legal replies')
        r['selections_before_goal']={}
        for law in ('geometric_half','linear_mixture'):
            raw=exact_board_means(law);scale=raw['TR'];w={t:v/scale for t,v in raw.items()};r['selections_before_goal'][law]=selections(features,w)
        r['selections_before_goal']['unit']=selections(features,{t:F(1) for t in exact_board_means('geometric_half')})
        # Zero ignores both board AND hand, unlike the two material models.
        zeros={key:{reply:{} for reply in leaves} for key,leaves in features.items()};r['selections_before_goal']['zero']=selections(zeros,{})
        r['global_hand_parameter_scope']='one common hP,hR in[0,1]; exact affine extrema, zero ignores all inventory'
        write_record(PRE,r);r['prelabel_sha256']=hashlib.sha256(PRE.read_bytes()).hexdigest();save()
        selected=sorted({key for result in r['selections_before_goal'].values() for key in result['tie_set']});r['goal_width_rows']=[];needed=r['public_transitions'];exhausted=True
        for key in selected:
            for reply,leaf in sorted(states[key].items()):
                own=actions(leaf);needed+=len(own);r['goal_width_rows'].append(dict(root_action=key,enemy_action=reply,own_actions=list(own)));save()
                if needed>128:exhausted=False;break
            if not exhausted:break
        r['full_ply3_public_events_lower_bound']=needed;r['goal_width_exhausted']=exhausted;r['goal_over_budget']=needed>128
        r['independent_goal_status']='unknown: frozen complete-window expansion exceeds unchanged event cap' if needed>128 else 'width admitted; no goal observations in this preflight'
        r['complete']=r['goal_over_budget'] and len(r['selections_before_goal'])==4
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save();print(json.dumps({k:v for k,v in r.items() if k not in ('branches','root','source_sha256','selections_before_goal','goal_width_rows','old_board_files')}))
