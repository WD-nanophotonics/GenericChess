"""Finite three-cell budget calibration on saved complete Leaper inputs.

Prepare does not query Player. Run preflight/run/qualify with leaper_design.
The output is policy- and distribution-specific; it is not intrinsic fairness,
learning potential, a WDL oracle, or a replacement inverse-design objective.
"""
from __future__ import annotations
import argparse
import copy
from fractions import Fraction
from pathlib import Path
import time
from datetime import datetime, timezone
from scripts import leaper_design as L


def interval_sub(a, b):
    return [Fraction(a[0])-Fraction(b[1]), Fraction(a[1])-Fraction(b[0])]


def interval_mean(rows):
    if not rows:
        return None
    return [sum(Fraction(x[i]) for x in rows)/len(rows) for i in (0, 1)]


def effects(ll, hl, lh):
    # All three payoffs are physical actor0, including the LH game.
    g0, g1 = interval_sub(hl, ll), interval_sub(ll, lh)
    return dict(seat_baseline=list(map(Fraction,ll)), own0_fixed_low=g0,
                own1_fixed_low=g1, balanced=interval_mean([g0,g1]),
                cross_balanced=[x/2 for x in interval_sub(hl,lh)])


def serial(value):
    if isinstance(value,Fraction):
        return str(value)
    if isinstance(value,dict):
        return {str(k):serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):
        return [serial(v) for v in value]
    return value


def prepare(inputs, source_registration, output):
    assert not output.exists(), 'new output only; never refill frozen results'
    tick=time.perf_counter(); output.mkdir(parents=True)
    source=L.load(inputs); old=L.load(source_registration); worlds=source['worlds']
    assert len(worlds)==12 and all(w['status']=='ready' for w in worlds)
    assert [w['world'] for w in worlds]==list(range(12))
    assert len({(w['code_world'],w['placement_index']) for w in worlds})==12
    for w in worlds:
        c=L.compile_rule(L.ruleset_from_dict(w['rule']))
        s=L.GameSession.replay(c,L.deserialize_game_record(__import__('json').dumps(w['initial_record'])))
        assert L.record_value(s.state)==w['initial_state']
    L.write_record(output/'inputs.json',source)
    reg=copy.deepcopy(old)
    reg.update(frozen_at=datetime.now(timezone.utc).isoformat(),
        question='Do both physical roles have practically positive fixed128 own-budget gains on this exposed 12-root six-rule cohort?',
        changed_premise='Raw seat utility confounds the low-policy seat baseline. Three cells identify own gains; decomposition identity itself cannot be a scientific transfer hypothesis. Old inverse recipe remains stopped.',
        selection='ALL 12 saved complete uniform8 histories; six rule triples, two fixed layouts, equal weights. Exposed cohort, not independent holdout. No result/policy/terminal filtering.',
        pairs={'LL':['STATIC128','STATIC128'],'HL':['STATIC_ADAPTER','STATIC128'],'LH':['STATIC128','STATIC_ADAPTER']},
        roles=[0],repetitions=1,first_repeat=0,planned_games=36,
        search_variants={'STATIC128':{'base':'STATIC_ADAPTER','nodes':128}},
        preflight_policies=['STATIC128','STATIC_ADAPTER'],
        input_sha256=L.sha(output/'inputs.json'),source_sha256=L.sha(Path(L.__file__)),
        preparer_sha256=L.sha(Path(__file__)),whole_cap_seconds=900,expected_seconds=600,
        criterion='Finite diagnostic hypothesis: each role mean fixed128 own gain >=1/12, and each role/layout mean >=-1/6. One net utility step over12roots is the minimum signal for considering a resource coordinate; -1/6 allows at most one net step over6roots per layout. Any failure stops using this cohort as robust resource-screen evidence. No optimizer/learner/default gate; no retuning thresholds.',
        minimum_role_gain='1/12',minimum_layout_role_gain='-1/6',
        cost_basis='Before fitness: prior72 actual loop683.1522102/72*36*1.5=512.36415765s, plus actual preparation/full-history preflight; expected600, cooperative900 cap. Keep stock maximum-call forecast separately; sampled max is not future bound. All new calls charged, no old cost reuse.',
        empirical_loop_forecast_seconds=512.36415765,
        stop='36 physical games or original900s cap including preparation/preflight; preserve missing slots and UNKNOWN, no refill/HH addition/old cap reset.')
    reg['preparation_seconds']=time.perf_counter()-tick
    L.write_record(output/'registration.json',reg)
    L.write_record(output/'preflight-inputs.json',{'roots':[{'world':w['world'],'phase':w['context'],'rule':w['rule'],'record':w['initial_record']} for w in worlds]})
    print({'prepared':str(output),'physical_games':36,'new_Player_calls':0,'full_history_roundtrips':12},flush=True)


def analyze(output):
    reg=L.load(output/'registration.json'); worlds=L.load(output/'inputs.json')['worlds']; results=L.load(output/'results.json')
    assert results['status']=='CLOSED'
    slots={(s['world'],s['pair']):s for s in results['slots']}
    rows=[]
    for w in worlds:
        ss={k:slots[w['world'],k] for k in ('LL','HL','LH')}
        e=effects(*(ss[k]['utility'] for k in ('LL','HL','LH')))
        # Interval subtraction loses shared LL dependency: check identity only
        # on exact observations. Report direct cross interval separately.
        exact=all(s['utility'][0]==s['utility'][1] for s in ss.values())
        if exact:
            assert e['balanced']==e['cross_balanced']
        rows.append(dict(world=w['world'],code=w['code_world'],placement=w['placement_index'],
            immediate=w['initial_oneply_wins'],exact=exact,
            cells={k:s['utility'] for k,s in ss.items()},effects=e))
    groups={}
    for name,rr in [('ALL',rows)]+[(f'layout{p}',[x for x in rows if x['placement']==p]) for p in (0,1)]+[(f'code{c}',[x for x in rows if x['code']==c]) for c in sorted({x['code'] for x in rows})]+[(f'immediate{b}',[x for x in rows if bool(x['immediate'])==b]) for b in (False,True)]:
        groups[name]={'roots':len(rr),'means':{k:interval_mean([x['effects'][k] for x in rr]) for k in effects([0,0],[0,0],[0,0])}}
    hypothesis=all(groups['ALL']['means'][k][0]>=Fraction(reg['minimum_role_gain']) for k in ('own0_fixed_low','own1_fixed_low')) and all(groups[f'layout{p}']['means'][k][0]>=Fraction(reg['minimum_layout_role_gain']) for p in (0,1) for k in ('own0_fixed_low','own1_fixed_low'))
    out=dict(status='CLOSED',new_physical_games=len([s for s in results['slots'] if s['status']=='finished']),UNKNOWN=sum(s['utility'][0]!=s['utility'][1] for s in results['slots']),hypothesis_supported=hypothesis,groups=groups,rows=rows,limits='Finite exposed cohort and exact chosen policy/protocol only. Missing shared-baseline dependencies widen marginal intervals; use direct paired interval for balanced effect. No HH/reference-interaction/WDL/learning/default claim.')
    L.write_record(output/'assessment.json',serial(out));print(serial({k:out[k] for k in ('new_physical_games','UNKNOWN','hypothesis_supported','groups')}),flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=['prepare','analyze']);p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path);p.add_argument('--source-registration',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if a.inputs is None or a.source_registration is None:p.error('prepare requires inputs and source-registration')
        prepare(a.inputs,a.source_registration,a.output)
    else:analyze(a.output)
if __name__=='__main__':main()
