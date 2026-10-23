"""Read fixed initial-mu E0 outputs through actual public Core; no H6 solve."""
import argparse,json,time
from pathlib import Path
from fractions import Fraction as F
from collections import Counter
from datetime import datetime,timezone
from scripts import leaper_design as L
from scripts.leaper_h6_e0 import graph,safe_geometry
from scripts.leaper_parity_scope import digest
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.core.actions import action_to_dict
from tools.local_agent.common import write_json
from tools.local_agent import session

def qualify(source,analysis,output):
    p=L.load(source);z=L.load(analysis);assert p['status']=='CLOSED' and z['source_sha256']==L.sha(source)
    start=datetime.now(timezone.utc).isoformat();tick=time.perf_counter();roots=edges=positives=negative=0;fps=set();failure=None;counts=Counter();amap={(r['family'],r['setup_key']):r for r in z['rows']};wmap={(r['family'],r['source_state_sha256']):r for r in z['oneply_positive_witnesses']}
    # Verify every certificatepair and the COMPLETEdomain, independently of producer.
    expected={(v,k) for v in range(9) for k in range(9) if not __import__('scripts.leaper_parity_scope',fromlist=['adjacent']).adjacent((v%3,v//3),(k%3,k//3))}
    actual=set()
    for item in z['colour_geometry_certificate']:
        v,k=item['victim'],item['other_royal'];x,y=item['escape'];assert 0<=x<3 and 0<=y<3 and abs(x-v%3)+abs(y-v//3)==1 and max(abs(x-k%3),abs(y-k//3))>1
        assert (x+y)%2!=item['ordinary_global_colour']==(v%3+v//3)%2;actual.add((v,k))
    assert actual==expected and len(actual)==len(z['colour_geometry_certificate'])
    for family in p['families']:
        rr=[r for r in p['rows'] if r['family']==family['family']]
        if family['status']=='MU_UNAVAILABLE':assert not rr and family['both_King_safe_candidates']==0;continue
        rule=L.ruleset_from_dict(family['rule']);assert rule.max_ply==6 and rule.repetition_limit==2 and rule.capture_disposition=='remove_from_game'
        c=L.compile_rule(rule);assert L.compute_fingerprint(rule)==family['fingerprint'];fps.add(family['fingerprint']);keys=[r['setup_key'] for r in rr];assert len(set(keys))==len(keys)==family['admitted_initial_layouts']
        assert set(keys)=={None,*c.support.initial_setup_options}
        for r in rr:
            if session.stopped() or time.perf_counter()-tick>=600:raise RuntimeError('600s independentE0reader cap/scopedstop')
            ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(r['full_record'])));assert ss.state.ply_count==0 and L.record_value(ss.state)==r['full_state'] and L.state_sha(ss.state)==r['state_sha256'] and digest(r['full_record'])==r['record_sha256'];assert ss.to_record().initial_setup_key==r['setup_key']
            expected_pieces=[(ix,o,t) for ix,o,t in [(r['placement'][0],0,'K'),(r['placement'][1],0,'A'),(r['placement'][2],1,'K'),(r['placement'][3],1,'B')]]
            assert sorted((ix,pc.owner,pc.current_type_id) for ix,pc in enumerate(ss.state.position.board) if pc)==sorted(expected_pieces)
            actions=legal_actions(ss.state,c);children=[(a,apply_action(ss.state,a,c)) for a in actions]
            actual=[{'action':L.record_value(a),'terminal':L.record_value(ch.terminal_status)} for a,ch in children];assert actual==r['actions']
            edges+=len(actions);roots+=1;positive=any(ch.terminal_status.winner is not None for _,ch in children);assert positive==r['feature_oneply_scoring_child'];positives+=int(positive)
            g=family['geometry'];assert g==[graph(m) for m in family['masks']]
            pp=r['predictions'];expected_geom=.75 if all(x['components']==[9] for x in g) else .25;assert pp['geometric_cooperative']==expected_geom and pp['oneply_augmented_cooperative']==(1.0 if positive else expected_geom)
            assert pp['uninformative_cooperative']==.5 and pp['same_board_roster_cooperative']==1
            if positive:
                witness=wmap[family['family'],r['state_sha256']];won=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(witness['complete_record'])));assert won.result.winner is not None and len(won.to_record().actions)==1 and L.state_sha(won.state)==witness['final_state_sha256']
            ar=amap[family['family'],r['setup_key']];assert ar['literal_oneply_positive']==positive;negative+=int(ar['proposed_colour_negative'])
            if ar['proposed_colour_negative']:
                from scripts.leaper_h6_e0_bounds import colour_condition
                assert colour_condition(family,r) and not positive
        counts['families']+=1
        write_json(output.with_suffix('.progress.json'),{'started_at':start,'at':datetime.now(timezone.utc).isoformat(),'families':counts['families'],'roots':roots,'edges':edges})
    # Independent finite count enumeration of each family's RATE loss contrast.
    # This is a relaxed feasible-label interval; semantic correlations can only
    # shrink it. No IID/independent-game assumption is made.
    for label,views in z['rule_prevalence_contrasts'].items():
        for key,item in views.items():
            cond=key=='with_proposed_colour_binding'
            for row in item['family_bounds']:
                f=row['family'];rr=[r for r in z['rows'] if r['family']==f];n=len(rr);known=sum(r['literal_oneply_positive'] for r in rr);neg=sum(r['proposed_colour_negative'] for r in rr) if cond else 0;p0=F(row['model_rate_prediction']);q0=F(row['baseline_rate_prediction'])
                values=[(p0-F(k,n))**2-(q0-F(k,n))**2 for k in range(known,n-neg+1)]
                assert [str(min(values)),str(max(values))]==row['contrast_bounds']
    result={'status':'PASS','started_at':start,'ended_at':datetime.now(timezone.utc).isoformat(),'seconds':time.perf_counter()-tick,'actual_families':counts['families'],'unavailable_families':1,'roots':roots,'public_Core_applied_edges':edges,'literal_oneply_positive_witnesses':positives,'proposed_colour_negative':negative,'source_sha256':L.sha(source),'analysis_sha256':L.sha(analysis),'source_code_sha256':L.sha(Path(__file__)),'scope':'publiclegal_actions/apply_action andstrictGameRecordreader; sharedCore not independent H6oracle. Exactfinitealgebra bounds overrelaxedlabelsets; no IID/oracletruth/calibrationclaim; no Player/solver.'};write_json(output,result);print(result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();qualify(a.source,a.analysis,a.output)
