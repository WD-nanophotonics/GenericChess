"""One-ply counterexample probes for a scoped E0 mating-support prediction.

No graph closure, minimax solver, Player calls or natural-input selection. New
safe setups are explicit controls; no labels transfer to other histories.
"""
import argparse,json,time
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_e0_panel import MASKS,rule


def probe(d):
    assert not d.exists();d.mkdir();tick=time.perf_counter()
    forecast={str(m):{'offset_parities':sorted({(dx+dy)%2 for dx,dy in L.offsets(m)}),'E0_no_scoring_terminal_prediction':len({(dx+dy)%2 for dx,dy in L.offsets(m)})==1,'independent_truth':'NOT_ASSIGNED','qualifier':'analytic candidate for4x4 K+AversusbareK only; mixedparity UNKNOWN, not positivebydefault'} for m in MASKS}
    plan={'frozen_at':datetime.now(timezone.utc).isoformat(),'question':'Does a singleparity ordinary move set supply a scoped cheap mating-obstruction feature that empty-board connectivity misses?','changed_premise':'E0/E1root-policy feature failed practicalscorecriterion; newrule-explorer priority needs rule-derived properties and explicittruthscope. Same-color orallcolor-flipping moves both leave two orthogonal escapes unguarded bythecheckingordinarypiece.','forecast':forecast,'claim_scope':'Square4x4, exactlytwo adjacent8royalAnchors andoneplainLeaper A, remove/nohand/drop/promotion/aux, anchorcapturesforbidden, checkmateonlyscoringterminal;stalemate/repetition/clockdraw. Extraactors,thinboards,stalemateloss/captureAnchor andothergoals excluded. No genericpriceorallgenerateddomainclaim.','reasoning':'Choose two perpendicular orthogonal neighboursu,v ofvictimKing. Ifchecker movesalloneparity, its attacksfromcheckersquare hitonlyvictimsquarecolor, neveru/v. AttackerKing cannot coverbothu/v withoutbeing adjacenttovictimKing, illegal. Ifthecheckeroccupiesu, protectingitwhilecoveringv hasthesameimpossibleKingintersection;victimcancaptureit or escape. BareKing cannotlegallycheckanothertoyalKing. Thisisawrittenpropositionforreview, not an independentcertificate or an exportedWDLlabel.','probe':'ALL12metadata masks andTWOpredeclaredsetupcontrols. SharedCoreenumeratesONElegalplyonly;winningchildren savedwithcompletelegalGameRecords, failures/unadmittedsetupskept. No search/refill. Noabsence-of-oneply-win promoted toclosure.','exposure':'PublishedAUXmating/deadzoneinventoryalreadyread. Panelknownpositivepathsinclude3and10;thisisnot ablindcalibrationclaim. Fresh5setupcontrol chosenbyanalyticalconstruction, not μsample. Forecastsameparityspatialclaim predeclaredBEFOREthesequeries.','budget':'24rootsetups,allCore-legaloneplychildren or60seconds total;expected<5seconds.0Player/solvercalls.'}
    L.write_record(d/'plan-before-probes.json',plan);inputs=[]
    for mask in MASKS:
        for name,k,a,victim in [('near',(2,1),(1,2),(0,0)),('far',(2,2),(3,3),(0,0))]:
            r=rule(mask,0);board=[None]*16
            for sq,owner,t in [(k,0,'K'),(a,0,'A'),(victim,1,'K')]:board[4*sq[1]+sq[0]]=L.Piece(owner,t,t)
            r=replace(r,initial_position=tuple(tuple(board[4*i:4*i+4]) for i in range(4)));inputs.append({'mask':mask,'setup':name,'rule':L.ruleset_to_dict(r,include_metadata=True),'fingerprint':L.compute_fingerprint(r)})
    L.write_record(d/'inputs.json',{'rows':inputs});rows=[]
    for w in inputs:
        if time.perf_counter()-tick>=60:break
        z={**w,'status':'setup_pending'};rows.append(z);L.write_record(d/'results.json',{'status':'RUNNING','rows':rows})
        try:
            c=L.compile_rule(L.ruleset_from_dict(w['rule']));s=L.GameSession(c);z.update(status='ready',initial_record=L.record_value(s.to_record()),initial_state=L.record_value(s.state));children=list(L.legal_successors(s.state,c));wins=[]
            for action,ch in children:
                if ch.terminal_status.is_terminal and ch.terminal_status.winner==0:
                    t=L.GameSession.replay(c,s.to_record());t.submit(action);assert L.record_value(t.state)==L.record_value(ch)
                    wins.append({'action':L.record_value(action),'complete_record':L.record_value(t.to_record()),'final_state':L.record_value(t.state),'terminal':L.record_value(t.result)})
            z.update(status='finished',legal_children=len(children),scoring_children=wins,contradicts_singleparity_forecast=bool(wins) and forecast[str(w['mask'])]['E0_no_scoring_terminal_prediction'])
        except Exception as e:z.update(status='setup_failed',error=repr(e))
        L.write_record(d/'results.json',{'status':'RUNNING','rows':rows})
    out={'status':'CLOSED','rows':rows,'unattempted':len(inputs)-len(rows),'seconds':time.perf_counter()-tick,'new_Player_calls':0,'new_solver_calls':0,'ordinary_game_deployments':0,'oneply_control_setups':len(rows),'core_legal_child_checks':sum(x.get('legal_children',0) for x in rows),'positive_paths':sum(len(x.get('scoring_children',[])) for x in rows),'singleparity_falsifications':sum(x.get('contradicts_singleparity_forecast',False) for x in rows),'scope':'Actualoneplypaths only. Analyticobstruction remains E0proposalforindependentreview, not blindtruthcalibration/wholeclosure. DifferentinitialRuleSetfingerprints from48panelinputs; nevertransferpositivepathreachability tothatμ.'};L.write_record(d/'results.json',out);print({k:out[k] for k in ('status','unattempted','seconds','oneply_control_setups','core_legal_child_checks','positive_paths','singleparity_falsifications')});print([{'mask':x['mask'],'setup':x['setup'],'status':x['status'],'winning_children':len(x.get('scoring_children',[]))} for x in rows])


def main():
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();probe(a.output)
if __name__=='__main__':main()
