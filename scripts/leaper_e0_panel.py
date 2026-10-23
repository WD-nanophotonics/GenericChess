"""Small three-piece Leaper E0 panel, frozen without any oracle labels.

Only rule/input/feature preparation; use the existing bounded Leaper producer
for new policy observations. Geometry is not structural game truth.
"""
from __future__ import annotations
import argparse,copy,json,random,time
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from scripts import leaper_design as L

MASKS=(1,2,4,8,16,3,5,6,9,10,12,31)
CALIBRATION=(1,2,4,8,16,3)


def rule(mask,layout):
    base=L.definition(mask,mask);types=base.piece_types[:2];board=[None]*16
    for ix,owner,tid in (((0,0,'K'),(1,0,'A'),(15,1,'K')) if layout==0 else ((3,0,'K'),(7,0,'A'),(12,1,'K'))):board[ix]=L.Piece(owner,tid,tid)
    return replace(base,piece_types=types,initial_position=tuple(tuple(board[4*r:4*r+4]) for r in range(4)),drop_allowed={'A':((False,)*16,)*2},max_ply=64)


def prepare(d):
    assert not d.exists();d.mkdir();tick=time.perf_counter()
    plan={'frozen_at':datetime.now(timezone.utc).isoformat(),'question':'Do empty-board motion plus immediate-win E0 features predict finite Random/FLOOR/AB policy decisiveness on a fixed small3piecepanel, while keeping structural/gameWDL truth UNKNOWN?','selection':'ALL12fixed masks1,2,4,8,16,3,5,6,9,10,12,31 on4x4K+A versusK, twofixedlayouts, initial and independently seeded uniform4 prefix each. No solver/oracle/outcome selection. Allalreadyterminalprefixes retained. Family masks exposed in earlier6piece work; NEWroster/clock/fullhistories, not unknown-code generalization.','split':{'calibration_masks':list(CALIBRATION),'reserved_validation_masks':[m for m in MASKS if m not in CALIBRATION],'unit':'movementmask family, BOTHlayouts/prefixes staytogether; no fitting thisround; frozen for possibleE1. Not IID/populationcalibration.'},'prediction_rule':'For decisive terminal event in eachregisteredpolicygame: p=.75 when Aempty-board graphconnectedANDmeanDegree>=3, else.25; ifroot isalreadyterminal useexactknownterminalindicator. Baseline.5 forongoing andknownterminalindicator otherwise. SAMEpredacrosspolicies/roles to expose missingconditionalinformation. FreezebeforeanyPlayer orpolicyoutcomes.','structural_targets':'Cooperativewinningpath/structuraldeadzone/fullhistoryminimax/actionWDL remain UNKNOWN pending independentlysuppliedAUXlabels; emptygraphcomponents are features only. Observeddecisive trajectories later are one-sided cooperative witnesses, not negatives fromdraws.','count':'48contexts*5pairs*2roles*4seedrepeats=1920physicaldeployments,384perpair,32perrule/pair. Not1920independentcontexts.','cost':'NEWgeometry/rootcost preflight beforefitness, no oracle. Expected producer1800seconds, cooperativeproducer cap2700seconds includingprep/preflight, total logicalcap3300 incl600necessaryqualification/analysis reserve=55min<120min. Conservative sampledmax retained; empirical oldpolicy clocks onlyplanning notcoverageguarantee. Stopallslotsorcap, no refill/thresholdchange.'}
    L.write_record(d/'plan-before-inputs.json',plan);worlds=[];preds=[]
    for mask in MASKS:
        geom=L.graph(mask);positive=geom['components']==[16] and geom['mean_empty_board_degree']>=3
        for layout in (0,1):
            rr=rule(mask,layout);raw=L.ruleset_to_dict(rr,include_metadata=True);c=L.compile_rule(rr)
            for prefix in (0,4):
                s=L.GameSession(c);seed=202610231220+10000*mask+100*layout+prefix;rng=random.Random(seed)
                for _ in range(prefix):
                    if s.state.terminal_status.is_terminal:break
                    aa=s.legal_actions();s.submit(aa[rng.randrange(len(aa))])
                w={'world':len(worlds),'code_world':MASKS.index(mask),'masks':[mask],'rule':raw,'fingerprint':L.compute_fingerprint(rr),'initial_record':L.record_value(s.to_record()),'initial_state':L.record_value(s.state),'initial_terminal':L.record_value(s.result),'initial_legal_count':len(s.legal_actions()),'initial_oneply_win_witness':False if s.state.terminal_status.is_terminal else any(ch.terminal_status.is_terminal and ch.terminal_status.winner==s.state.position.side_to_move for _,ch in L.legal_successors(s.state,c)),'placement_index':layout,'prefix_requested':prefix,'prefix_seed':seed,'status':'ready','floor_type_map':{'K':'K','A':'A'},'geometry':geom,'rule_split':'calibration' if mask in CALIBRATION else 'reserved_validation'}
                check=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['initial_record'])));assert L.record_value(check.state)==w['initial_state'];worlds.append(w)
                terminal=s.state.terminal_status.is_terminal;known=int(s.result.winner is not None) if terminal else None
                preds.append({'world':w['world'],'fingerprint':w['fingerprint'],'rule_split':w['rule_split'],'positive_feature':positive,'terminal_at_start':terminal,'probability_decisive_policy_terminal':known if terminal else .75 if positive else .25,'zero_information_baseline_probability':known if terminal else .5,'structural_deadzone':'UNKNOWN','minimax_WDL':'UNKNOWN','action_WDL':'UNKNOWN','cooperative_decisive_reachability':'UNKNOWN','feature_source':'onlyfrozenrule/fullinitialhistory/emptygraph,0Playercalls/0oracle/0policyfitness'})
    L.write_record(d/'inputs.json',{'scope':'4x4K+AversusK remove/maxply64/repetition4/plainLeaps, no promotion/drop. Fullhistory retained; longtermdomain unchanged.','worlds':worlds})
    r={'frozen_at':datetime.now(timezone.utc).isoformat(),'question':plan['question'],'selection':plan['selection'],'pairs':{'AB128_RNG':['AB128','RNG'],'AB512_RNG':['AB512','RNG'],'AB2048_RNG':['AB2048','RNG'],'FLOOR_RNG':['FLOOR','RNG'],'RNG_RNG':['RNG','RNG']},'roles':[0,1],'repetitions':4,'first_repeat':0,'seed':202610231223,'nodes':512,'caller_plies':64,'rule_max_ply':64,'repetition_limit':4,'q':0,'forced_check_depth':8,'TT':'freshactor/game retainedwithingame','disk_cache':False,'floor_coupling':L.FLOOR_COUPLING,'search_variants':{f'AB{n}':{'base':'AB','nodes':n,'depth':64} for n in (128,512,2048)},'preflight_policies':['AB128','AB512','AB2048'],'planned_games':1920,'source_sha256':L.sha(Path(L.__file__)),'preparer_sha256':L.sha(Path(__file__)),'input_sha256':L.sha(d/'inputs.json'),'expected_seconds':1800,'whole_cap_seconds':2700,'logical_cap_seconds':3300,'validation_analysis_reserve_seconds':600,'empirical_loop_forecast_seconds':1600,'cost_basis':plan['cost'],'criterion':'Reportexactfinitepolicydecisiveness frequencies andsignedutility byrule/role/layout/prefix/controller, UNKNOWNbounds andcost. FrozenE0vs.5baselineBrier/classification are descriptions of thissmallnonIIDpanel, not calibratedprobabilities/populationhit rates. Cooperativepositivewitnessfromactualdecisivepath; neverequate alldraws todeadzone. No default/inversepromotion orAUXsolver.', 'stop':'1920slotsor2700producerseconds inclactualprep/preflight; nonewcap/reset/refill. Allnotstarted/censored/failedUNKNOWN preserved.'}
    roots=[{'world':w['world'],'rule':w['rule'],'record':w['initial_record'],'phase':'initial' if w['prefix_requested']==0 else 'uniform4'} for w in worlds if w['initial_terminal']['status']=='ongoing'];L.write_record(d/'preflight-inputs.json',{'roots':roots});r['preparation_seconds']=time.perf_counter()-tick;L.write_record(d/'registration.json',r);L.write_record(d/'e0-predictions.json',{'frozen_at':datetime.now(timezone.utc).isoformat(),'input_sha256':r['input_sha256'],'registration_sha256':L.sha(d/'registration.json'),'prediction_rule':plan['prediction_rule'],'split':plan['split'],'rows':preds,'Player_calls':0,'oracle_reads':0,'fitness':0});print({'worlds':len(worlds),'terminalprefixes':sum(w['initial_terminal']['status']!='ongoing' for w in worlds),'slots':1920,'prep_seconds':r['preparation_seconds'],'input_sha256':r['input_sha256'],'predictions_sha256':L.sha(d/'e0-predictions.json')},flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a.output)
if __name__=='__main__':main()
