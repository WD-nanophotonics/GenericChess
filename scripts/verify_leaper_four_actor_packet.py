"""Portable data-only four-actor evidence reader; capsules are never executed."""
from pathlib import Path
from collections import Counter
from fractions import Fraction
import argparse,gzip,json,time
from math import isclose
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.verify_leaper_ab_learning_packet import read,no_time
from scripts.verify_leaper_ab_learning import verify_uniform_game,td_sum
from scripts.verify_leaper_frozen_learning import replay_query
from scripts.leaper_four_actor_history import run as history_run,clock_dp
from scripts.leaper_cooperative_certificate import encode_position
from scripts.leaper_cooperative_truth import cooperative_distances
from generic_chess.learning.incremental import FixedScaleSessionEnv
from generic_chess.core.actions import action_to_dict,action_from_dict

DEFAULT=Path('docs/research/data/leaper_four_actor_signal_20261024')
def rat(x):return Fraction(*x)
def pair(x):return[x.numerator,x.denominator]
def stable(value):return no_time(json.loads(json.dumps(value)))

def feature_credit(base,output):
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.core.attacks import anchor_square
    from generic_chess.learning.incremental import Model,_material_features
    from generic_chess.core.search_runtime import SearchPathRuntime
    cfg=L.load(base/'cost/plan.json');game=L.load(base/'cost/game-000.json');saved=L.load(base/'feature-credit/result.json')
    spec=L.load(base/'feature-credit/spec.json');c=L.compile_rule(L.ruleset_from_dict(cfg['world']['rule']))
    _,zero=L.material_profiles(c);e=Evaluator(c,zero,EvaluationConfig(dynamic_mobility_weight=1,anchor_escape_weight=1,promotion_potential_weight=0))
    def feature(state):
        attacks=e._attack_maps(state);a=len(attacks[0])-len(attacks[1])
        esc=e._anchor_escape(state.position,0,attacks[1])-e._anchor_escape(state.position,1,attacks[0])
        check=int(anchor_square(state.position,1,c)in attacks[0])-int(anchor_square(state.position,0,c)in attacks[1])
        if e.evaluate(state)*(1 if state.position.side_to_move==0 else-1)!=a+esc+10*check:raise ValueError('served dynamic basis differs')
        mat=_material_features(state.position,c,(('board','A'),('board','B'),('hand','A'),('hand','B')));count=mat[0]+mat[1]
        cc=state.repetition_counts if hasattr(state,'repetition_counts')else state._runtime.repetition_counts.items()
        return tuple(mat)+(a/25,esc/8,check,(64-state.ply_count)/64*count,max(n for _,n in cc)/4*count)
    projected=[];model=Model(spec['initial'])
    for event,expected in zip((x for x in game['events']if x['kind']=='candidate'),saved['features']):
        record=dict(game['final_record']);record['actions']=record['actions'][:event['ply']];s=restore(c,record);r=event['receipt']
        for choice in r['pv_choices']:s.submit(L.match_action(s,choice['action']))
        phi=None if r['pv_terminal']else feature(s.state)
        if (None if phi is None else list(phi))!=expected['PV_phi']or L.state_sha(s.state)!=expected['PV_state_sha256']:
            raise ValueError('counterfactual basis/source PV differs')
        if phi is not None and model.raw(phi)!=r['value']:raise ValueError('zero initialization changed retained target')
        projected.append(dict(r,pv_phi=phi))
    after,stats=td_sum(spec['initial'],projected,game['result']['outcome'])
    if any(not isclose(a,b,abs_tol=1e-14,rel_tol=1e-12)for a,b in zip(after,saved['after']))or stats!=saved['update']:
        raise ValueError('counterfactual TD credit differs')
    record=dict(game['final_record']);record['actions']=record['actions'][:50];s=restore(c,record);rt=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses);before=[]
    for action in L.deserialize_game_record(json.dumps(game['final_record'])).actions[50:]:
        if feature(s.state)!=feature(rt.state):raise ValueError('pinned runtime feature projection differs')
        before.append(feature(s.state));s.submit(action);rt.push(action)
    if feature(s.state)!=feature(rt.state):raise ValueError('terminal runtime count projection differs')
    for expected in reversed(before):rt.pop();assert feature(rt.state)==expected
    result=dict(verified=True,after=after,update=stats,bridge_pushes=len(before),bridge_balanced=rt.depth==0,
        new_Player_queries=0,new_experiential_episodes=0,oracle_targets=0,
        scope='Offline retained-PV arithmetic and pinned runtime projection only; failed feature-policy query staysUNKNOWN, no actual learned dynamic policy result.')
    write(output,result);return result

def bounds(base,graph,queries_file,tree_file,output):
    tick=time.perf_counter();spec=L.load(base/'uniform/spec.json');saved=L.load(base/'uniform/result.json')
    cfg=L.load(base/'cost/plan.json');game=L.load(base/'cost/game-000.json')
    if spec['world']!=cfg['world']or spec['source_cost_sha256']!=L.sha(base/'cost/game-000.json'):
        raise ValueError('Uniform original source differs')
    g=json.loads(gzip.decompress(graph.read_bytes()));qual=L.load(base/'graph/qualification.json')
    if spec['graph_sha256']!=L.sha(graph)or not qual['verified']or qual['sha256']!=L.sha(graph)or g['rule']!=spec['world']['rule']:
        raise ValueError('Uniform qualified graph differs')
    if saved['tree_sha256']!=L.sha(tree_file)or saved['queries_sha256']!=L.sha(queries_file):raise ValueError('Uniform retained bytes differ')
    c=L.compile_rule(L.ruleset_from_dict(g['rule']));index={(p[0],p[1]):i for i,p in enumerate(g['positions'])}
    distance,_=cooperative_distances(g['edges'],[int(i)for i,w in g['terminals'].items()if w==0])
    potential=[min(65,distance.get(i,65))for i in range(len(g['positions']))]
    if any(potential[int(i)]!=0 for i,w in g['terminals'].items()if w==0)or any(potential[i]>1+potential[j]for i,ee in enumerate(g['edges'])for j in ee):
        raise ValueError('cooperative no-WIN0 lower-distance potential invalid')
    tree=json.loads(gzip.decompress(tree_file.read_bytes()));nodes=tree['nodes']
    queries=[json.loads(line)for line in gzip.decompress(queries_file.read_bytes()).decode().splitlines()]
    byprefix={q['prefix']:q for q in queries}
    if len(byprefix)!=len(queries):raise ValueError('duplicate prefix query')
    original={e['state_sha256']:e['receipt']for e in game['events']if e['kind']=='candidate'}
    seen={};mass=[Fraction(0)]*len(nodes);mass[0]=Fraction(1);leaves=Counter();counts=Counter();extra=Counter();extra_mass=Counter()
    frontier={x['prefix']:rat(x['mass'])for x in tree['frontier']};unknown=Fraction(0)
    if len(frontier)!=len(tree['frontier']):raise ValueError('duplicate frontier prefix')
    start=spec['world']['roots'][0]['record'];depths=Counter();prefix_depths=Counter()
    for i,n in enumerate(nodes):
        if i==0:
            if n['parent']is not None:raise ValueError('bad prefix root')
        elif type(n['parent'])is not int or not 0<=n['parent']<i:raise ValueError('cyclic/future parent')
        aa=[];j=i
        while nodes[j]['parent']is not None:
            aa.append(nodes[j]['action']);j=nodes[j]['parent']
        record=dict(start);record['actions']=start['actions']+list(reversed(aa))
        s=restore(c,record);p=mass[i]
        if p<=0:raise ValueError('orphan prefix')
        prefix_depths[s.state.ply_count]+=1
        kind=n['kind']
        if kind is None:
            if i not in frontier or frontier[i]!=p or n.get('children'):raise ValueError('frontier mass/binding differs')
            # Newly derived data-only frontier classification, kept SEPARATE
            # from the original capped experiment and its frozen bounds.
            if s.state.terminal_status.is_terminal:
                bucket='WIN0'if s.result.winner==0 else'WIN1'if s.result.winner==1 else'DRAW'
                extra[bucket]+=1;extra_mass[bucket]+=p
            else:
                raw=encode_position(s.state.position,c.initial_position);ix=index[(raw[0],raw[1])]
                if potential[ix]>64-s.state.ply_count:extra['no_WIN0']+=1;extra_mass['no_WIN0']+=p
            continue
        counts['expanded_prefixes']+=1
        if n['state_sha256']!=L.state_sha(s.state)or n['ply']!=s.state.ply_count or rat(n['mass'])!=p:
            raise ValueError('actual full-history prefix differs')
        if kind.startswith('actual_'):
            actual='actual_WIN0'if s.result.winner==0 else'actual_WIN1'if s.result.winner==1 else'actual_DRAW'
            if not s.state.terminal_status.is_terminal or kind!=actual:raise ValueError('literal terminal mass false')
            leaves[kind]+=p;counts[kind]+=1
        elif kind=='no_cooperative_WIN0':
            raw=encode_position(s.state.position,c.initial_position);ix=index[(raw[0],raw[1])]
            if s.state.terminal_status.is_terminal or potential[ix]<=64-s.state.ply_count:raise ValueError('unproved zero-WIN0 mass')
            leaves[kind]+=p;counts[kind]+=1
        elif kind=='Uniform':
            if s.state.terminal_status.is_terminal or s.state.position.side_to_move!=1:raise ValueError('Uniform policy seat differs')
            legal=[action_to_dict(a.action)for a in FixedScaleSessionEnv(s,unit_type='A').actions()]
            children=n['children']
            if Counter(json.dumps(a,sort_keys=True)for a in legal)!=Counter(json.dumps(nodes[j]['action'],sort_keys=True)for j in children):
                raise ValueError('Uniform does not cover every legal action exactly')
            counts['Uniform_prefixes']+=1
            for j in children:
                if nodes[j]['parent']!=i or mass[j]:raise ValueError('prefix parent/duplicate mass differs')
                mass[j]=p/len(children)
        elif kind in('candidate','UNKNOWN_response'):
            q=byprefix[i];sha=L.state_sha(s.state);r=q['receipt']
            if q['state_sha256']!=sha or s.state.position.side_to_move!=0:raise ValueError('response actual state differs')
            if q['origin']=='actual':
                if not q['reused']or r!=original.get(sha):raise ValueError('reused original receipt differs')
                counts['reused_actual_receipts']+=1
            elif q['origin']=='tree':
                if not q['reused']or r!=seen.get(sha):raise ValueError('retained first response differs')
                counts['reused_tree_receipts']+=1
            else:
                if q['reused']or sha in seen:raise ValueError('new query retried a retained response')
                counts['new_Player_queries']+=1;counts['new_Player_nodes']+=r['nodes']
            usable=r['complete']and r['completed_depth']>=4 and r['action']is not None
            if not usable:
                if kind!='UNKNOWN_response'or n.get('children'):raise ValueError('unusable query advanced')
                unknown+=p;counts['UNKNOWN_responses']+=1
            else:
                seen[sha]=r
                if kind!='candidate'or len(n['children'])!=1:raise ValueError('complete response not a single child')
                action=L.match_action(s,r['action']['action']);counts['PV_plies']+=replay_query(s,[1,1,0,0],r,action_to_dict(action))
                depths[r['completed_depth']]+=1
                j=n['children'][0]
                if nodes[j]['parent']!=i or nodes[j]['action']!=action_to_dict(action)or mass[j]:raise ValueError('response child differs')
                mass[j]=p
        else:raise ValueError('unknown prefix classification')
        if i%5000==0:print('BOUND_READER',i,len(nodes),round(time.perf_counter()-tick,2),flush=True)
    if counts['expanded_prefixes']!=saved['counts']['expanded_prefixes']:raise ValueError('expanded prefix count differs')
    if len(queries)!=sum(counts[k]for k in('new_Player_queries','reused_actual_receipts','reused_tree_receipts')):raise ValueError('unused query evidence')
    for name in('Uniform_prefixes','new_Player_queries','new_Player_nodes','reused_actual_receipts','reused_tree_receipts','UNKNOWN_responses','actual_WIN0','actual_WIN1','actual_DRAW','no_cooperative_WIN0'):
        if counts[name]!=saved['counts'].get(name,0):raise ValueError('response work/count differs:'+name)
    pending=sum(frontier.values(),Fraction(0))+unknown
    lower=Fraction(leaves['actual_WIN0']);upper=lower+pending
    if sum(leaves.values(),Fraction(0))+pending!=1 or rat(saved['unresolved_mass'])!=pending or list(map(pair,(lower,upper)))!=saved['WIN0_bounds']:
        raise ValueError('exact rational probability bounds differ')
    if {k:pair(v)for k,v in leaves.items()}!=saved['leaf_mass']or unknown!=rat(tree['unresolved_response_mass']):
        raise ValueError('leaf/residual mass differs')
    refined_lower=lower+extra_mass['WIN0'];refined_upper=upper-extra_mass['WIN1']-extra_mass['DRAW']-extra_mass['no_WIN0']
    result=dict(verified=True,counts=dict(counts),prefixes=len(nodes),prefix_ply_histogram=dict(prefix_depths),completed_depths=dict(depths),
        original_frozen_WIN0_bounds=[pair(lower),pair(upper)],posthoc_frontier_counts=dict(extra),posthoc_frontier_mass={k:pair(v)for k,v in extra_mass.items()},
        posthoc_WIN0_bounds=[pair(refined_lower),pair(refined_upper)],seconds=time.perf_counter()-tick,
        scope='No Player or training calls. Every saved complete source prefix replayed through public GameSession, every literal PV and full Uniform legal frontier checked, exact Fraction mass conserved. Original capped-case bounds reproduced unchanged; separate posthoc queued-frontier terminal/distance inspection cannot select experience or become a completed policy law.')
    write(output,result);return result

def verify(directory,output):
    output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter();manifest,packet=read(directory,output)
    cfg=L.load(output/'cost/plan.json');row=L.load(output/'cost/game-000.json')
    copy=dict(row,slot=dict(root=cfg['root'],role=cfg['role'],seed=cfg['seed'],phase='train'))
    cost=verify_uniform_game(cfg['world'],copy)
    graph=directory/'domain.json.gz';qualification=output/'graph/qualification.json'
    clock=clock_dp(graph,qualification,cfg['world'],output/'clock-replay.json')
    if stable(clock)!=stable(L.load(output/'graph/clock.json')):raise ValueError('finite-clock evidence differs')
    actual=history_run(output/'cost',graph,qualification,output/'history-replay.json')
    if stable(actual)!=stable(L.load(output/'graph/trace-truth.json')):raise ValueError('actual history evidence differs')
    next_cfg=L.load(output/'next-role/plan.json');next_row=L.load(output/'next-role/game-000.json')
    next_cost=verify_uniform_game(next_cfg['world'],dict(next_row,slot=dict(root=next_cfg['root'],role=next_cfg['role'],seed=next_cfg['seed'],phase='train')))
    next_truth=history_run(output/'next-role',graph,qualification,output/'next-history-replay.json')
    if stable(next_truth)!=stable(L.load(output/'next-role/trace-truth.json')):raise ValueError('next original-role history differs')
    b=bounds(output,graph,directory/'uniform-queries.jsonl.gz',directory/'uniform-tree.json.gz',output/'bounds-replay.json')
    credit=feature_credit(output,output/'feature-credit-replay.json')
    deeper=L.load(output/'deeper/result.json');spec=L.load(output/'deeper/spec.json');s=restore(L.compile_rule(L.ruleset_from_dict(cfg['world']['rule'])),spec['record']);r=deeper['receipt']
    if deeper['complete']:replay_query(s,[1,1,0,0],r,action_to_dict(L.match_action(s,r['action']['action'])))
    tail=L.load(output/'tail/result.json')
    for case in tail['rows']:
        if not case['complete']and case['value']is not None:raise ValueError('capped explicit tree imputed')
        if case['complete']and case['value']!=case['rank_reduction_value']:raise ValueError('explicit tail result differs')
    if L.load(output/'feature-choice/failure.json')['status']!='UNKNOWN':raise ValueError('failed feature slot misreported')
    result=dict(verified=True,documents=len(packet['documents_utf8']),source_capsules=len(packet['source_capsules_utf8']),cost=cost,
        original_roots=[x['truth']['value']for x in actual['original_roots']],history=actual['counts'],next_role_cost=next_cost,next_role_history=next_truth['counts'],clock_horizons=len(clock['rows']),bounds=b,
        deeper_completed_depth=r['completed_depth'],deeper_chosen=deeper['chosen_truth'],tail_complete=sum(x['complete']for x in tail['rows']),
        feature_credit=credit,seconds=time.perf_counter()-tick,new_experimental_Player_queries=0,new_experiential_episodes=0,
        scope='Capsules hashed as data only. Full source Core qualification/explicit-tail/exhaustive-test receipts hash-bound, not rerun by default. Actual episode/RNG/PVs/TD, complete clock DP/history barriers and every response prefix/legal Uniform frontier/PV/exact probability bound independently replayed with public Core; no independent rules-engine or policy-gain claim.')
    write(output/'verification.json',result);print('FOUR_ACTOR_PACKET_PASS',result['seconds'],flush=True);return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=DEFAULT);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();verify(a.directory,a.output)

