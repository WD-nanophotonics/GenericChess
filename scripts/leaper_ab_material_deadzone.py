"""Closed physical subdomains reached by the original A/B games.

Core supplies every transition. Physical decisive values are NOT full-history
WDL. A complete domain with no decisive terminal certifies universal draw
under the source rule's draw-only repetition/clock. No oracle training roots.
"""
from collections import deque,Counter
from pathlib import Path
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,SOURCE,restore,write
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_cooperative_certificate import encode_position
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.transition import legal_successors


def run(output):
    output.mkdir(parents=True,exist_ok=False);docs=source_documents();world=json.loads(docs['contact/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    examples={};actual=[]
    for gi,slot in enumerate(json.loads(docs['contact/results.json'])['slots']):
        game=json.loads(docs[f'contact/game-{gi:03d}.json']);s=restore(c,game['initial_record'])
        for q in game['queries']:
            composition=tuple(sorted((p.owner,p.current_type_id)for p in s.state.position.board if p))
            if len(composition)<=4:
                key=str(composition);examples.setdefault(key,L.record_value(s.to_record()));actual.append((gi,s.state.ply_count,key,s.state.position,L.state_sha(s.state)))
            s.submit(L.match_action(s,q['action']))
    # Source order, all actually observed <=4actor compositions. No new layout.
    spec=dict(source=SOURCE,rule=world['rule'],examples=examples,
        question='Are the B-sensitive material remnants actually universal-draw deadzones, rather than evidence that B has no conditional value?',
        selection='All <=4actor compositions in original contact games, first literal source record per composition. Posthoc truth only, never experiential starts or a generator campaign.',
        caps=dict(states_per_domain=350000,whole_seconds=1200),
        scope='Fixed plain remove King8/Ferz/Wazir/H64repeat4 source only. Position graph describes moves/static terminals; decisive labels remain physical/UNKNOWN for history. Complete no-mate closure gives universalDRAW through draw-only stops. Partial domains never get labels.')
    write(output/'spec.json',spec);began=time.perf_counter();summaries=[]
    for number,(key,record)in enumerate(examples.items()):
        root=restore(c,record);positions=[root.state.position];indices={positions[0]:0};queue=deque([0]);edges=[];terms={};counts=Counter();stop=None;tick=time.perf_counter()
        while queue:
            if role_stop_requested():stop='USER_STOP';break
            if time.perf_counter()-began>=1200:stop='WHOLE_CAP_UNKNOWN';break
            i=queue.popleft();p=positions[i];state=fresh_state(p,c)
            if state.terminal_status.is_terminal:
                terms[i]=state.terminal_status.winner;counts[state.terminal_status.status.value]+=1;edges.append([]);continue
            ee=[]
            for a,ch in legal_successors(state,c):
                cp=ch.position
                if cp not in indices:
                    if len(positions)>=350000:stop='VERTEX_CAP_UNKNOWN';break
                    indices[cp]=len(positions);positions.append(cp);queue.append(indices[cp])
                ee.append(indices[cp])
            if stop:break
            edges.append(ee)
            if i%10000==0:print('domain',number,i,len(positions),round(time.perf_counter()-tick,2),flush=True)
        complete=not queue and stop is None and len(edges)==len(positions)
        values=None;ranks=None;universal=None
        if complete:
            relative={i:0 if w is None else 1 if w==positions[i].side_to_move else-1 for i,w in terms.items()}
            values,ranks=attractor(edges,relative);universal=not any(w is not None for w in terms.values())
        matches=[dict(game=gi,ply=ply,state_sha256=sha,index=indices.get(p),
            physical_value=None if not complete or p not in indices else values[indices[p]]*(1 if p.side_to_move==0 else-1),
            full_history_universal_draw=True if universal and p in indices else None)
            for gi,ply,composition,p,sha in actual if composition==key]
        summary=dict(domain=number,composition=key,complete=complete,status=stop or'COMPLETE',positions=len(positions),expanded=len(edges),edges=sum(map(len,edges)),terminal_reasons=dict(counts),universal_draw=universal,actual_contexts=matches,seconds=time.perf_counter()-tick)
        if complete:
            graph=dict(source=SOURCE,rule=world['rule'],root_record=record,composition=key,
                positions=[encode_position(p,c.initial_position)for p in positions],edges=edges,terminals=terms,relative_values=values,ranks=ranks)
            (output/f'domain-{number}.json.gz').write_bytes(gzip.compress(json.dumps(graph,separators=(',',':')).encode(),mtime=0))
            summary['graph_sha256']=L.sha(output/f'domain-{number}.json.gz')
        summaries.append(summary);write(output/'partial.json',dict(rows=summaries,seconds=time.perf_counter()-began));print(summary['composition'],complete,summary['positions'],universal,flush=True)
        if stop=='USER_STOP'or time.perf_counter()-began>=1200:break
    result=dict(source=SOURCE,rows=summaries,unstarted=list(examples)[len(summaries):],seconds=time.perf_counter()-began)
    write(output/'result.json',result);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.output)
