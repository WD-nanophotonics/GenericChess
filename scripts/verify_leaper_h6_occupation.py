"""Independent direct full-history probability traversal for fixed H6 roots."""
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
import json,time,argparse
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_microgames import ExactTree
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record


def check(directory,occupation,plan):
    inputs=load(Path(directory)/'inputs.json.gz');by={r['id']:r for r in occupation['rows']};start=time.perf_counter();cases=[];contexts=0
    for family in inputs['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        source=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,source[0]);tree=ExactTree(c,max_states=plan['full_context_cap'],seconds=plan['family_cap_seconds'])
        for ix in sorted({0,len(source)//2,len(source)-1}):
            if time.perf_counter()-start>=plan['whole_cap_seconds']:raise RuntimeError('OCCUPATION_CHECK_CAP_UNKNOWN')
            sr=source[ix];s=GameSession.replay(c,deserialize_game_record(json.dumps(sr['full_record'])));tree.solve(s.state)
            expected=by[sr['state_sha256']];count=Counter();firstfork=[F(0)]*6;firstloss=[F(0)]*6;term=[F(0)]*3
            def walk(state,mass,sawfork=False,sawloss=False):
                children=tree.edges[state]
                if not children:
                    winner=state.terminal_status.winner;v=0 if winner is None else 1 if winner==0 else-1
                    term[v+1]+=mass;return
                count['expected_decisions']+=mass
                fork=len({tree.values[ch]for a,ch in children})>1
                if fork:
                    count['expected_fork_visits']+=mass
                    if not sawfork:firstfork[state.ply_count]+=mass
                for a,ch in children:
                    m=mass/len(children);bad=tree.values[ch]!=tree.values[state]
                    if bad:
                        count['expected_guarantee_lowering_decisions']+=m
                        if not sawloss:firstloss[state.ply_count]+=m
                    walk(ch,m,sawfork or fork,sawloss or bad)
            walk(s.state,F(1))
            if list(map(F,expected['uniform_terminal_LDW']))!=term:raise ValueError('terminal probability mismatch')
            if list(map(F,expected['first_fork_ply_mass']))!=firstfork or list(map(F,expected['first_lowering_ply_mass']))!=firstloss:raise ValueError('first event law mismatch')
            if any(F(expected[k])!=count[k]for k in ('expected_decisions','expected_fork_visits','expected_guarantee_lowering_decisions')):raise ValueError('occupation count mismatch')
            cases.append(dict(family=family['family'],row_index=ix,id=sr['state_sha256']))
        contexts+=len(tree.values)
    return dict(verified=True,occupation_digest=digest(occupation),cases=cases,full_history_contexts=contexts,
        seconds=time.perf_counter()-start,scope='33fixedmetadata roots/all11families,existing fullGameState ExactTree plus direct rational path-mass traversal; no compact occupation recurrence used for this control. All3616analytic laws remain certified by complete-domain/history recurrence, not33independent games.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--occupation',required=True);cli.add_argument('--plan',required=True);cli.add_argument('--output',required=True);a=cli.parse_args();r=check(a.directory,load(a.occupation),load(a.plan));save(a.output,r);print(json.dumps(r))
