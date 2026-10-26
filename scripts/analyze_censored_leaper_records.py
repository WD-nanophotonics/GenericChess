"""Censoring views of fixed published records, not new trials or WDL solving."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

from scripts.paired_path_bounds import analyze_pair, observed_regret_sum, verify_forced_link, _potential, _rule_wdl_scope
from scripts.leaper_truth_compatibility import bind_context, digest
from scripts.qualify_primary_leaper_sources import read_checked
from scripts.research_record import record_value
from scripts.score_published_leaper_choices import load_source,SOURCE_COMMIT
from scripts.audit_published_leaper_exposure import _experienced_regret_mean_bounds

QUALIFIED_COMMIT='bfd43fe406b72c7d4a4f5df492f42772fc4a60ba'
QUALIFIED_PATH='docs/research/data/aux_saved_decisions_20261026/game-exposure.json.gz'


def cut(record,ply):
    if ply is None:return None
    result=deepcopy(record);result['actions']=result['actions'][:ply];return result


def abstract_pair(a,b):
    same=a['key']==b['key']
    prefix=[0,0]if same else[a['bounds'][0]-b['bounds'][1],a['bounds'][1]-b['bounds'][0]]
    points=[]
    for index,endpoint in enumerate((a,b)):
        if endpoint['terminal']:
            z=endpoint['bounds'][0];point=Fraction(1+(z if index==0 else-z),2);points.append((point,point))
        else:points.append((Fraction(0),Fraction(1)))
    score=[str(sum(p[j]for p in points)/2)for j in(0,1)]
    return [str(v)for v in prefix],score


def analyze(source):
    packet,_=load_source(source);rows={r['id']:r for r in packet['rows']}
    manifest=json.loads((source/'manifest.json').read_bytes())
    def read(name):return read_checked(source/name,name,manifest)
    games=read('population-games/games.json.gz');executed=read('population-games/executed-source.json.gz')
    qualified_bytes=subprocess.check_output(['git','show',QUALIFIED_COMMIT+':'+QUALIFIED_PATH])
    qualified=json.loads(gzip.decompress(qualified_bytes));qmap={q['query_id']:q for q in qualified['queries']}
    prefixes={};paths=[];actual_points={};forced_omission_verified=False;total_crosschecks=0;all_classes=Counter();case_results=[]
    for game in games:
        case=game['case_id'];row=rows[case];start=len(game['initial_record']['actions'])
        if game['initial_record']!=row['record']:raise ValueError('source initial record differs')
        timeline=[];record=deepcopy(game['initial_record'])
        for index,query in enumerate(game['queries']):
            q=qmap[query['query_id']]
            if q['game_id']!=game['game_id']or q['ply']!=start+index or q['record_before_sha256']!=digest(record):
                raise ValueError('qualified snapshot/actual record prefix differs')
            if q['query_id']==371:
                child_record=deepcopy(record);child_record['actions'].append(q['action'])
                if digest(child_record)!=query['record_after_sha256']:
                    raise ValueError('provided forced child record differs from saved source')
                forced_proof=verify_forced_link(row['RuleSet'],record,child_record)
                if forced_proof['status']!='VERIFIED_FORCED_VALUE_EQUALITY':
                    raise ValueError('timing omitted action is not a verified forced choice')
                forced_omission_verified=True
            timeline.append(dict(key=(game['fingerprint'],q['record_before_sha256']),bounds=[-1,1],terminal=False,
                position=q['position_sha256'],ply=q['ply'],repetition=q['repetition_counts_sha256']))
            record['actions'].append(q['action'])
        if record!=game['final_record']:raise ValueError('qualified saved actual actions do not reconstruct final record')
        end=bind_context(row['RuleSet'],record);_rule_wdl_scope(end)
        if record_value(end.session.result)!=game['Session_result']:raise ValueError('actual final Core/Session differs')
        timeline.append(dict(key=(game['fingerprint'],end.identity['record_sha256']),bounds=_potential(end),terminal=True,
            position=end.identity['position_sha256'],ply=end.identity['ply'],repetition=digest(end.identity['repetition_counts'])))
        z=_potential(end)[0]
        actual_points[game['game_id']]=Fraction(1+(z if game['long_seat']==0 else-z),2)
        prefixes[game['game_id']]=timeline
        paths.append(dict(rule=row['RuleSet'],initial_record=row['record'],endpoint_record=record,candidate_seat=game['long_seat']))
    for case in executed['root_ids']:
        a,b=sorted([g for g in games if g['case_id']==case],key=lambda g:g['long_seat'])
        aa,bb=prefixes[a['game_id']],prefixes[b['game_id']];counts=Counter();bound_counts=Counter();false_board=0;false_board_clock=0
        common=next(r['common_actual_move_prefix']for r in qualified['prefix_stopping_diagnostics']if r['case_id']==case)
        for ea in aa:
            for eb in bb:
                prefix,score=abstract_pair(ea,eb);bound_counts[','.join(prefix)]+=1
                counts['cut_pairs']+=1;counts['same_full_endpoint']+=int(ea['key']==eb['key'])
                counts['strict_positive_regret_lower_bound']+=int(Fraction(prefix[0])>0)
                counts['both_terminal']+=int(ea['terminal']and eb['terminal'])
                counts['neither_terminal']+=int(not ea['terminal']and not eb['terminal'])
                counts['one_terminal']+=int(ea['terminal']!=eb['terminal'])
                false_board+=int(ea['position']==eb['position']and ea['key']!=eb['key'])
                false_board_clock+=int(ea['position']==eb['position']and ea['ply']==eb['ply']and ea['key']!=eb['key'])
        n,m=len(aa)-1,len(bb)-1
        controls=[(0,0),(common,common),(common+1,common+1),(n,m),(n,m-1),(n-1,m),(0,m),(n,0)]
        for i,j in controls:
            result=analyze_pair(rows[case]['RuleSet'],rows[case]['record'],cut(a['final_record'],aa[i]['ply']),cut(b['final_record'],bb[j]['ply']))
            expected,score=abstract_pair(aa[i],bb[j])
            if result['baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds']!=expected or result['candidate_planned_mean_game_point_completion_bounds']!=score:
                raise ValueError('independent raw-record replay disagrees with endpoint census')
            total_crosschecks+=1
        all_classes.update(counts)
        case_results.append(dict(case_id=case,family=rows[case]['family'],n=rows[case]['n'],counts=dict(counts),
            prefix_regret_bound_counts=dict(bound_counts),same_position_different_context_cut_pairs=false_board,
            same_position_and_clock_different_context_cut_pairs=false_board_clock))
    cohorts={}
    for name,selected in [('all_24_games',games),('timing_eligible_23_games',[g for g in games if g['timing_eligible']]),
        ('complete_timing_pairs',[g for g in games if all(h['timing_eligible']for h in games if h['case_id']==g['case_id'])])]:
        chosen_ids={g['game_id']for g in selected}
        selected_paths=[p for g,p in zip(games,paths)if g['game_id']in chosen_ids]
        cohort=observed_regret_sum(selected_paths)
        counts=Counter(q['policy']for q in qmap.values()if q['game_id']in chosen_ids)
        cohort['recorded_decision_counts']=dict(counts)
        nonforced=Counter(q['policy']for q in qmap.values()if q['game_id']in chosen_ids and not q['forced_action'])
        cohort['nonforced_decision_counts']=dict(nonforced)
        lo,hi=map(Fraction,cohort['baseline_minus_candidate_experienced_actor_WDL_regret_bounds'])
        if lo.denominator!=1 or hi.denominator!=1:raise ValueError('this source gap interval is not integral')
        possibilities=[_experienced_regret_mean_bounds(counts['short'],counts['long'],nonforced['short'],nonforced['long'],gap)
                       for gap in range(int(lo),int(hi)+1)]
        cohort['experienced_short_minus_long_mean_regret_outer_bounds']=[str(min(Fraction(p['short_minus_long_mean_WDL_regret_outer_bounds'][0])for p in possibilities)),str(max(Fraction(p['short_minus_long_mean_WDL_regret_outer_bounds'][1])for p in possibilities))]
        cohort['mean_scope']='Outer aggregate constraints only; uncertainty in residual root potentials is retained. Not independent strength evidence or actual RuleSet completions.'
        cohorts[name]=cohort
    selected=[(g,p)for g,p in zip(games,paths)if g['timing_eligible']]
    color_counts=Counter(g['long_seat']for g,p in selected)
    normalized_paths=[dict(p,weight=str(Fraction(1,color_counts[g['long_seat']])))for g,p in selected]
    normalized=observed_regret_sum(normalized_paths)
    normalized['color_game_counts']={str(k):v for k,v in color_counts.items()}
    normalized['weight_scope']='Sum of two empirical color means (each color total weight1); not raw23game total or a common-root expected policy contrast.'
    root_records={digest(g['initial_record'])for g in games}
    mismatch=sum((abs(Fraction(t['coefficient']))for t in normalized['residual_context_potentials']if t['record_sha256']in root_records),Fraction())
    normalized['initial_context_coefficient_L1']=str(mismatch)
    cohorts['timing_23_color_normalized']=normalized
    if len(games)!=2*len(executed['root_ids']) or len({g['game_id']for g in games})!=len(games):
        raise ValueError('planned source game denominator differs')
    family_scores=[]
    for family in sorted({rows[g['case_id']]['family']for g in games}):
        group=[g for g in games if rows[g['case_id']]['family']==family]
        bounds=[sum((actual_points[g['game_id']]if g['timing_eligible']else Fraction(j))for g in group)/len(group)for j in(0,1)]
        family_scores.append(dict(family=family,planned_games=len(group),timing_qualified_games=sum(g['timing_eligible']for g in group),
            actual_candidate_mean_points=str(sum(actual_points[g['game_id']]for g in group)/len(group)),
            protocol_completion_mean_point_bounds=[str(v)for v in bounds]))
    protocol_bounds=[sum((actual_points[g['game_id']]if g['timing_eligible']else Fraction(j))for g in games)/len(games)for j in(0,1)]
    score_target=dict(planned_games=len(games),actual_Core_terminal_games=len(games),
        actual_all_game_mean_points=str(sum(actual_points.values())/len(games)),
        actual_timing_eligible_game_mean_points=str(sum(actual_points[g['game_id']]for g in games if g['timing_eligible'])/sum(g['timing_eligible']for g in games)),
        protocol_completion_mean_point_bounds=[str(v)for v in protocol_bounds],families=family_scores,
        strictly_positive_family_count_outer_bounds=[sum(Fraction(r['protocol_completion_mean_point_bounds'][0])>Fraction(1,2)for r in family_scores),sum(Fraction(r['protocol_completion_mean_point_bounds'][1])>Fraction(1,2)for r in family_scores)],
        scope='Old resource-arm contrast only. Actual terminal outcomes remain facts; an inadmissible protocol slot gets a separate[0,1]hypothetical table-completion interval, not changed utility; no qualifying execution or attainable game score is asserted. No rerun, causal correction, significance, PVS prediction or new trial gate.')
    omitted=[q for q in qmap.values()if not q['timing_eligible']]
    if not forced_omission_verified or len(omitted)!=1 or omitted[0]['query_id']!=371 or not omitted[0]['forced_action']:
        raise ValueError('timing-omission zero-regret premise differs')
    eligible_counts=Counter(q['policy']for q in qmap.values()if q['timing_eligible'])
    if eligible_counts['short']!=eligible_counts['long']:raise ValueError('query-filtered denominators are not equal')
    total=qualified['terminal_outcome_contrasts']['short_minus_long_total_actor_regret']
    query_mean=str(Fraction(total,eligible_counts['short']))
    return dict(primary_source=SOURCE_COMMIT,qualified_source=dict(commit=QUALIFIED_COMMIT,path=QUALIFIED_PATH,
        sha256=hashlib.sha256(qualified_bytes).hexdigest()),status='PASS',saved_actual_games=len(games),
        source_derived_cut_pair_controls=dict(all_classes),cases=case_results,
        independent_raw_record_pair_checks=total_crosschecks,observed_path_cohorts=cohorts,
        forced_relation_refinement=dict(shared_prefix_forced_nodes=sum(r['legal_actions']==1 for r in qualified['matched_prefix_contexts']),
            decision='NO_ADDITIONAL_EQUALITY_CENSUS_IMPLEMENTED',
            scope='No common-prefix move is forced; full records never rejoin after actual divergence. Equality links on only supplied forced edges cannot connect the two divergent branches. Numeric terminal-value propagation is not performed.'),
        query_timing_mask=dict(eligible_queries=sum(eligible_counts.values()),counts=dict(eligible_counts),
            omitted_query=371,omitted_policy='short',omitted_regret=0,forced_omission_verified_by_Core=forced_omission_verified,
            experienced_short_minus_long_total_WDL_regret=total,
            experienced_short_minus_long_mean_WDL_regret=query_mean,
            scope='Algebraic masking of an independently checked forced zero-regret move; the real action remains in record replay. Not censoring repair, expected policy value or new game evidence.'),
        planned_protocol_score_completions=score_target,
        strict_positive_cut_families=sorted({str(r['family'])for r in case_results if r['counts']['strict_positive_regret_lower_bound']}),
        scope='Cut pairs are exhaustive source-derived retrospective views, not new trials, actual missing-slot frequencies or sampling probabilities. Uses prior qualified query contexts; final records and96representative cut pairs are freshly replayed. No local action truth or newPlayer/solver/game/build.',
        new_Player=0,new_solver=0,new_games=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=analyze(args.source);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items()if k not in('cases','observed_path_cohorts')}))


if __name__=='__main__':main()
