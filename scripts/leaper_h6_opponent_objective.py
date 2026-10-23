"""New objective check on old fixed A/B histories, with zero new sampling.

Maximizing expected terminal W-L against IID Uniform defense is different
from maximizing the worst-case WDL. The full H6/repeat2 state class is the
already qualified (Position,remaining,visited-set) constructor, not a generic
history quotient or an experiential training-start selector.
"""
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_h6_initial_truth import admit
from scripts.leaper_h6_headroom import evaluate
from scripts.leaper_cooperative_certificate import decode_position
from scripts.leaper_microgames import role_stop_requested


def analyze(directory,old_policy,output,*,seconds=180):
    tick=time.perf_counter();directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz')
    past=load(old_policy)
    if past['plan']['inputs_digest']!=digest(inputs)or past['plan']['truth_digest']!=digest(truth)or past['plan']['pairs_digest']!=digest(adj):raise ValueError('old nominal policy input differs')
    source={r['id']:r for r in truth['roots']};result=[]
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('H6_OBJECTIVE_CAP_UNKNOWN_NO_REFILL')
    for pair in adj['pairs']:
      for tag,key in(('left_family','left_id'),('right_family','right_id')):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);rows=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,rows[0]);d=load(directory/f"domain{family['family']}.json.gz")
        old=next(r for r in load(directory/'summary.json')['families']if r['family']==family['family'])
        if digest(d)!=old['domain_digest']:raise ValueError('closed Core domain differs')
        positions=[decode_position(p,c.initial_position)for p in d['positions']];sides=[p.side_to_move for p in positions];edges=d['edges'];terms={int(i):v for i,v in d['terminals'].items()}
        features=[(sum(p is not None and(p.owner,p.current_type_id)==(0,'A')for p in pos.board),-sum(p is not None and(p.owner,p.current_type_id)==(1,'B')for p in pos.board))for pos in positions]
        ended,exact,_,_,_=evaluate(edges,terms,sides,features,guard);contexts=set()
        @lru_cache(None)
        def chance(i,h,prior):
            contexts.add((i,h,prior))
            if len(contexts)%2048==0:guard()
            if ended(i,h,prior):return F(exact(i,h,prior))
            pp=prior|1<<i;values=[chance(j,h-1,pp)for j in edges[i]]
            return max(values)if sides[i]==0 else sum(values)/len(values)
        root_rows=[]
        for rr in pair['rows']:
            sr=source[rr[key]];i=sr['root_index'];value=chance(i,6,0);pp=1<<i
            cv=[chance(j,5,pp)for j in edges[i]];wv=[exact(j,5,pp)for j in edges[i]]
            best=max(cv);chosen=[k for k,v in enumerate(cv)if v==best];robust=max(wv)
            root_rows.append(dict(id=sr['id'],oracle_uniform_U=str(value),minimax_WDL=robust,chance_optimal_action_indices=chosen,chance_optimal_worstcase_values=[wv[k]for k in chosen],some_chance_optimum_worse_minimax=any(wv[k]<robust for k in chosen),all_chance_optima_worse_minimax=all(wv[k]<robust for k in chosen)))
        census=Counter()
        for i,h,prior in contexts:
            if ended(i,h,prior)or sides[i]!=0:continue
            pp=prior|1<<i;cv=[chance(j,h-1,pp)for j in edges[i]];wv=[exact(j,h-1,pp)for j in edges[i]];best=max(cv);robust=max(wv);chosen=[k for k,v in enumerate(cv)if v==best]
            census['seat0_history_classes']+=1;census['some_uniform_optimum_worse_minimax']+=any(wv[k]<robust for k in chosen);census['all_uniform_optima_worse_minimax']+=all(wv[k]<robust for k in chosen)
        oracle=sum(F(r['oracle_uniform_U'])for r in root_rows)/len(root_rows)
        comparisons=[]
        for policy in('unitD1','positive_cellD1','unitD2'):
            oldrow=next(r for r in past['rows']if r['family']==family['family']and r['foe']=='UNIFORM'and r['policy']==policy)
            comparisons.append(dict(policy=policy,old_nominal_U=oldrow['U'],oracle_gap=str(oracle-F(oldrow['U']))))
        row=dict(family=family['family'],fingerprint=c.ruleset_fingerprint,roots=len(root_rows),history_classes=len(contexts),oracle_uniform_U=str(oracle),root_some_conflict=sum(r['some_chance_optimum_worse_minimax']for r in root_rows),root_all_conflict=sum(r['all_chance_optima_worse_minimax']for r in root_rows),census=dict(census),comparisons=comparisons,root_rows=root_rows)
        result.append(row);print({k:v for k,v in row.items()if k!='root_rows'},flush=True)
    out=dict(verified=True,rows=result,seconds=time.perf_counter()-tick,Player_queries=0,training_episodes=0,source_inputs_digest=digest(inputs),source_truth_digest=digest(truth),scope='OnlytwoalreadyexposedH6/repeat2A/Bfamiliesandtheir128oldunfilteredstartseach. ExactnominalIIDUniform-opponentterminalW-Loracle,notactualservedpolicygainornewtraining. Classcountsareconditionaldiagnostics,notnaturaloccupation;sourcefullSessionclassqualificationwaspreviouslypublished. No newrules/layouts/clock/caprefill.')
    Path(output).write_text(json.dumps(out,indent=2),encoding='utf8');return out


def compare_scalar_cells(directory,objective,output,*,seconds=180):
    """Posthoc representation control, not a trained or adopted price.

    All signed surviving-count affine leaves cross only at B=-1,0,1.
    Seven exact representatives cover their intervals/singletons while the
    terminal score dominates material. Actual rounded/partial Player returns
    need not share these nominal regions.
    """
    from scripts.leaper_h6_policy_bounds import policy_values
    tick=time.perf_counter();directory=Path(directory);inputs=load(directory/'inputs.json.gz');truth=load(directory/'truth.json.gz');adj=load(directory/'adjacent-pairs.json.gz');src={r['id']:r for r in truth['roots']};rows=[]
    if objective['source_inputs_digest']!=digest(inputs)or objective['source_truth_digest']!=digest(truth):raise ValueError('objective source differs')
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('SCALAR_CELL_CAP_UNKNOWN_NO_REFILL')
    for pair in adj['pairs']:
      for tag,key in(('left_family','left_id'),('right_family','right_id')):
        family=next(f for f in inputs['families']if f['family']==pair[tag]);rr=[r for r in inputs['rows']if r['family']==family['family']];c=admit(family,rr[0]);d=load(directory/f"domain{family['family']}.json.gz")
        expected=next(r['domain_digest']for r in load(directory/'summary.json')['families']if r['family']==family['family'])
        if digest(d)!=expected:raise ValueError('scalar-cell domain differs')
        positions=[decode_position(p,c.initial_position)for p in d['positions']];sides=[p.side_to_move for p in positions];terms={int(i):v for i,v in d['terminals'].items()}
        phi=[(sum(p is not None and(p.owner,p.current_type_id)==(0,'A')for p in pos.board),-sum(p is not None and(p.owner,p.current_type_id)==(1,'B')for p in pos.board))for pos in positions]
        ended,exact,_,decision,_=evaluate(d['edges'],terms,sides,phi,guard);cells=[]
        for B in map(F,(-2,-1,'-1/2',0,'1/2',1,2)):
            guard();walk,_=policy_values(d['edges'],terms,sides,ended,exact,decision,1,B,'UNIFORM',guard)
            utilities=[walk(src[r[key]]['root_index'],6,0)for r in pair['rows']]
            value=sum(item[0][0]-item[0][2]for item in utilities)/len(utilities)
            cells.append(dict(B=str(B),nominal_U=str(value),arbitrary_history_tie_U_bounds=[str(sum(item[k]for item in utilities)/len(utilities))for k in(1,2)]))
        best=max(F(r['nominal_U'])for r in cells);oracle=F(next(r['oracle_uniform_U']for r in objective['rows']if r['family']==family['family']))
        if best>oracle:raise ValueError('nominal policy beats unrestricted exact oracle')
        tie_best=max(F(r['arbitrary_history_tie_U_bounds'][1])for r in cells)
        if tie_best>oracle:raise ValueError('restricted tie controller beats unrestricted oracle')
        rows.append(dict(family=family['family'],cells=cells,best_nominal_U=str(best),best_cells=[r['B']for r in cells if F(r['nominal_U'])==best],unrestricted_oracle_U=str(oracle),unclosed_uniform_tie_policy_class_gap=str(oracle-best),best_arbitrary_history_tie_U=str(tie_best),unclosed_even_with_oracle_ties=str(oracle-tie_best)))
    result=dict(verified=True,rows=rows,seconds=time.perf_counter()-tick,Player_queries=0,training_episodes=0,scope='Posthocoraclecomparisonofall7signedscalarpricecellsfornominalcompleteD1/uniformtieonOLDunfilteredmu. Arbitrarytieenvelopesallowhistoryoraclechoices,notservedengineties;theuniformtiepolicygapaloneisnotapurepricefeatureobstruction. Notfittedlearning,heldoutselection,actualrounded/timedPlayerpolicyorpriceadoption. Nopricecellcrossingorpositivegainisanadmissiongateforanewboundedlearningtest.')
    Path(output).write_text(json.dumps(result,indent=2),encoding='utf8');return result
