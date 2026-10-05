"""Complete root-child reply widths before depth2 expansion; fixed two roots."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record,record_value
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.material_leaf_choice import material_score
from fractions import Fraction as F
OUT=ROOT/'docs/research/data/contact_narrow_width_20261005.json'
SOURCES=('scripts/audit_contact_narrow_width.py','docs/research/CONTACT_NARROW_SEARCH_PROTOCOL.md','docs/research/data/contact_narrow_preflight_20261005.json','scripts/public_goal_intervals.py','scripts/research_state_replay.py','scripts/chess_exact_contact_family.py','scripts/material_leaf_choice.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('fixed two-root width study never rerun')
    start=monotonic();r=dict(complete=False,rows=[],public_transitions=0,enumerated=0,source_queries=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec shared execution')
    def actions(state):
        table={str(a):a for a in game.actions(state,check)};r['enumerated']+=len(table)
        if len(table)>128 or r['enumerated']>5000:raise ValueError('action cap')
        return table
    def apply(state,action,width):
        check();r['enumerated']+=width
        if r['public_transitions']>=128 or r['enumerated']>5000:raise ValueError('same128/5000 execution cap')
        r['public_transitions']+=1;return game.successor(state,action)
    def save():write_record(OUT,r)
    try:
        pre=json.loads((ROOT/SOURCES[2]).read_text());assert pre['complete'] and len(pre['accepted'])==2
        game=PublicGame(compile_ruleset_for_execution(build_western_chess_ruleset()));pending=[]
        for accepted in pre['accepted']:
            root=read_game_state(accepted['root']);table=actions(root)
            if list(table)!=accepted['actions']:raise ValueError('preflight full-action drift')
            row=dict(root=accepted['root'],all_root_actions=list(table),branches={});r['rows'].append(row)
            for key,action in table.items():
                child=apply(root,action,len(table));terminal=game.terminal(child)
                replies={} if terminal.is_terminal else actions(child)
                branch=dict(state=record_value(child),all_enemy_actions=list(replies),leaves={});row['branches'][key]=branch
                pending.append((child,replies,branch));save()
        needed=r['public_transitions']+sum(len(table) for _,table,_ in pending)
        r['required_full_depth2_events']=needed;r['depth2_fits']=needed<=128;save()
        if r['depth2_fits']:
            for state,table,branch in pending:
                for key,action in table.items():branch['leaves'][key]=record_value(apply(state,action,len(table)));save()
            weights={law:{k:v[0] for k,v in exact_chess_contact_intervals(law).items()} for law in ('geometric_half','linear_mixture')}
            weights.update(unit={('board',t):F(1) for t in 'PNBRQ'},zero={('board',t):F(0) for t in 'PNBRQ'})
            def score(state,w):
                terminal=game.terminal(state)
                if terminal.is_terminal:return F(0 if terminal.winner is None else 1 if terminal.winner==0 else -1)
                return material_score(state.position,w,{'K'},30)
            for row in r['rows']:
                row['selections_before_ply3']={}
                for name,w in weights.items():
                    scores={key:min(score(read_game_state(leaf),w) for leaf in branch['leaves'].values()) if branch['all_enemy_actions'] else score(read_game_state(branch['state']),w) for key,branch in row['branches'].items()}
                    best=max(scores.values());ties=sorted(k for k,v in scores.items() if v==best)
                    row['selections_before_ply3'][name]=dict(selected=ties[0],tie_set=ties,scores=scores)
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('rows','source_sha256')}))
