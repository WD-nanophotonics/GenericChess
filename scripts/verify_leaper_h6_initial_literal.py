"""Existing full-GameState ExactTree check of the new compact H6 truth."""
from pathlib import Path
from collections import Counter
import json,time,argparse,gc
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_microgames import ExactTree,Exhaustion,role_stop_requested
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_design import state_sha


def verify(inputs,truth,plan,output):
    start=time.perf_counter();by={r['id']:r for r in truth['roots']};summary=[];total=Counter()
    for family in inputs['families']:
        if family['status']=='MU_UNAVAILABLE':continue
        rows=[r for r in inputs['rows']if r['family']==family['family']]
        if time.perf_counter()-start>=plan['whole_cap_seconds']or role_stop_requested():break
        c=admit(family,rows[0]);tree=ExactTree(c,max_states=plan['full_GameState_contexts_per_family'],seconds=min(plan['family_cap_seconds'],plan['whole_cap_seconds']-(time.perf_counter()-start)))
        status='COMPLETE';roots=[]
        try:
            for row in rows:
                session=GameSession.replay(c,deserialize_game_record(json.dumps(row['full_record'])))
                if state_sha(session.state)!=row['state_sha256']:raise ValueError('literal root binding mismatch')
                value=tree.solve(session.state);expected=by[row['state_sha256']]
                branch=[tree.values[ch]for a,ch in tree.edges[session.state]]
                if expected['wdl_bounds']!=[value,value]or expected['wdl_fork']!=(len(set(branch))>1):
                    raise ValueError('full history WDL/fork disagrees with compact solver')
                roots.append((row['state_sha256'],session.state))
        except Exhaustion as exc:status=str(exc)
        future={}
        for state in sorted(tree.values,key=lambda s:s.ply_count,reverse=True):
            children=tree.edges[state]
            if not children:future[state]=state.terminal_status.winner is not None
            else:
                # A stopped ExactTree may retain unresolved edges. Never fill
                # them with draw/false; only completed values are usable.
                if not all(ch in future for a,ch in children):continue
                future[state]=any(future[ch]for a,ch in children)
        for hid,state in roots:
            if future.get(state)is not by[hid]['cooperative_decisive']:
                raise ValueError('literal history/cooperative proof disagree')
        item=dict(family=family['family'],status=status,roots_checked=len(roots),planned_roots=len(rows),
            full_history_contexts=len(tree.values),charged_contexts=tree.visits,
            full_history_edges=sum(len(tree.edges[s])for s in tree.values),seconds=time.perf_counter()-tree.began)
        summary.append(item)
        total['roots']+=len(roots);total['contexts']+=len(tree.values);total['edges']+=item['full_history_edges']
        print(json.dumps(item),flush=True)
        result=dict(verified=total['roots']==len(inputs['rows'])and all(f['status']=='COMPLETE'for f in summary),families=summary,
            counts=dict(total),source_digest=digest(inputs),truth_digest=digest(truth),seconds=time.perf_counter()-start,
            scope='Existing ExactTree fullGameState/history and actualCore legal_actions/apply_action,not compact Position/visitedset memo. Checks WDL/actionfork/cooperativeoutcomes of actualfrozenfreshroots; sharedCore is not a separate engine.')
        save(output,result);del tree,future,roots;gc.collect()
    return result


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--input',required=True);cli.add_argument('--truth',required=True);cli.add_argument('--plan',required=True);cli.add_argument('--output',required=True);a=cli.parse_args()
    r=verify(load(a.input),load(a.truth),load(a.plan),a.output);print(json.dumps(r))
