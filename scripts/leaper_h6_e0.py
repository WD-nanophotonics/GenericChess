"""Frozen initial-mu rule-property E0 handoff; no oracle, solver or Player."""
import argparse,itertools,random,time,json
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
from collections import Counter
from scripts import leaper_design as L
from scripts.leaper_parity_scope import adjacent,xy,digest
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.core.semantic_executor import semantic_engine_for
from tools.local_agent.common import write_json
from tools.local_agent import session

def now():return datetime.now(timezone.utc).isoformat()
def graph(mask):
    offsets=L.offsets(mask);adj={i:{3*(i//3+dy)+i%3+dx for dx,dy in offsets if 0<=i%3+dx<3 and 0<=i//3+dy<3} for i in range(9)}
    todo=set(adj);components=[]
    while todo:
        seen={min(todo)};queue=list(seen)
        while queue:
            for j in adj[queue.pop()]-seen:seen.add(j);queue.append(j)
        components.append(len(seen));todo-=seen
    return {'components':sorted(components),'mean_degree':sum(map(len,adj.values()))/9}

def board(spec):
    k,a,v,b=spec;cells=[None]*9
    for i,o,t in ((k,0,'K'),(a,0,'A'),(v,1,'K'),(b,1,'B')):cells[i]=L.Piece(o,t,t)
    return tuple(tuple(cells[3*j:3*j+3]) for j in range(3))

def base_rule(a,b,spec):
    r=L.definition(a,b)
    return replace(r,board_size=3,initial_position=board(spec),drop_allowed={t:((False,)*9,)*2 for t in ('A','B')},max_ply=6,repetition_limit=2)

def safe_geometry(spec,a,b):
    k,aa,v,bb=spec;ks=xy(k,3);vs=xy(v,3);asq=xy(aa,3);bsq=xy(bb,3)
    return not adjacent(ks,vs) and (vs[0]-asq[0],vs[1]-asq[1]) not in L.offsets(a) and (bsq[0]-ks[0],bsq[1]-ks[1]) not in L.offsets(b)

def run(output,plan_path):
    assert not output.exists();output.mkdir();start=now();tick=time.perf_counter();plan=L.load(plan_path)
    # Discovery of the EXISTING compiler admission contract precedes this run:
    # initial stalemate is a setup refusal, not a secret negative outcome filter.
    plan={**plan,'execution_started_at':start,'mu_contract_correction':'Uniform over compiler-admitted fresh layouts. Allboth-King-safe placements are examined; initial no-legal-action failures remain explicit excludedsetuprows, not outcome-selected replacements. Compiler forbids a duplicated default board among alternate setups: default uses None key; others stablekeys. Changes are made before anynewfamilyCore query, preserving all12metadata selections.','source_sha256':L.sha(Path(__file__))}
    write_json(output/'plan-before-inputs.json',plan)
    pairs=random.Random(202610231430).sample([(a,b) for a in range(1,32) for b in range(a,32) if (a,b) not in ((1,1),(1,2),(2,2),(3,3))],12)
    write_json(output/'selected-metadata.json',{'pairs':pairs,'calibration':pairs[:6],'reserved':pairs[6:],'oracle_access':'No NEW family truth read; priorfoundationonefamily truth and old31maskKAKlocalgeometryalreadyexposed.'})
    families=[];rows=[];admission=[];first128=[];preflight_tick=None;totalraw=0
    for index,(a,b) in enumerate(pairs):
        if session.stopped() or time.perf_counter()-tick>=600:break
        candidates=[spec for spec in itertools.permutations(range(9),4) if safe_geometry(spec,a,b)]
        family={'family':index,'masks':[a,b],'split':'calibration' if index<6 else 'reserved_validation','raw_labelled_placements':3024,'both_King_safe_candidates':len(candidates),'geometry':[graph(a),graph(b)]};totalraw+=3024
        c0=None;approved=[];refused=[]
        for spec in candidates:
            try:
                if c0 is None:c0=L.compile_rule(base_rule(a,b,spec))
                else:
                    pos=replace(c0.initial_position,board=tuple(x for row in board(spec) for x in row));engine=semantic_engine_for(c0)
                    assert not engine.in_check(pos,0) and not engine.in_check(pos,1)
                    if not engine.has_legal_action(pos):raise ValueError('INITIAL_NO_LEGAL_ACTION')
                approved.append(spec)
            except Exception as exc:refused.append({'placement':spec,'error':repr(exc)})
        family['refused_initial_setups']=refused;family['admitted_initial_layouts']=len(approved)
        if not approved:
            family.update(status='MU_UNAVAILABLE',rule=None);families.append(family);write_json(output/'family-admission.json',{'families':families});continue
        options=tuple(RuleInitialSetupOption('s-'+'-'.join(map(str,z)),board(z)) for z in approved[1:]);rr=replace(base_rule(a,b,approved[0]),initial_setup_options=options)
        raw=L.ruleset_to_dict(rr,include_metadata=True);fp=L.compute_fingerprint(rr)
        family.update(status='FEATURES_PENDING',rule=raw,fingerprint=fp,mu_id='GC-H6-INIT-UNIFORM-'+fp)
        families.append(family);write_json(output/'family-admission.json',{'families':families})
        # The actual family and E0formulas are saved BEFORE newfamily Corefeatures.
        write_json(output/('family-'+str(index)+'-frozen.json'),family)
        c=L.compile_rule(rr);geom_coop=.75 if all(z['components']==[9] for z in family['geometry']) else .25;geom_fork=.75 if sum(z['mean_degree'] for z in family['geometry'])/2>=3 else .25
        for root_index,spec in enumerate(approved):
            if session.stopped() or time.perf_counter()-tick>=600:break
            if preflight_tick is None:preflight_tick=time.perf_counter()
            key=None if root_index==0 else 's-'+'-'.join(map(str,spec));ss=L.GameSession(c,initial_setup_key=key);rec=L.record_value(ss.to_record());state=L.record_value(ss.state)
            children=L.legal_successors(ss.state,c)
            observed={'family':index,'setup_key':key,'placement':spec,'full_record':rec,'full_state':state,'actions':[{'action':L.record_value(ac),'terminal':L.record_value(ch.terminal_status)} for ac,ch in children]}
            write_json(output/'latest-feature-return.json',observed)
            terminal=ss.state.terminal_status.is_terminal;immediate=any(ch.terminal_status.winner is not None for _,ch in children)
            known=int(ss.result.winner is not None) if terminal else None
            predictions={'geometric_cooperative':known if terminal else geom_coop,'oneply_augmented_cooperative':known if terminal else 1.0 if immediate else geom_coop,'geometric_wdl_fork':0 if terminal else geom_fork,'uninformative_cooperative':known if terminal else .5,'uninformative_wdl_fork':0 if terminal else .5,'same_board_roster_cooperative':known if terminal else 1.0,'same_board_roster_wdl_fork':0 if terminal else 35/36}
            rows.append({**observed,'fingerprint':fp,'mu_id':family['mu_id'],'split':family['split'],'state_sha256':L.state_sha(ss.state),'record_sha256':digest(rec),'feature_oneply_scoring_child':immediate,'predictions':predictions,'cooperative_truth':'UNKNOWN_PENDING_AUX','wdl_fork_truth':'UNKNOWN_PENDING_AUX'})
            first128.append(1)
            if len(first128)==128:
                elapsed=time.perf_counter()-preflight_tick;max_est=elapsed*(12*1344/128)*1.5
                write_json(output/'actual-feature-cost-preflight.json',{'actual_first_roots':128,'actual_seconds':elapsed,'conservative_candidate_roots_upper_bound':16128,'forecast_seconds':max_est,'warning':'Sampledmeannotguarantee,600s capunchanged. Initialgeometryadmission/compilation costs separatelyinwholeproducerclock.'})
                if max_est>=7200:raise RuntimeError('expected>=120min;doNOTstartadditionalfeatures')
        family['feature_rows_observed']=sum(x['family']==index for x in rows);family['status']='CLOSED' if family['feature_rows_observed']==len(approved) else 'INCOMPLETE'
        write_json(output/'feature-rows.json',{'rows':rows});write_json(output/'family-admission.json',{'families':families});print({'family':index,'masks':[a,b],'admitted':len(approved),'refused':len(refused),'features':family['feature_rows_observed']},flush=True)
    final={'status':'CLOSED' if len(families)==12 and all(f['status'] in ('CLOSED','MU_UNAVAILABLE') for f in families) else 'INCOMPLETE','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'families':families,'rows':rows,'source_sha256':L.sha(Path(__file__)),'plan_sha256':L.sha(output/'plan-before-inputs.json'),'new_Player_calls':0,'new_solver_calls':0,'truth_access':'Only permitted1plyfeatures; no H6oracle/minimax/forksolver, no oldAUXmatchinglabelsimported','logical_targets':'Cooperative scoringreachability under actualH6/fullhistory and WDL-fork; metadata/nolegalsetupfailures remain; no policydecisivenessequation, no sampled-root IIDclaim.'};write_json(output/'results.json',final);print({'status':final['status'],'families':len(families),'roots':len(rows),'seconds':final['seconds']});return final

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args();run(a.output,a.plan)
