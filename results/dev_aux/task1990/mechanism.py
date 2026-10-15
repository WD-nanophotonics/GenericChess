"""ALLTRAIN arms versusUNIT first-choice mechanism, no payoff-selected states."""
from pathlib import Path
from collections import Counter,defaultdict
import json
ROOT=Path('results/dev_aux/task1979');OUT=Path('results/dev_aux/task1990')
def run():
    results=[]
    for index in (0,1):
        folder=ROOT/f'cohort{index}';assert json.loads((folder/'completion.json').read_text(encoding='utf-8'))['status']=='COMPLETE'
        games=[json.loads(s) for s in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()];moves=[json.loads(s) for s in (folder/'moves.jsonl').read_text(encoding='utf-8').splitlines()];by_slot=defaultdict(list)
        for m in moves:by_slot[m['slot']].append(m)
        cells={(g['family'],g['candidate_side'],g['R']):g for g in games if g['phase']!='DEV'};grid=sorted({k[2] for k in cells});counts=Counter();pairs=[]
        for family in range(16):
            for side in (0,1):
                baseline=cells[family,side,720];a=by_slot[baseline['slot']]
                for r in grid:
                    if r==720:continue
                    other=cells[family,side,r];b=by_slot[other['slot']];first=None
                    for ply,(x,y) in enumerate(zip(a,b)):
                        assert x['ply']==y['ply']==ply
                        if x['choice']!=y['choice']:
                            assert x['before_state_sha']==y['before_state_sha'] and x['side']==y['side']
                            kind=('CANDIDATE_NORMAL' if x['source']=='EXTERNAL_SEARCH' and y['source']=='EXTERNAL_SEARCH' else 'CANDIDATE_OTHER_SOURCE') if x['side']==side else 'FIXED_OPPONENT_FIRST'
                            first=dict(kind=kind,ply=ply,side=x['side'],sources=[x['source'],y['source']],choices=[x['choice'],y['choice']],before_state_sha=x['before_state_sha'],elapsed=[x['seconds'],y['seconds']],search_nodes=[x['search_nodes'],y['search_nodes']],proof_nodes=[x['proof_nodes'],y['proof_nodes']]);break
                    if first is None:
                        if len(a)==len(b):
                            kind='IDENTICAL_COMPLETE_PATH';assert baseline['record']==other['record'] and baseline['outcome']==other['outcome']
                        else:kind='SAME_MOVE_PREFIX_DIFFERENT_LENGTH'
                    else:kind=first['kind']
                    counts[kind]+=1;pairs.append(dict(family=family,candidate_side=side,R=r,baseline_slot=baseline['slot'],other_slot=other['slot'],kind=kind,first=first,outcomes=[baseline['outcome'],other['outcome']]))
        assert len(pairs)==384
        results.append(dict(cohort=index,pairs=384,counts=dict(counts),all_pairs=pairs,scope='ALL13TRAINarms/ALL16families/bothroles versusUNIT, notoutcome/pricewinner-selected. FirstcandidateNORMALdifference showsprice-sensitivepolicyorclock/Nativevariation, notaloneproof of causalvaluegain. FIXED_OPPONENT_FIRST would disclose same-inputphysicalpolicyvariation; neverexcludeit orrerun. Samecompletepath gives exactlysameactualterminal, notfutureunlimitedWDL. No added Native/PN/reference calls.'))
    with (OUT/'result.json').open('x',encoding='utf-8') as f:json.dump(dict(status='PASS',cohorts=results),f,indent=2)
    print(json.dumps(dict(status='PASS',cohorts=[{k:x[k] for k in ('cohort','pairs','counts')} for x in results])))
if __name__=='__main__':run()
