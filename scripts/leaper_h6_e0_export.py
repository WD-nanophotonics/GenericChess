"""Export frozen E0 inputs to the existing strict AUX forecast formats.

Reuses retained feature returns, not new Core/Player/oracle queries. The source
SHA is the actually executed COMMITTED exporter revision; original feature-run
and frozen-code hashes remain separate in the provenance record.
"""
import argparse,json,re,subprocess,time
from pathlib import Path
from fractions import Fraction as F
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.leaper_parity_scope import digest
from tools.local_agent.common import write_json

def export(source,analysis,output,execution_sha):
    if re.fullmatch('[0-9a-f]{40}',execution_sha) is None:raise ValueError('full committed execution SHA required')
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head==execution_sha
    committed=subprocess.check_output(['git','show',head+':scripts/leaper_h6_e0_export.py'])
    assert committed.replace(b'\r\n',b'\n')==Path(__file__).read_bytes().replace(b'\r\n',b'\n')
    start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter();p=L.load(source);a=L.load(analysis);assert a['source_sha256']==L.sha(source)
    aliases=[];hsets={};rsets={};files=[];models=list(a['rows'][0]['predictions'])
    for model in models:
        posthoc=model.startswith('v2_');is_fork=model.endswith('wdl_fork');property_name='wdl_fork' if is_fork else 'cooperative_decisive'
        freeze={'forecast_id':'GC-H6-20261023-'+model,'information_set':'CompleteRuleSet/freshinitialGameRecord/geometry; '+('retainedactualoneplyCorechildren and separatelyversioned exposedcolourproof' if posthoc else 'retainedactualoneplyCorechildren' if model=='oneply_augmented_cooperative' else 'exposedM/MH6sameboard-roster prior' if model.startswith('same_board') else 'no newfamilyoracles; frozenmetadata/constant formula'),'frozen_at':p['started_at'],'truth_access':'No independentH6/forkoraclefornewfamilies. Literaloneplypositiveevidence IS included in enhancedmethod. Sourceprimitives/olderdataexposed. V2 is POSTHOC analyticdevelopment, notblinding/test-rescue.' if posthoc else 'Formulasfrozenbeforethesefeaturequeries; enhancedmethodusesliteraloneplypositiveevidence, notfullH6truth. OlderM/Mtruthknown forstrongerconstant; movementprimitivesexposedelsewhere.'}
        if posthoc:freeze['frozen_at']=a['started_at'];freeze['timestamp_note']='Exact exposed-v2 analysis execution timestamp, AFTER featuredata; not an assertion of pre-query freezing.'
        common={'freeze':freeze,'probability_semantics':'cooperative_decisive = ANYscoringcontinuation before actual6ply/repeat2terminal; wdl_fork=existchildwithdifferentminimaxWDL, notfirstactiondisagreement','source_binding':'source_sha isthisCOMMITTEDexportexecution; featureproducerexecutedsourceSHA256 andCorebaseline3eb9998822c281834e37443456a36e664e0c1493 remainexplicitlyseparate','feature_source_packet_sha256':L.sha(source),'feature_producer_source_sha256':p['source_sha256'],'cost_units':'Numericcostdicts countactualADDITIONALfeatureCore rootreturns/childrecords. Inputmuadmission/compilation shared; theirunseparated wholeproducerwall13.910812s is reported ONCE below, neverzero-runtime orsumcopiedtime. No incrementalwall comparison.','shared_whole_feature_producer_seconds':p['seconds'],'new_Core_queries_during_export':0,'new_Player_queries':0,'new_solver_queries':0}
        h={'format':'leaper-explorer-predictions-v1',**common,'predictions':[]};r={'format':'leaper-rule-prevalence-predictions-v1',**common,'predictions':[]}
        for f in p['families']:
            if f['status']!='CLOSED':continue
            sr=[x for x in p['rows'] if x['family']==f['family']];ar=[x for x in a['rows'] if x['family']==f['family']];ids=sorted(x['state_sha256'] for x in sr);assert len(set(ids))==len(ids)
            mu_id=digest(ids);alias={'fingerprint':f['fingerprint'],'original_mu_name':f['mu_id'],'support_mu_id':mu_id,'roots':len(ids),'state_ids':ids,'law':'uniformexactlistedcompletefreshhistories; namesonlyaliaschange, no row/weight/predictionchange'}
            if model==models[0]:aliases.append(alias)
            use_core=model=='oneply_augmented_cooperative' or posthoc
            for row in ar:
                original=next(x for x in sr if x['state_sha256']==row['state_sha256']);cost={'Core_feature_root_returns':int(use_core),'Core_feature_children':len(original['actions']) if use_core else 0,'colour_predicate_checks':int(posthoc)}
                h['predictions'].append({'id':row['state_sha256'],'fingerprint':f['fingerprint'],'mu_id':mu_id,'property':property_name,'probability':row['predictions'][model],'source_sha':execution_sha,'cost':cost})
            probability=sum(F(str(x['predictions'][model])) for x in ar)/len(ar)
            r['predictions'].append({'fingerprint':f['fingerprint'],'mu_id':mu_id,'property':property_name,'probability':float(probability),'exact_probability':str(probability),'source_sha':execution_sha,'cost':{'Core_feature_root_returns':len(sr) if use_core else 0,'Core_feature_children':sum(len(x['actions']) for x in sr) if use_core else 0,'colour_predicate_checks':len(sr) if posthoc else 0},'score_target':'Familyprevalencerate; meanpredictionbroadcastconstant forbinaryBrier. DoNOTreuseoriginalconditional-rootBrier asrateMSE.'})
        hsets[model]=h;rsets[model]=r
    result={'schema':'genericchess.H6.E0.strict_handoff.v1','execution_sha':execution_sha,'started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),'export_seconds':time.perf_counter()-tick,'mu_aliases':aliases,'history_forecasts':hsets,'rule_prevalence_forecasts':rsets,'unavailable_families':[f for f in p['families'] if f['status']=='MU_UNAVAILABLE'],'status':'PREDICTIONS_READY_INDEPENDENT_TRUTH_NOT_EXECUTED','scope':'Frozenv1vsseparateexposedv2; same3616historysupport/11rules,missing12thnotimputed; BOTHforecasttargets/formats explicit. No receiving/reading/scoringbyAUX claimed.'};write_json(output,result);print({'methods':len(models),'histories':len(aliases) and sum(x['roots'] for x in aliases),'families':len(aliases),'export_seconds':result['export_seconds']});return result

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--execution-sha',required=True);a=p.parse_args();export(a.source,a.analysis,a.output,a.execution_sha)
