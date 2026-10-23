"""Prepare a new E0/E1 temporal prefix transfer, without oracle or old refills."""
import argparse,copy,json,random,time
from datetime import datetime,timezone
from pathlib import Path
from scripts import leaper_design as L


def prepare(d,calibration,proposal):
    assert not d.exists();d.mkdir();tick=time.perf_counter();old=L.load(calibration/'inputs.json')['worlds'];analysis=L.load(calibration/'e0-analysis.json');train=[w for w in analysis['world_predictions'] if not w['terminal_at_start'] and w['label_any_role_nonzero_interaction'] is not None];assert len(train)==23
    bins={str(v):{'n':sum(w['positive_feature']==v for w in train),'positive':sum(w['positive_feature']==v and w['label_any_role_nonzero_interaction']==1 for w in train)} for v in (False,True)}
    probabilities={k:(v['positive']+1)/(v['n']+2) for k,v in bins.items()};constant=(sum(w['label_any_role_nonzero_interaction'] for w in train)+1)/(len(train)+2)
    plan={'frozen_at':datetime.now(timezone.utc).isoformat(),'question':'Does the observed root-action feature add prospective predictive information over a stronger calibratedconstant, for any-role finite price/horizon interaction under onefixedStaticD3reference?','changed_premise':'First24E0cohort has5TP/6FP/2FN/11TN andBrier5.4375vs5.75, butweak.5baseline. FitBOTH E1two-bin andconstant from23nonterminalcalibrationcontexts ONLY, withLaplace(1,1). Need new independentprefixseedstream, not reusinglabels as test.','selection':'ALL6exposedrules/2layouts/EIGHTnewuniform8prefixes;96contexts,768physicalslots. No outcome/oracle/rootfeature filtering. Keepterminalstarts. Temporalprefixtransfer only, masks/families alreadyexposed.','calibration':{'directory_label':calibration.name,'analysis_sha256':L.sha(calibration/'e0-analysis.json'),'input_sha256':L.sha(calibration/'inputs.json'),'bins':bins,'probability_by_feature':probabilities,'constant':constant,'Laplace_pseudocounts':[1,1],'n':23},'criterion':'Primary score is summedBrier(constant)-summedBrier(E1) overALL96contexts withUNKNOWNscorebounds retained. Practical utility: meanimprovement>=.02 to justifyretainingaddedrootfeatures; perrole/layout/oldpositive-rule exclusions descriptive. Ifbelow .02 do notretainfeature basedontest, no retraining orthresholdchange. Also reportfrozenoriginalE0 and nofeature .5 reference. It is not stronggameplayadoption or populationcalibration.','cost':'Observed predecessor192gameproducer520.1607321seconds +115preflight17.8567417seconds. New768games planning4xloopx1.35=2808.868s,475anticipatedcostcalls~74s,preparation~2s,necessaryqualificationanalysis reserve600s. Expected~3500seconds58.3min;producer cap3600,total logicalcap4200s70min<120min. Maxsampleforecastseparate, genuine oldsameinterface measured fullgame empiricalbasis. Frozenclosedsmall3piece1920scope isnotrestarted orfilled.','stop':'ALL768slotsorproducer3600secondsinclprep/preflight; total4200secondsinclusivequalificationanalysis. PreserveallUNKNOWN, no refill/extension/streamreplacement ormodelrefit.'}
    L.write_record(d/'plan-before-generation.json',plan);worlds=[];seen=set();seed0=202610231225
    original_by={(w['code_world'],w['placement_index']):w for w in old};exposed=old+L.load(proposal/'inputs.json')['worlds']
    for (_,layout),ow in sorted(original_by.items()):
        c=L.compile_rule(L.ruleset_from_dict(ow['rule']))
        for pi in range(8):
            s=L.GameSession(c);seed=seed0+10000*ow['code_world']+100*layout+pi;rng=random.Random(seed)
            for _ in range(8):
                if s.state.terminal_status.is_terminal:break
                aa=s.legal_actions();s.submit(aa[rng.randrange(len(aa))])
            w=copy.deepcopy(ow);w.update(world=len(worlds),prefix_index=pi,prefix_seed=seed,context='prospectiveE1uniform8',initial_record=L.record_value(s.to_record()),initial_state=L.record_value(s.state),initial_terminal=L.record_value(s.result),initial_legal_count=len(s.legal_actions()));worlds.append(w)
    L.write_record(d/'inputs.json',{'scope':plan['selection'],'worlds':worlds});r=copy.deepcopy(L.load(calibration/'registration.json'));r.update(frozen_at=datetime.now(timezone.utc).isoformat(),question=plan['question'],changed_premise=plan['changed_premise'],selection=plan['selection'],planned_games=768,seed=202610231226,expected_seconds=3500,whole_cap_seconds=3600,logical_cap_seconds=4200,validation_analysis_reserve_seconds=600,empirical_loop_forecast_seconds=520.1607320999028*4*1.35,cost_basis=plan['cost'],criterion=plan['criterion'],stop=plan['stop'],calibration=plan['calibration'],calibrated_probability_by_feature=probabilities,calibrated_constant_probability=constant,preparer_sha256=L.sha(Path(__file__)),input_sha256=L.sha(d/'inputs.json'))
    roots=[{'world':w['world'],'rule':w['rule'],'record':w['initial_record'],'phase':'prospectiveE1uniform8'} for w in worlds if w['initial_terminal']['status']=='ongoing'];L.write_record(d/'preflight-inputs.json',{'roots':roots});r['preparation_seconds']=time.perf_counter()-tick;L.write_record(d/'registration.json',r)
    def key(w,f):return json.dumps([w['rule'],w[f]],sort_keys=True,separators=(',',':'))
    oldhist={key(w,'initial_record') for w in exposed};oldstate={key(w,'initial_state') for w in exposed};meta={'worlds':len(worlds),'terminalprefixes':sum(w['initial_terminal']['status']!='ongoing' for w in worlds),'exact_old_history_matches':sum(key(w,'initial_record') in oldhist for w in worlds),'exact_old_state_matches':sum(key(w,'initial_state') in oldstate for w in worlds),'distinct_literal_histories':len({key(w,'initial_record') for w in worlds}),'calibrated_probabilities':probabilities,'constant':constant,'new_Player_calls':0,'input_sha256':r['input_sha256'],'seconds':time.perf_counter()-tick};L.write_record(d/'preparation.json',meta);print(meta,flush=True)


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--calibration',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True);a=p.parse_args();prepare(a.output,a.calibration,a.proposal)
if __name__=='__main__':main()
