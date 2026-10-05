"""Three new full-history capture controls, saved root states never replayed."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
from scripts.research_state_replay import read_game_state
from scripts.public_goal_intervals import PublicGame
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
OUT=ROOT/'docs/research/data/chess_promotion_erasure_20261005.json'
SOURCES=('scripts/audit_chess_promotion_erasure.py','scripts/research_state_replay.py',
 'scripts/research_record.py','docs/research/CHESS_PROMOTION_ERASURE_PROTOCOL.md',
 'docs/research/data/chess_knight_interposition_20261005.json',
 'docs/research/data/chess_knight_interposition_20261005.selections.json','scripts/public_goal_intervals.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen three-control producer never rerun')
    start=monotonic();r=dict(complete=False,rows=[],public_transitions=0,enumerated=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+1.656>=15:raise TimeoutError('same cumulative15sec cap')
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    save()
    try:
        pre=json.loads((ROOT/SOURCES[5]).read_text());observed=json.loads((ROOT/SOURCES[4]).read_text())
        if not observed['complete']:raise ValueError('complete prior phase required')
        for name,pin in observed['source_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=pin:raise ValueError('prior source drift')
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c)
        contact=pre['selections_before_labels']['contact']['selected'];table=observed['reply_tables'][contact]
        if len(table['mating_replies'])!=1:raise ValueError('unique prior mate witness required')
        witness=table['mating_replies'][0]
        expected=[row['state']['position'] for row in table['rows'] if row['action']==witness][0]
        for mode in ('B','N','R'):
            key=[key for key in pre['children'] if key.endswith('='+mode)][0]
            state=read_game_state(pre['children'][key]);game.terminal(state)
            if state.ply_count!=1 or len(state.history)!=2:raise ValueError('full imported child history lost')
            actions={str(a):a for a in game.actions(state,check)};r['enumerated']+=2*len(actions)
            if len(actions)>128 or r['enumerated']+2696>5000:raise ValueError('same action cap')
            row=dict(mode=mode,parent_key=key,all_actions=list(actions));r['rows'].append(row);save()
            if witness not in actions:raise ValueError('erasure capture not legal')
            if r['public_transitions']+77+5>=128:raise ValueError('same event cap')
            r['public_transitions']+=1;after=game.successor(state,actions[witness]);terminal=game.terminal(after)
            row.update(action=witness,state=record_value(after),terminal=record_value(terminal));save()
            if record_value(after.position)!=expected or terminal.status.value!='checkmate' or terminal.winner!=1:
                raise ValueError('captured-current equivalence fails')
        r['full_root_branch_intervals']={key:([-1,1] if key==pre['selections_before_labels']['unit']['selected'] else [-1,-1]) for key in pre['children']}
        r['weakly_optimal']=pre['selections_before_labels']['unit']['selected']
        r['decision_regret']={'contact':[0,2],'unit':[0,0],'zero':[0,0]};r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows','full_root_branch_intervals')}))
