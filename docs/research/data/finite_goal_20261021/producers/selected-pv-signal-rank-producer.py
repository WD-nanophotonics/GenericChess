"""Selected-PV price-feature rank; no training, label fit or sampling gate.

Rank is descriptive identifiability of this frozen linear parameterization only.
At ties a selected branch is not a unique minimax derivative. Terminal outputs
are fixed constants, so their raw-price feature derivative is zero.
"""
from pathlib import Path
from collections import Counter
from dataclasses import replace
import json
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import write_record
base=Path('artifacts/price-regions-20261021');source=json.loads((base/'finite-decision-census.json').read_text());games=json.loads((base/'finite-opening-games.json').read_text())
output=base/'selected-pv-signal-rank.json'
if output.exists():raise FileExistsError(output)

def rank2(rows):
    nonzero=[v for v in rows if any(v)]
    if not nonzero:return 0
    x=nonzero[0]
    return 2 if any(x[0]*y[1]!=x[1]*y[0] for y in nonzero[1:]) else 1
result=dict(scope=__doc__,parameters=['boardH','boardB'],held_fixed='Anchor0, inert hand0, other state terms (if any) fixed, no parameter update',worlds=[])
for world in source['worlds']:
    c=compile_ruleset_for_execution(ruleset_from_dict(world['rule']));features={};validated=0
    for index,row in enumerate(world['rows']):
        for check in row['checks']:
            root=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])));owner=root.state.position.side_to_move
            for a in check['decision']['principal_variation']:
                # record_value retains the typed dataclass field names. Reconstruct
                # from the actual legal binding, never coordinates alone.
                options=[]
                for action in root.legal_actions():
                    from scripts.research_record import record_value
                    if record_value(action)==a:options.append(action)
                action,=options;root.submit(action)
            if root.state.terminal_status.is_terminal:v=(0,0)
            else:
                v=tuple(sum((1 if p.owner==owner else -1) for p in root.state.position.board if p is not None and p.current_type_id==tid) for tid in ('H','B'))
                if check['model']=='material1000':assert 1000*sum(v)==check['decision']['score']
            features[index,check['model'],check['depth']]=v;validated+=1
    summary=[]
    for model,depth in sorted({(x['model'],x['depth']) for row in world['rows'] for x in row['checks']}):
        vectors=[features[i,model,depth] for i,_ in enumerate(world['rows'])]
        summary.append(dict(model=model,depth=depth,full_reachable_rank=rank2(vectors),counts={str(k):v for k,v in Counter(vectors).items()}))
    traces=[]
    for game in games['games']:
        if game['world']!=world['world']:continue
        model=game['model'].rsplit('_D',1)[0];depth=int(game['model'].rsplit('_D',1)[1]);vectors=[];rows=[]
        for e in game['events']:
            prefix=game['record']['actions'][:e['ply']-1]
            index,row=next((i,r) for i,r in enumerate(world['rows']) if r['record']['actions']==prefix)
            active_model,active_depth=(model,depth) if e['candidate'] else ('material1000',3)
            v=features[index,active_model,active_depth]
            if e['candidate']:vectors.append(v)
            rows.append(dict(ply=row['ply'],candidate=e['candidate'],gradient=v))
        all_vectors=[tuple(x['gradient']) for x in rows]
        traces.append(dict(model=game['model'],result=game['outcome']['result'],candidate_only_rank=rank2(vectors),
            candidate_plus_fixed_foe_rank=rank2(all_vectors),candidate_vectors=vectors,all_turns=rows))
    result['worlds'].append(dict(world=world['world'],validated_literal_PVs=validated,summary=summary,opening_traces=traces))
write_record(output,result)
for w in result['worlds']:
    print(w['world'],'PVs',w['validated_literal_PVs']);print([(x['model'],x['depth'],x['full_reachable_rank']) for x in w['summary']]);print([(x['model'],x['result'],x['candidate_only_rank'],x['candidate_plus_fixed_foe_rank'],x['candidate_vectors']) for x in w['opening_traces']])
