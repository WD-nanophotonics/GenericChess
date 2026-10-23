"""Controlled Static/Unit candidate by Static/Unit reference Leaper portrait.

No training or inverse choice. Prepare on saved complete histories, then use
leaper_design preflight/run/qualify. All references share D3 and8192 node cap.
"""
from __future__ import annotations
import argparse,copy,json,time
from pathlib import Path
from datetime import datetime,timezone
from fractions import Fraction as F
from scripts import leaper_design as L
from scripts.leaper_budget_calibration import interval_mean,interval_sub,serial


def prepare(inputs, registration, output):
    assert not output.exists();tick=time.perf_counter();output.mkdir(parents=True)
    inp=L.load(inputs);r=copy.deepcopy(L.load(registration));ww=inp['worlds']
    assert len(ww)==12 and all(w['status']=='ready' for w in ww)
    for w in ww:
        c=L.compile_rule(L.ruleset_from_dict(w['rule']))
        s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['initial_record'])))
        assert L.record_value(s.state)==w['initial_state']
    L.write_record(output/'inputs.json',inp)
    r.update(frozen_at=datetime.now(timezone.utc).isoformat(),
        question='On the same12 full histories, does candidate Static-versus-Unit utility depend on whether the fixed D3 reference evaluates with Static or Unit?',
        changed_premise='Incoming independent review identifies evaluator alignment as an unresolved confound of price portraits. Old StaticD3 and FLOOR results are conditional; prior inverse recipe already stopped. This new six-rule cohort has no matching four-cell strong-reference results.',
        selection='ALL12 exposed complete uniform8 histories from six independently sampled literal rule triples and two placements; no outcome or price-divergence filter. Equal code/layout/role weights, not blind holdout or population inference.',
        pairs={'STATIC_vs_STATICD3':['STATIC_ADAPTER','STATIC_D3'],'UNIT_vs_STATICD3':['UNIT','STATIC_D3'],'STATIC_vs_UNITD3':['STATIC_ADAPTER','UNIT_D3'],'UNIT_vs_UNITD3':['UNIT','UNIT_D3']},
        roles=[0,1],first_repeat=0,repetitions=1,planned_games=96,
        search_variants={'STATIC_D3':{'base':'STATIC_ADAPTER','nodes':8192,'depth':3},'UNIT_D3':{'base':'UNIT','nodes':8192,'depth':3}},
        preflight_policies=['STATIC_ADAPTER','UNIT','STATIC_D3','UNIT_D3'],
        criterion='Report candidate Unit-minus-Static separately under each reference, interaction and role/layout signs. A strict role- or layout-specific sign reversal disproves reference-invariant ranking on these finite inputs. Opponent interaction alone does not establish causal evaluator-model alignment or intrinsic price superiority. No optimizer/learner/default gate.',
        nodes=512,whole_cap_seconds=1800,expected_seconds=1450,
        empirical_loop_forecast_seconds=1366.3044204,
        cost_basis='Prior same-cohort72mixed high-resource/depth/pricegames actual683.1522102seconds /72 *96 *1.5=1366.3044204 plus new complete-history48cost calls/preparation. This is empirical, not a worst-case guarantee; keep maximum-call forecast separately and cap1800unchanged. No legacycost reuse.',
        stop='96 physical games or original1800second cooperativecap including actual prep/preflight, preserve all missing/UNKNOWN; no broadening/refill or new references.',
        source_sha256=L.sha(Path(L.__file__)),preparer_sha256=L.sha(Path(__file__)),input_sha256=L.sha(output/'inputs.json'))
    r['preparation_seconds']=time.perf_counter()-tick;L.write_record(output/'registration.json',r)
    L.write_record(output/'preflight-inputs.json',{'roots':[{'world':w['world'],'phase':w['context'],'rule':w['rule'],'record':w['initial_record']}for w in ww]})
    print({'prepared':str(output),'planned':96,'fitness':0},flush=True)


def analyze(output):
    r=L.load(output/'results.json');ww=L.load(output/'inputs.json')['worlds'];assert r['status']=='CLOSED';ss={(x['world'],x['role'],x['pair']):x for x in r['slots']};rows=[]
    for w in ww:
        for role in (0,1):
            u={k:ss[w['world'],role,k]['utility']for k in L.load(output/'registration.json')['pairs']}
            a=interval_sub(u['UNIT_vs_STATICD3'],u['STATIC_vs_STATICD3']);b=interval_sub(u['UNIT_vs_UNITD3'],u['STATIC_vs_UNITD3'])
            rows.append(dict(world=w['world'],code=w['code_world'],placement=w['placement_index'],role=role,raw=u,unit_minus_static_with_static_reference=a,unit_minus_static_with_unit_reference=b,interaction=interval_sub(b,a),strict_rank_reversal=(a[0]>0 and b[1]<0) or (a[1]<0 and b[0]>0)))
    metrics=['unit_minus_static_with_static_reference','unit_minus_static_with_unit_reference','interaction'];groups={}
    for name,rr in [('ALL',rows)]+[(f'role{x}',[z for z in rows if z['role']==x])for x in (0,1)]+[(f'layout{x}',[z for z in rows if z['placement']==x])for x in (0,1)]+[(f'code{x}',[z for z in rows if z['code']==x])for x in range(6)]:
        means={k:interval_mean([z[k]for z in rr])for k in metrics};a=means[metrics[0]];b=means[metrics[1]];groups[name]=dict(contexts=len(rr),means=means,strict_rank_reversal=(a[0]>0 and b[1]<0) or(a[1]<0 and b[0]>0))
    out=dict(status='CLOSED',groups=groups,rows=rows,UNKNOWN=sum(s['utility'][0]!=s['utility'][1]for s in r['slots']),strict_individual_reversals=sum(z['strict_rank_reversal']for z in rows),scope='Finite chosen policy/reference/history controls, not intrinsic price rankings, WDL, learning utility, causally isolated model alignment, or independent population holdout.')
    L.write_record(output/'assessment.json',serial(out));print(serial({k:out[k]for k in ('groups','UNKNOWN','strict_individual_reversals')}),flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=['prepare','analyze']);p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path);p.add_argument('--source-registration',type=Path);a=p.parse_args()
    if a.command=='prepare':
        if a.inputs is None or a.source_registration is None:p.error('prepare requires inputs and source-registration')
        prepare(a.inputs,a.source_registration,a.output)
    else:analyze(a.output)
if __name__=='__main__':main()
