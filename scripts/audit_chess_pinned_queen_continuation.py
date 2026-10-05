"""Continue exact persisted partial states; no old transition replay."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.coordinates import Square
from generic_chess.core.semantic_executor import SemanticAction,semantic_engine_for,_semantic_public_action
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.public_goal_intervals import PublicGame
from scripts.research_state_replay import read_game_state
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/chess_pinned_queen_continuation_20261005.json'
SOURCES=('scripts/audit_chess_pinned_queen_continuation.py','docs/research/CHESS_PINNED_QUEEN_CONTINUATION_SCOPE.md',
 'docs/research/data/chess_pinned_queen_mate_20261005.json','docs/research/data/chess_pinned_queen_mate_20261005.selections.json',
 'scripts/research_state_replay.py','scripts/research_record.py','scripts/public_goal_intervals.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen partial-state continuation never rerun')
    start=monotonic();r=dict(complete=False,public_transitions=0,enumerated=0,source_queries=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def save():r['seconds']=monotonic()-start;write_record(OUT,r)
    def check():
        if monotonic()-start+0.141>=15:raise TimeoutError('same15sec cumulative computation cap')
    save()
    try:
        old=json.loads((ROOT/SOURCES[2]).read_text());pre=json.loads((ROOT/SOURCES[3]).read_text())
        if old['complete'] or old['public_transitions']!=22 or 'unique' not in old['error']:raise ValueError('specific saved partial required')
        for name,pin in old['source_sha256'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=pin:raise ValueError('old source drift')
        c=compile_ruleset_for_execution(build_western_chess_ruleset());game=PublicGame(c);e=semantic_engine_for(c)
        def actions(state):
            check();a={str(a):a for a in game.actions(state,check)};r['enumerated']+=len(a)
            if len(a)>128 or r['enumerated']+495>5000:raise ValueError('same action cap')
            return a
        def apply(state,action,count):
            check();r['enumerated']+=count
            if r['enumerated']+495>5000 or r['public_transitions']+22>=128:raise ValueError('same event/member cap')
            r['public_transitions']+=1;child=game.successor(state,action);check();return child
        if len(old['candidate_all_replies'])!=1 or len(old['candidate_replies'])!=1:raise ValueError('complete singleton enemy branch required')
        row=old['candidate_replies'][0];state=read_game_state(row['enemy_child'])
        action=_semantic_public_action(e,SemanticAction('sem_08_q_quiet',62,59,None,'Q','g21'))
        if str(action) not in row['all_own_replies']:raise ValueError('saved named action missing')
        end=apply(state,action,len(row['all_own_replies']));r['candidate_mate']=dict(action=str(action),state=record_value(end));save()
        if game.terminal(end).status.value!='checkmate' or game.terminal(end).winner!=0:raise ValueError('candidate mate not proved')
        r['baseline_counterbranches']={};picks=pre['selections_before_labels'];save()
        for selected in sorted({picks[name]['selected'] for name in ('unit','zero')}):
            child=read_game_state(pre['children'][selected]);table=actions(child)
            branch=dict(all_enemy_replies=list(table),own_rows=[]);r['baseline_counterbranches'][selected]=branch;save()
            counter=[(k,a) for k,a in table.items() if getattr(a,'actor_type_id',None)=='Q' and getattr(a,'from_square',None)==Square(6,7) and getattr(a,'to_square',None)==Square(7,7)]
            if len(counter)!=1:raise ValueError('Qxh8 counterreply not unique/legal')
            after=apply(child,counter[0][1],len(table));own=actions(after)
            branch.update(enemy_action=counter[0][0],enemy_child=record_value(after),all_own_replies=list(own));save()
            if not own:raise ValueError('expected legal counterresponses absent')
            for key,action in own.items():
                end=apply(after,action,len(own));t=game.terminal(end)
                branch['own_rows'].append(dict(action=key,state=record_value(end)));save()
                if t.status.value=='checkmate' and t.winner==0:raise ValueError('baseline can force window mate against counterreply')
        r['window_values']=dict(contact=1,unit=0,zero=0);r['game_value_intervals']=dict(contact=[1,1],unit=[-1,1],zero=[-1,1]);r['full_goal_regret']=dict(contact=[0,0],unit=[0,2],zero=[0,2]);r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());save()
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','candidate_mate','baseline_counterbranches')}))
