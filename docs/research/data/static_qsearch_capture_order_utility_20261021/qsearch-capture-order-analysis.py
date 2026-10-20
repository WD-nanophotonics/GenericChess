from __future__ import annotations
import hashlib,json,statistics
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[4]
RUN=BASE/'qsearch-capture-order-run-20261021'
PLAN=json.loads((BASE/'qsearch-capture-order-plan.json').read_text(encoding='utf-8'))
rows=[json.loads(x) for x in (RUN/'qsearch-capture-order-games.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
expected=set(PLAN['arms']['candidate'])
if len(rows)!=64: raise SystemExit(f'SLOT_COUNT:{len(rows)}')
keys=[(r['root_id'],r['candidate_owner'],r['variant']) for r in rows]
if len(keys)!=len(set(keys)): raise SystemExit('DUPLICATE_SLOT')
roots={r['root_id']:r for r in json.loads((RUN/'roots.json').read_text(encoding='utf-8'))}
pairmap={}
unit_values={-10,0,990,1000}
q_calls_by_arm={v:0 for v in expected}; q_changed_values=0; normal_calls=0
for g in rows:
    if not g['full_history_replay_equal'] or g['action_invalid_count']:
        raise SystemExit(f"INTEGRITY_FAILURE:{g['game_id']}")
    if g['normal_type_value_calls'] or g['q_type_value_calls']:
        raise SystemExit(f"UNPLANNED_TYPE_VALUE_CALL:{g['game_id']}")
    for m in g['moves']:
        for t in m['normal_capture_order_trace']:
            if t['value'] not in unit_values: raise SystemExit(f"NON_UNIT_NORMAL_ORDER:{g['game_id']}")
        if m['role']=='candidate':
            q_calls_by_arm[g['variant']]+=m['q_capture_order_calls_delta']
            for t in m['q_capture_order_trace']:
                if g['variant']=='static_v2_q_order' and t['value'] not in unit_values:
                    q_changed_values+=1
        normal_calls+=m['normal_capture_order_calls_delta']
    k=(g['root_id'],g['candidate_owner'])
    pairmap.setdefault(k,{})[g['variant']]=g
if len(pairmap)!=32 or any(set(p)!=expected for p in pairmap.values()): raise SystemExit('PAIR_COMPLETENESS')
def bounds(g): return (-1,1) if g['reward'] is None else (int(g['reward']),int(g['reward']))
def candidate(g): return [m for m in g['moves'] if m['role']=='candidate']
def cost(g,field): return sum(int(m[field]) for m in candidate(g))
def secs(g): return sum(float(m['elapsed_seconds']) for m in candidate(g))
def wdl(gs):
    out={'win':0,'draw':0,'loss':0,'unknown':0}
    for g in gs:
        if g['reward'] is None: out['unknown']+=1
        elif g['reward']==1: out['win']+=1
        elif g['reward']==0: out['draw']+=1
        else: out['loss']+=1
    return out
pairs=[]; divergence=[]
for (rid,owner),arms in sorted(pairmap.items()):
    u=arms['unit_q_order']; s=arms['static_v2_q_order']
    if u['root_state_sha256']!=s['root_state_sha256']: raise SystemExit(f'ROOT_MISMATCH:{rid}:{owner}')
    ulo,uhi=bounds(u); slo,shi=bounds(s); ri=roots[rid]
    cm_u={m['state_before']:m['action'] for m in candidate(u)}
    cm_s={m['state_before']:m['action'] for m in candidate(s)}
    common=set(cm_u)&set(cm_s)
    divergence.append({'root_id':rid,'owner':owner,'common_candidate_states':len(common),'different_actions':sum(cm_u[x]!=cm_s[x] for x in common)})
    pairs.append({'root_id':rid,'seed':ri['seed'],'family':ri['family'],'root_plies':ri['prefix_plies'],'candidate_owner':owner,
      'candidate_first':owner==(ri['prefix_plies']%2),'unit_reward':u['reward'],'static_reward':s['reward'],
      'utility_lower':slo-uhi,'utility_upper':shi-ulo,'both_known':u['reward'] is not None and s['reward'] is not None,
      'unit_candidate_nodes':cost(u,'nodes'),'static_candidate_nodes':cost(s,'nodes'),
      'unit_candidate_qnodes':cost(u,'qnodes'),'static_candidate_qnodes':cost(s,'qnodes'),
      'unit_candidate_qorder_calls':cost(u,'q_capture_order_calls_delta'),'static_candidate_qorder_calls':cost(s,'q_capture_order_calls_delta'),
      'unit_candidate_seconds':secs(u),'static_candidate_seconds':secs(s)})
def util(ps):
    n=len(ps)
    return {'n_pairs':n,'both_known_pairs':sum(x['both_known'] for x in ps),'pairs_with_unknown':sum(not x['both_known'] for x in ps),
      'mean_conservative_lower':sum(x['utility_lower'] for x in ps)/n if n else None,
      'mean_conservative_upper':sum(x['utility_upper'] for x in ps)/n if n else None,
      'lower_sum':sum(x['utility_lower'] for x in ps),'upper_sum':sum(x['utility_upper'] for x in ps)}
def cost_summary(ps):
    vals=[(x['unit_candidate_nodes']-x['static_candidate_nodes'])/max(x['unit_candidate_nodes'],1) for x in ps]
    qvals=[(x['unit_candidate_qnodes']-x['static_candidate_qnodes'])/max(x['unit_candidate_qnodes'],1) for x in ps]
    return {'n_pairs':len(ps),'unit_candidate_nodes':sum(x['unit_candidate_nodes'] for x in ps),'static_candidate_nodes':sum(x['static_candidate_nodes'] for x in ps),
      'median_paired_node_reduction':statistics.median(vals) if vals else None,'pairs_nodes_unit_zero':sum(x['unit_candidate_nodes']==0 for x in ps),
      'unit_candidate_qnodes':sum(x['unit_candidate_qnodes'] for x in ps),'static_candidate_qnodes':sum(x['static_candidate_qnodes'] for x in ps),
      'median_paired_qnode_reduction':statistics.median(qvals) if qvals else None,
      'unit_candidate_seconds':sum(x['unit_candidate_seconds'] for x in ps),'static_candidate_seconds':sum(x['static_candidate_seconds'] for x in ps)}
groups={'overall':pairs}
for o in (0,1): groups[f'owner_{o}']=[p for p in pairs if p['candidate_owner']==o]
for n in (3,4): groups[f'root_plies_{n}']=[p for p in pairs if p['root_plies']==n]
for f in (True,False): groups[f'candidate_{"first" if f else "reply"}']=[p for p in pairs if p['candidate_first']==f]
metrics={k:{'utility':util(v),'candidate_cost':cost_summary(v)} for k,v in groups.items()}
loo={str(seed):{'utility':util([p for p in pairs if p['seed']!=seed]),'candidate_cost':cost_summary([p for p in pairs if p['seed']!=seed])} for seed in sorted({p['seed'] for p in pairs})}
required=['overall','owner_0','owner_1','root_plies_3','root_plies_4']
gate_a=all(metrics[k]['utility']['mean_conservative_lower']>0 for k in required) and all(v['utility']['mean_conservative_lower']>0 for v in loo.values())
gate_b=all(metrics[k]['candidate_cost']['median_paired_node_reduction']>=.10 for k in required) and all(metrics[k]['utility']['mean_conservative_lower']>=0 for k in required)
unknown=[g for g in rows if g['reward'] is None]
run_result=json.loads((RUN/'result.json').read_text(encoding='utf-8'))
summary={'schema':'primary-static-qsearch-capture-order-utility-analysis-v1','status':'COMPLETE','session_id':PLAN['session_id'],
 'plan_sha256':hashlib.sha256((BASE/'qsearch-capture-order-plan.json').read_bytes()).hexdigest(),
 'preflight_sha256':hashlib.sha256((BASE/'qsearch-capture-order-preflight.json').read_bytes()).hexdigest(),
 'producer_sha256':hashlib.sha256((BASE/'qsearch-capture-order-producer.py').read_bytes()).hexdigest(),
 'execution_sha256':hashlib.sha256((RUN/'execution-start.json').read_bytes()).hexdigest(),
 'games_sha256':hashlib.sha256((RUN/'qsearch-capture-order-games.jsonl').read_bytes()).hexdigest(),
 'physical_games':len(rows),'pairs':len(pairs),'actual_terminals':run_result['actual_terminals'],'unknown_slots':len(unknown),
 'unknown_reasons':{k:sum(g['terminal_reason']==k for g in unknown) for k in sorted({g['terminal_reason'] for g in unknown})},
 'invalid_actions':sum(g['action_invalid_count'] for g in rows),'replay_mismatches':sum(not g['full_history_replay_equal'] for g in rows),
 'unit_value_domain_for_normal_orders':sorted(unit_values),'all_normal_order_values_unit':True,'normal_capture_calls':normal_calls,
 'candidate_q_order_capture_calls':q_calls_by_arm,'static_q_values_outside_unit_domain':q_changed_values,
 'type_value_calls':{'normal':run_result['normal_type_value_calls'],'qsearch':run_result['q_type_value_calls']},
 'candidate_wdl':{v:wdl([g for g in rows if g['variant']==v]) for v in sorted(expected)},
 'strata':metrics,'leave_one_seed_out':loo,'same_state_action_comparison':{'common_candidate_states':sum(x['common_candidate_states'] for x in divergence),'different_actions':sum(x['different_actions'] for x in divergence),'pairs':divergence},
 'retention_gate':{'utility_gate_a':gate_a,'node_saving_gate_b':gate_b,'retain_scoped_candidate':gate_a or gate_b,'tested_views':required,'loo_seed_count':len(loo),'scope_claim':'No default/global price, population or strength claim.'},
 'run_receipt':run_result,'pairs':pairs}
out=RUN/'analysis.json'; out.write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('physical_games','pairs','actual_terminals','unknown_slots','unknown_reasons','invalid_actions','replay_mismatches','candidate_q_order_capture_calls','static_q_values_outside_unit_domain','candidate_wdl','strata','retention_gate','same_state_action_comparison')},sort_keys=True))
