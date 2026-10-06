"""Source-free replay of EVERY strategy path, with full actual local history."""
from time import monotonic
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.identity import position_identity_key
from generic_chess.core.transition import apply_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.research_state_replay import read_game_state
from scripts.audit_lichess_complete_children import uci
from scripts.research_record import write_record


def verify(certificate,*,seconds=30,max_transitions=20000):
    start=monotonic();compiled=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(compiled)
    if not certificate['complete']:raise ValueError('incomplete certificate')
    nodes=certificate['nodes'];root=certificate['root'];r=dict(complete=False,source_calls=0,transitions=0,
        visits=0,legal_entries=0,mate_leaves=0,max_absolute_ply=0)
    def check():
        if monotonic()-start>seconds:raise TimeoutError('verifier safety time')
        if r['transitions']>max_transitions:raise ValueError('verifier transition safety')
    def visit(key,state):
        check();r['visits']+=1;r['max_absolute_ply']=max(r['max_absolute_ply'],state.ply_count)
        if key not in nodes or key!=position_identity_key(state.position,compiled):raise ValueError('certificate edge identity')
        n=nodes[key]
        if state.position!=read_game_state(n['representative_state']).position or state.position.side_to_move!=n['actor']:raise ValueError('complete position/actor mismatch')
        terminal=game.terminal(state)
        if terminal.is_terminal:
            if n['rank']!=0 or n['strategy'] or n['all_actions'] or n['terminal']!='checkmate' or terminal.status.value!='checkmate' or terminal.winner!=0 or n.get('winner')!=0:raise ValueError('not an actual White mate leaf')
            r['mate_leaves']+=1;return
        if n['terminal']!='ongoing' or type(n['rank']) is not int or n['rank']<=0:raise ValueError('ongoing rank/terminal mismatch')
        actions={uci(a):a for a in game.actions(state,check)};r['legal_entries']+=len(actions)
        if sorted(actions)!=n['all_actions']:raise ValueError('incomplete legal action set')
        if n['actor']==1:
            if sorted(n['strategy'])!=sorted(actions):raise ValueError('missing defender action')
        elif len(n['strategy'])!=1 or not set(n['strategy'])<=set(actions):raise ValueError('missing legal attacker choice')
        for action,target in n['strategy'].items():
            if target not in nodes or nodes[target]['rank']>=n['rank']:raise ValueError('rank is not strictly decreasing')
            r['transitions']+=1;check();child=apply_action(state,actions[action],compiled)
            visit(target,child)
    visit(root,read_game_state(nodes[root]['representative_state']))
    r.update(complete=True,owner_zero_win=True,full_path_history_replay=True,seconds=monotonic()-start)
    return r


if __name__=='__main__':
    raw='docs/research/data/promoted_queen_strategy_20261006.json';out=ROOT/'docs/research/data/promoted_queen_verification_20261006.json'
    if out.exists():raise FileExistsError('preserve source-free verification')
    paths=(raw,'scripts/verify_promoted_queen_certificate.py','scripts/research_state_replay.py',
      'scripts/public_goal_intervals.py','scripts/audit_lichess_complete_children.py',
      'generic_chess/core/transition.py','generic_chess/core/terminal.py','generic_chess/rules/western_chess.py')
    try:r=verify(json.loads((ROOT/raw).read_text()))
    except Exception as e:r=dict(complete=False,error=f'{type(e).__name__}: {e}')
    r['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    write_record(out,r);print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}))
