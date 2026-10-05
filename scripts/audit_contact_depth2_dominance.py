"""Global shared-vector proof and only NEW enemy edges from saved child states."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
from scripts.research_state_replay import read_game_state
from scripts.saved_action_binding import saved_board_action
from scripts.native_chess_contact_intervals import native_contact_intervals,_ongoing_features
from scripts.material_leaf_choice import inventory_features
from scripts.public_goal_intervals import PublicGame
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
OUT=ROOT/'docs/research/data/contact_depth2_dominance_20261005.json'
SOURCES=('scripts/audit_contact_depth2_dominance.py','scripts/saved_action_binding.py',
 'docs/research/CONTACT_DEPTH2_DOMINANCE_PROTOCOL.md','docs/research/data/chess_knight_interposition_20261005.json',
 'docs/research/data/chess_promotion_erasure_20261005.json','docs/research/data/chess_pinned_queen_mate_20261005.json',
 'docs/research/data/chess_pinned_queen_continuation_20261005.json','scripts/native_chess_contact_intervals.py',
 'scripts/research_state_replay.py','scripts/research_record.py','scripts/public_goal_intervals.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen depth2 continuation never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,enumerated=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+0.219>=15:raise TimeoutError('same15sec pinned-Queen cap')
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    save()
    try:
        negative=json.loads((ROOT/SOURCES[3]).read_text());positive=json.loads((ROOT/SOURCES[5]).read_text());continued=json.loads((ROOT/SOURCES[6]).read_text())
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c);e=semantic_engine_for(c)
        def apply(state,key,count):
            check();r['enumerated']+=count
            if r['enumerated']+622>5000 or r['public_transitions']+34>=128:raise ValueError('same event/membership cap')
            r['public_transitions']+=1;return game.successor(state,saved_board_action(e,state,key))
        picks=positive['selections_before_labels'];zero=picks['zero']['selected'];unit=picks['unit']['selected']
        children={k:read_game_state(v) for k,v in positive['children'].items()}
        rkey=[k for k in children if 'r_capture' in k and k.endswith('h8-g8')][0]
        rchild=children[rkey];actions={str(a):a for a in game.actions(rchild,check)};r['enumerated']+=len(actions)
        if len(actions)!=1:raise ValueError('R capture singleton reply hypothesis fails')
        r['rook_capture']=dict(parent=rkey,all_enemy_replies=list(actions));save()
        after=apply(rchild,next(iter(actions)),len(actions));r['rook_capture']['state']=record_value(after);save()
        if game.terminal(after).is_terminal or inventory_features(after.position,{'K'})!=inventory_features(rchild.position,{'K'}):raise ValueError('R singleton changed score')
        branch=continued['baseline_counterbranches'][zero];zchild=children[zero];r['zero_all_replies']=branch['all_enemy_replies'];r['zero_rows']=[];save()
        for key in branch['all_enemy_replies']:
            if key==branch['enemy_action']:
                after=read_game_state(branch['enemy_child']);reused=True
            else:
                after=apply(zchild,key,len(branch['all_enemy_replies']));reused=False
            t=game.terminal(after);r['zero_rows'].append(dict(action=key,state=record_value(after),reused=reused));save()
            if t.status.value=='checkmate' and t.winner==1:raise ValueError('zero earliest branch loses at depth2')
        unit_scores={k:F(v) for k,v in picks['unit']['scores'].items()};best=unit_scores[rkey]
        if any(k<rkey and v>=best and k!=unit for k,v in unit_scores.items()):raise ValueError('unproved earlier unit tie')
        counter=read_game_state(continued['baseline_counterbranches'][unit]['enemy_child'])
        ucounter=sum(inventory_features(counter.position,{'K'}).values())/F(31)
        if not ucounter<best:raise ValueError('King capture tie not eliminated')
        for law in ('geometric_half','linear_mixture'):
            margins=picks['contact']['models'][law]['margins']
            if not all(F(pair[0])>0 for pair in margins.values()):raise ValueError('contact strict child margins missing')
        negunit=negative['selections_before_labels']['unit']['selected'];leafs=negative['reply_tables'][negunit]['rows']
        r['negative_leaf_features']=[]
        for row in leafs:
            state=read_game_state(row['state']);t=game.terminal(state)
            if t.is_terminal and t.winner==1:raise ValueError('negative baseline depth2 terminal loss')
            if not t.is_terminal:r['negative_leaf_features'].append(record_value(_ongoing_features(state.position)))
        r['negative_depth2']={name:negunit for name in ('contact','unit','zero')}
        r['positive_depth2']=dict(contact=picks['contact']['selected'],unit=rkey,zero=zero)
        r['operator_scope']='fixed two-ply terminal-first STATIC minimax; global coefficient dominance, not WDL score calibration or new validation'
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rook_capture','zero_rows','zero_all_replies','negative_leaf_features')}))
