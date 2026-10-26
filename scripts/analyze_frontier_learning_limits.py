"""Data-only limits of partial terminal facts and ungated material targets."""
from collections import Counter,defaultdict
from fractions import Fraction
import argparse,gzip,json
from pathlib import Path
from scripts.leaper_truth_compatibility import bind_context,digest
from scripts.qualify_pvs_source_intake import git_bytes,BASE,INPUT
from scripts.propagate_pvs_terminal_bounds import load
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
from scripts.analyze_leaper_td_signals import rank as rational_rank


def analyze(frontiers,derived):
    contexts=derived['contexts'];parent_keys={(r['ruleset_fingerprint'],r['record_sha256'])for r in contexts}
    children=[tuple(c['child_key'])for r in contexts for c in r['children']]
    indegree=Counter(children)
    if any(n!=1 for n in indegree.values()):raise ValueError('conservative record graph is not the expected forest')
    roots=parent_keys-set(children);all_nodes=parent_keys|set(children)
    if len(all_nodes)-len(children)!=len(roots):raise ValueError('finite forest count differs')
    terminal=[c for r in contexts for c in r['children']if c['authority']=='CORE_TERMINAL']
    zero_feasible=all(c['bounds'][0]<=0<=c['bounds'][1]for r in contexts for c in r['children'])
    zero_feasible=zero_feasible and all(r['derived_bounds'][0]<=0<=r['derived_bounds'][1]for r in contexts)
    if not zero_feasible or any(c['bounds']!=[0,0]for c in terminal):raise ValueError('this packet does not admit the all-zero local relaxation')
    games={g['game_id']:g for g in json.loads(gzip.decompress(git_bytes(BASE+'pilot/games.json.gz')))}
    rows={r['id']:r for r in json.loads(gzip.decompress(git_bytes(INPUT)))['rows']}
    reps={q['context_sha256']:q for q in frontiers['queries']}
    features=[];groups=defaultdict(list);saved_plies=0
    for d in contexts:
        if d['derived_bounds']!=[0,0]:continue
        q=reps[d['source_context_sha256']];g=games[q['game_id']]
        record=dict(g['final_record']);record['actions']=record['actions'][:d['ply']]
        ctx=bind_context(rows[d['case_id']]['RuleSet'],record);saved_plies+=len(record['actions'])
        if ctx.identity['state_sha256']!=d['state_sha256']:raise ValueError('feature context differs')
        env=FixedScaleSessionEnv(ctx.session,unit_type='A',use_runtime=False)
        phi=env.features();names=env.names
        board={name:phi[i]for i,(kind,name)in enumerate(names)if kind=='board'}
        if any(phi[i]for i,(kind,name)in enumerate(names)if kind=='hand'):
            raise ValueError('this static two-board-feature diagnostic excludes nonempty hand channels')
        pair=[board.get('A',0),board.get('B',0)];groups[d['case_id']].append(pair)
        model=Model([1]*len(phi),fixed=0,scale=10)
        features.append(dict(case_id=d['case_id'],source_context_sha256=d['source_context_sha256'],
             source_query=q['query_id'],ply=d['ply'],exact_rule_WDL=0,channel_names=names,phi=phi,board_A_B_delta=pair,
             unit_weights_raw=model.raw(phi),unit_weights_prediction=model.prediction(phi),
             scope='Static ungated material prediction only, not an actual search receipt, learned model or prospective evaluation.'))
    per_rule=[]
    for case,matrix in sorted(groups.items()):
        nonzero=[v for v in matrix if any(v)]
        rank=rational_rank(matrix)
        ratios={Fraction(-a,b)for a,b in nonzero if b}
        impossible=any(a and not b for a,b in nonzero)or len(ratios)>1
        per_rule.append(dict(case_id=case,certified_query_contexts=len(matrix),feature_rows=matrix,rational_rank=rank,
            exact_zero_constraints_with_board_A_fixed_one=('INFEASIBLE'if impossible else'UNIDENTIFIED_B'if not ratios else'REQUIRES_B='+str(next(iter(ratios)))),
            scope='Necessary algebra for exact WDL=0 representation by an UNGATED linear/tanh material model. Not fitted prices, a requirement on a search-backed learner, a training recommendation or actual parameter values.'))
    return dict(status='PASS',finite_partial_record_forest=dict(initial_h2_roots=len(roots),internal_query_parents=len(parent_keys),
        generated_edges=len(children),known_terminal_leaves=len(terminal),unexpanded_nonterminal_leaves=derived['unexpanded_nonterminal_children'],
        total_record_nodes=len(all_nodes),duplicate_child_record_keys=0,
        scope='Conservative complete GameRecord keys unfold repeated positions; this is not a position-only SCC or a statement about the full game graph.'),
        all_zero_relaxation=dict(feasible=True,fixed_value=0,strict_action_gap_in_this_completion=0,
        scope='A feasible assignment for these observed/local interval constraints only, not an attainable full RuleSet minimax solution. Therefore these facts alone cannot force a strict action preference.'),
        exact_context_material_features=features,per_rule_material_constraints=per_rule,
        model_updates=0,new_Player_calls=0,new_played_games=0,new_hypothetical_successors=0,
        actual_saved_records_replayed=len(features),actual_saved_record_plies_replayed=saved_plies,
        scope='All18exact query-parent DRAW contexts retained, no oracle-selected training starts or fitting. Partial bounds are not replaced by point targets. Material-only exact representability differs from semantic search correctness and terminal TD credit.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--frontiers',type=Path,required=True);p.add_argument('--derived',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=analyze(load(a.frontiers),load(a.derived));a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items()if k not in ('exact_context_material_features','per_rule_material_constraints')}))
    print(json.dumps(r['per_rule_material_constraints']))
if __name__=='__main__':main()
