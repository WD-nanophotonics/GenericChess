"""One posthoc odd-Ferz component from actual old quiet experience.

No rule generation, Player or learning. Reuse Core legal_successors and the
existing finite graph attractor; actual history labels remain separate.
"""
from pathlib import Path
from collections import deque,Counter
import argparse,gzip,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,restore,write
from scripts.leaper_cooperative_certificate import encode_position
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.transition import legal_successors


def plan(output):
    output.mkdir(parents=True,exist_ok=False);world=json.loads(source_documents()['two-type/inputs.json']);c=L.compile_rule(L.ruleset_from_dict(world['rule']))
    old=Path('artifacts/leaper-ab-uniform-20261024');r=json.loads((old/'result.json').read_bytes());selected=None
    for entry in r['rows']:
        slot=entry['slot']
        if slot['group']!='two-type':continue
        row=json.loads((old/f"game-{slot['id']:03d}.json").read_bytes());s=restore(c,world['roots'][slot['root']]['record'])
        for action in L.deserialize_game_record(json.dumps(row['final_record'])).actions:
            pieces=[(p.owner,p.current_type_id)for p in s.state.position.board if p]
            if sorted(pieces)==[(0,'A'),(0,'B'),(0,'K'),(1,'K')]:
                square=next(i for i,p in enumerate(s.state.position.board)if p and p.current_type_id=='A')
                if (square//5+square%5)%2==1:selected=dict(slot=slot,record=L.record_value(s.to_record()),state_sha256=L.state_sha(s.state),A_square=square,source_game_sha256=L.sha(old/f"game-{slot['id']:03d}.json"));break
            s.submit(action)
        if selected:break
    if selected is None:raise ValueError('no actual odd-Ferz source history in declared source order')
    spec=dict(source='56560fb3e24102792f72a005c5c5bdb52526943f',rule=world['rule'],selected=selected,producer_sha256=L.sha(Path(__file__)),
        question='Does a literally visited odd-Ferz A+B/bareK component change the known-versus-UNKNOWN exposure interpretation?',
        selection='First old actual Uniform quiet record/ply with A0+B0/bareK1 and odd-parity Ferz square. Posthoc component structure diagnostic, never an experiential root or oracle rule sampler. All original TRAIN records remain unchanged.',
        states_cap=350000,expansion_seconds=900,expected_seconds=520,qualification_expected_seconds=800,
        budget='Independent finite truth question, not an extension/refill of the active deeper-target experiment. Previous similar240kclosure383.9s and qualification323s. Cooperative expansion cap900s plus finite<=350k attractor/serialization, both target-owner qualifications forecast800s and analysis remain under120min. All actual time charged; not a strict OS wall watchdog. Failed/partial expansion UNKNOWN; no cap extension.',
        scope='Actual quiet fullRuleSet compiled. Closed physical WDL does not become historyWDL except proven draw safety. No reuse by piece counts alone, default policy, Player or TRAIN.')
    write(output/'spec.json',spec);return spec


def run(output):
    spec=json.loads((output/'spec.json').read_bytes());assert L.sha(Path(__file__))==spec['producer_sha256']
    with(output/'execution.json').open('x',encoding='utf8')as f:json.dump(dict(started=time.time()),f)
    c=L.compile_rule(L.ruleset_from_dict(spec['rule']));root=restore(c,spec['selected']['record']);positions=[root.state.position];indices={positions[0]:0};queue=deque([0]);edges=[];terms={};counts=Counter();tick=time.perf_counter();stop=None
    while queue:
        if role_stop_requested():stop='USER_STOP';break
        if time.perf_counter()-tick>=spec['expansion_seconds']:stop='EXPANSION_CAP_UNKNOWN';break
        i=queue.popleft();s=fresh_state(positions[i],c)
        if s.terminal_status.is_terminal:terms[i]=s.terminal_status.winner;counts[s.terminal_status.status.value]+=1;edges.append([]);continue
        ee=[]
        for a,ch in legal_successors(s,c):
            p=ch.position
            if p not in indices:
                if len(positions)>=spec['states_cap']:stop='VERTEX_CAP_UNKNOWN';break
                indices[p]=len(positions);positions.append(p);queue.append(indices[p])
            ee.append(indices[p])
        if stop:break
        edges.append(ee)
        if i%10000==0:print(i,len(positions),round(time.perf_counter()-tick,2),flush=True)
    complete=stop is None and not queue and len(edges)==len(positions)
    if complete:
        terminal={i:0 if w is None else 1 if w==positions[i].side_to_move else-1 for i,w in terms.items()};values,ranks=attractor(edges,terminal)
        graph=dict(source=spec['source'],rule=spec['rule'],root_record=spec['selected']['record'],positions=[encode_position(p,c.initial_position)for p in positions],edges=edges,terminals=terms,relative_values=values,ranks=ranks)
        (output/'domain.json.gz').write_bytes(gzip.compress(json.dumps(graph,separators=(',',':')).encode(),mtime=0))
    result=dict(complete=complete,status='COMPLETE'if complete else stop or'INCOMPLETE_UNKNOWN',vertices=len(positions),expanded=len(edges),edges=sum(map(len,edges)),terminal_reasons=dict(counts),universal_draw=not any(w is not None for w in terms.values())if complete else None,graph_sha256=L.sha(output/'domain.json.gz')if complete else None,physical_root_value=values[0]*(1 if root.state.position.side_to_move==0 else-1)if complete else None,seconds=time.perf_counter()-tick,Player_queries=0,training_updates=0)
    write(output/'result.json',result);print(result,flush=True);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('plan','run'));ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();globals()[a.mode](a.output)
