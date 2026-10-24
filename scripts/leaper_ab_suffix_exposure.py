"""Reuse the existing full-history SuffixTree on original contact trajectories.

All original B1000 roots retained; clock suffixes are diagnostic only. One
cumulative cap preserves partial action frontiers as UNKNOWN, never DRAW.
"""
from pathlib import Path
import argparse,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,SOURCE,restore,write
from scripts.leaper_suffix_truth import SuffixTree,Limit
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict


def run(output):
    output.mkdir(parents=True,exist_ok=False);docs=source_documents()
    w=json.loads(docs['contact/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(w['rule']))
    slots=json.loads(docs['contact/results.json'])['slots'];candidates=[]
    for gi,slot in enumerate(slots):
        if slot['policy']!='B1000':continue
        game=json.loads(docs[f'contact/game-{gi:03d}.json']);s=restore(c,game['initial_record'])
        for q in game['queries']:
            if s.state.ply_count in (58,60,62):
                candidates.append(dict(game=gi,root=slot['root'],ply=s.state.ply_count,
                    state_sha256=L.state_sha(s.state),record=L.record_value(s.to_record())))
            s.submit(L.match_action(s,q['action']))
    candidates.sort(key=lambda r:(64-r['ply'],r['root'],r['game']))
    spec=dict(source=SOURCE,question='Do actual late-clock A/B histories contain different forced-WDL actions or merely cooperative terminal opportunities?',
        selection='All existing B1000 contact games at absolute ply62,60,58, sorted remaining then original root. No oracle filtering; retained histories are diagnostics, never training starts.',
        candidates=candidates,caps=dict(nodes=1000000,seconds=900),
        stop='One cumulative original cap; unfinished/unstarted roots/actions UNKNOWN, no refill/replacement.',
        solver='Unchanged scripts.leaper_suffix_truth.SuffixTree; complete Core GameState/history, no Position cache or repeat quotient.')
    write(output/'spec.json',spec);tree=SuffixTree(**spec['caps']);rows=[];status='COMPLETE'
    for r in candidates:
        s=restore(c,r['record']);assert L.state_sha(s.state)==r['state_sha256']
        start=time.perf_counter();before=tree.nodes;branches=[];stopped=None
        # Enumerate the complete actual legal root frontier, then stream each tree.
        children=list(legal_successors(s.state,c))
        for a,ch in children:
            try:future,value,witness=tree.solve(ch,c)
            except Limit as e:stopped=str(e);break
            if witness is not None:
                z=L.GameSession.replay(c,s.to_record());z.submit(a)
                for ac in witness:z.submit(L.match_action(z,ac))
                assert z.state.terminal_status.is_terminal and z.result.winner is not None
            branches.append(dict(action=action_to_dict(a),wdl_player0=value,
                terminal_outcomes_player0=sorted(future),decisive_witness=witness))
        complete=len(branches)==len(children)
        values=[b['wdl_player0']for b in branches]
        rows.append(dict(game=r['game'],root=r['root'],ply=r['ply'],state_sha256=r['state_sha256'],
            complete=complete,legal_count=len(children),branches=branches,
            wdl_player0=(max if s.state.position.side_to_move==0 else min)(values)if complete else None,
            different_action_WDL=len(set(values))>1 if complete else None,
            any_cooperative_decisive=any(set(b['terminal_outcomes_player0'])-{0}for b in branches),
            nodes=tree.nodes-before,seconds=time.perf_counter()-start,stop=stopped))
        write(output/'partial.json',dict(status='RUNNING',rows=rows,nodes=tree.nodes))
        print('suffix',r['root'],r['ply'],complete,tree.nodes,flush=True)
        if stopped:status=stopped;break
    result=dict(source=SOURCE,status=status,rows=rows,nodes=tree.nodes,edges=tree.edges,
        terminal_visits=dict(tree.terminals),seconds=time.perf_counter()-tree.began,
        unstarted=candidates[len(rows):],scope='Only COMPLETE root frontiers are exact WDL/outcome exposure. Any partial lower cooperative witness is existential, not universal. No new Player, training, full graph or policy sample.')
    write(output/'result.json',result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.output)
