"""Independent AUX intake of the fixed PVS packet; no producer/Player import."""
from collections import Counter,defaultdict
from copy import deepcopy
from fractions import Fraction
import argparse,gzip,hashlib,json,subprocess
from pathlib import Path
from scripts.leaper_truth_compatibility import bind_context,digest
from scripts.research_record import record_value
from generic_chess.session.serialization import deserialize_game_record

COMMIT='c695161cbc16fe5881773d4465ad00c1c5e1181e'
BASE='docs/research/data/leaper_pvs_quality_pilot_20261026/'
INPUT='docs/research/data/leaper_root_order_quality_20261026/prepared-v2/inputs.json.gz'

def git_bytes(path):
    return subprocess.check_output(['git','show',COMMIT+':'+path])

def qualify():
    manifest_bytes=git_bytes(BASE+'manifest.json')
    manifest=json.loads(manifest_bytes);receipts=[]
    def read(name):
        packed=git_bytes(BASE+name+'.gz');raw=gzip.decompress(packed)
        item=manifest['members'][name]
        if hashlib.sha256(packed).hexdigest()!=item['gzip_sha256'] or hashlib.sha256(raw).hexdigest()!=item['original_sha256'] or len(raw)!=item['original_bytes']:
            raise ValueError('manifest mismatch: '+name)
        receipts.append(dict(path=BASE+name+'.gz',gzip_sha256=item['gzip_sha256'],original_sha256=item['original_sha256']))
        return json.loads(raw)
    executed=read('pilot/executed-source.json')
    plan=read('execution-plan.json')
    plan_raw=gzip.decompress(git_bytes(BASE+'execution-plan.json.gz'))
    if hashlib.sha256(plan_raw).hexdigest()!=executed['plan_sha256']:
        raise ValueError('executed plan binding differs')
    inputs_bytes=git_bytes(INPUT)
    if hashlib.sha256(inputs_bytes).hexdigest()!=executed['input_sha256']:
        raise ValueError('executed input binding differs')
    if plan['input_sha256']!=executed['input_sha256']:
        raise ValueError('plan/input binding differs')
    source_bindings=[]
    for name,captured in executed['product_sources'].items():
        published=git_bytes(name).decode('utf-8')
        if captured.replace('\r\n','\n')!=published.replace('\r\n','\n'):
            raise ValueError('executed/published source differs: '+name)
        source_bindings.append(dict(path=name,published_LF_sha256=hashlib.sha256(published.replace('\r\n','\n').encode()).hexdigest()))
    inputs=json.loads(gzip.decompress(inputs_bytes))
    rows={r['id']:r for r in inputs['rows']}
    games=read('pilot/games.json');returns=read('pilot/returns.json');qualification=read('pilot/qualification.json')
    if len(games)!=24 or {g['game_id']for g in games}!=set(range(24)):
        raise ValueError('fixed24 planned source slots differ')
    slots=[];counts=Counter();contexts={};seen=set();groups=defaultdict(list)
    for game in games:
        # Check each individually archived slot as well as the aggregate.
        original_game=read('pilot/game-'+str(game['game_id']).zfill(2)+'.json')
        if original_game!=game:raise ValueError('aggregate/individual game differs')
        row=rows[game['case_id']]
        if row['record']!=game['initial_record'] or row['fingerprint']!=game['fingerprint'] or row['family']!=game['family']:
            raise ValueError('full initial context differs')
        if row['id'] not in contexts:contexts[row['id']]=bind_context(row['RuleSet'],row['record'])
        initial=contexts[row['id']]
        final=bind_context(row['RuleSet'],game['final_record'],compiled=initial.session.compiled)
        if record_value(final.session.state.terminal_status)!=game['Core_terminal'] or record_value(final.session.result)!=game['Session_result']:
            raise ValueError('actual Core/Session endpoint differs')
        if final.session.result.status.value not in ('repetition','max_ply','stalemate') or final.session.result.winner is not None:
            raise ValueError('not an actual Core draw')
        record=deepcopy(game['initial_record']);start=len(record['actions'])
        wire=game['final_record']['actions'];typed=deserialize_game_record(json.dumps(game['final_record'])).actions
        if wire[:start]!=record['actions'] or len(wire)-start!=len(game['queries']):
            raise ValueError('initial prefix or query denominator differs')
        local=Counter();bad=[];bad_frontiers=[]
        for i,q in enumerate(game['queries'],start):
            key=q['query_id']
            if key in seen:raise ValueError('duplicate return in game slots')
            seen.add(key);raw_entry=returns[key];raw=raw_entry['original_utf8'].encode('utf-8')
            if hashlib.sha256(raw).hexdigest()!=raw_entry['sha256']:
                raise ValueError('original return bytes differ')
            observed=json.loads(raw)
            if any(q.get(k)!=v for k,v in observed.items()):raise ValueError('query annotation changes original return')
            if q['record_before_sha256']!=digest(record) or q['ply_before']!=i:
                raise ValueError('full query prefix binding differs')
            # Literal final replay establishes legality; no missing move generated.
            if record_value(typed[i])!=q['decision']['action']:
                raise ValueError('returned action and actual record differ')
            record['actions'].append(wire[i])
            if q['record_after_sha256']!=digest(record):raise ValueError('full child record hash differs')
            if q['seat']!=(initial.session.state.position.side_to_move+(i-start))%2 or q['on']!=(q['seat']==game['on_seat']):
                raise ValueError('actual actor/policy attribution differs')
            deadline=q['limits']['max_time_seconds'];eligible=q['outer_seconds']<=deadline+max(.025,.1*deadline)
            if q['timing_eligible']!=eligible:raise ValueError('timing annotation differs')
            if not eligible:
                bad.append(key)
                bad_record=deepcopy(game['final_record']);bad_record['actions']=wire[:i]
                bad_context=bind_context(row['RuleSet'],bad_record,compiled=initial.session.compiled)
                bad_frontiers.append(dict(query_id=key,context=bad_context.identity,legal_actions=len(bad_context.legal_actions),regret='UNKNOWN'))
            decision=q['decision'];pv=decision['principal_variation']
            local.update(returns=1,empty_PV=int(not pv),PV_present=int(bool(pv)),supplied_PV_plies=len(pv),
                         caller_deadline_observed=int(q['caller_deadline_observed']))
            local['search_termination:'+str(decision['termination_reason'])]+=1
            local['policy_ON:'+str(q['on'])]+=1
            local['reported_runtime_depth_balanced:'+str(decision['runtime_depth_balanced'])]+=1
            local['caller_status:'+str(q['status'])]+=1
            if pv and pv[0]!=decision['action']:raise ValueError('supplied PV first move differs')
        if record!=game['final_record'] or game['timing_eligible']!=(not bad):
            raise ValueError('whole-game source or timing qualifier differs')
        groups[game['case_id']].append(game)
        counts.update(local);counts['actual_Core:'+final.session.result.status.value]+=1
        slots.append(dict(game_id=game['game_id'],case_id=game['case_id'],family=game['family'],on_seat=game['on_seat'],
             initial_context=initial.identity,final_context=final.identity,actual_Core_DRAW=True,
             timing_eligible=not bad,timing_ineligible_query_ids=bad,timing_ineligible_frontiers=bad_frontiers,queries=dict(local),
             initial_legal_actions=len(initial.legal_actions),root_minimax_WDL='UNKNOWN',
             minimax_root_or_action_labels='UNKNOWN',TT_internal_identity_and_memory='NOT_SNAPSHOTTED_NOT_VERIFIED',
             qualification='FULL_RECORD_REPLAY_AND_RETURN_BYTES_BOUND; PV content presence counted, interior PV not freshly replayed'))
    if any(len(g)!=2 or {h['on_seat']for h in g}!={0,1}for g in groups.values()) or len(groups)!=12:
        raise ValueError('complete switched-seat root pairs differ')
    qualification_ids={q['query_id']for q in qualification}
    if len(qualification)!=24 or set(returns)!=seen|qualification_ids or seen&qualification_ids:
        raise ValueError('qualification/game return partition differs')
    # These remain source-reported search returns, not newly executed searches.
    for q in qualification:
        e=returns[q['query_id']];raw=e['original_utf8'].encode()
        if hashlib.sha256(raw).hexdigest()!=e['sha256']:raise ValueError('qualification return hash differs')
        original=json.loads(raw)
        if q['decision']!=original['decision']:raise ValueError('qualification decision differs')
    qualified=sum(s['timing_eligible']for s in slots)
    known=Fraction(qualified,2)
    pair_qualified_ids={g['game_id']for gg in groups.values()if all(g['timing_eligible']for g in gg)for g in gg}
    pair_known=Fraction(len(pair_qualified_ids),2)
    pair_protocol=[str(pair_known/24),str((pair_known+24-len(pair_qualified_ids))/24)]
    family_bounds=[]
    for family in sorted({s['family']for s in slots}):
        family_slots=[s for s in slots if s['family']==family]
        retained=sum(s['game_id']in pair_qualified_ids for s in family_slots)
        known_points=Fraction(retained,2);denominator=len(family_slots)
        family_bounds.append(dict(family=family,planned_games=denominator,pair_qualified_games=retained,
            mean_bounds=[str(known_points/denominator),str((known_points+denominator-retained)/denominator)]))
    return dict(status='PASS',source_commit=COMMIT,manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        input_path=INPUT,input_sha256=executed['input_sha256'],hash_checked_members=receipts,executed_product_source_bindings=source_bindings,slots=slots,
        planned_game_slots=24,source_rules=len({s['initial_context']['ruleset_fingerprint']for s in slots}),
        families=len({s['family']for s in slots}),counts=dict(counts),source_game_returns=len(seen),
        source_qualification_returns=len(qualification),timing_qualified_games=qualified,
        complete_timing_qualified_pairs=sum(all(g['timing_eligible']for g in gg)for gg in groups.values()),
        actual_ON_mean_points='1/2',single_ineligible_slot_completion_bounds=[str(known/24),str((known+24-qualified)/24)],
        frozen_complete_pair_protocol_completion_bounds=pair_protocol,
        frozen_pair_mask_unknown_game_ids=sorted(set(range(24))-pair_qualified_ids),family_pair_completion_bounds=family_bounds,
        possible_positive_family_count_outer_bounds=[sum(Fraction(f['mean_bounds'][0])>Fraction(1,2)for f in family_bounds),sum(Fraction(f['mean_bounds'][1])>Fraction(1,2)for f in family_bounds)],
        new_Player=0,new_solver=0,new_games=0,new_training=0,action_WDL_labels_created=0,
        scope='Independent fixed-source intake. All24actual GameRecords replayed;2115recorded query prefixes and original return bytes bound. No interior PV replay, internal TT snapshot verification, missing-state solve or inference that DRAW actions are optimal. No source code executed.')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ('slots','hash_checked_members')}))
if __name__=='__main__':main()
