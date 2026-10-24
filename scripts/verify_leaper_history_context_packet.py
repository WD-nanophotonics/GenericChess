"""Portable history-structure evidence reader; capsules are DATA only."""
from pathlib import Path
from collections import Counter
from copy import copy
from fractions import Fraction as F
import argparse,gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load,digest
from scripts.verify_leaper_ab_learning_packet import read
from scripts.leaper_history_edit_context import census
from scripts.verify_leaper_history_edit_context import verify as literal_contexts
from scripts.verify_leaper_history_edit_sessions import verify as literal_sessions
from scripts.leaper_future_history_cone import analyze,first_hit_prior
from scripts.leaper_history_suffix_partition import run as suffix_partition
from scripts.leaper_history_action_necessity import run as action_necessity
from scripts.leaper_four_actor_history import admit_world
from scripts.leaper_first_repetition_flow import min_first_repetition
from scripts.leaper_repetition_cycle_baseline import repeated_single_cycle
from scripts.leaper_cooperative_certificate import encode_position,decode_position
from scripts.leaper_ab_learner_exposure import restore
from scripts.leaper_microgames import ExactTree
from scripts.verify_leaper_history_action_law import verify as literal_action_law
from scripts.research_record import record_value
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.session.serialization import deserialize_game_record

DEFAULT=Path('docs/research/data/leaper_history_context_20261024')

def stable(value):
    # Producer byte hashes remain independently bound to their actual capsules.
    # Replaying maintained code may add methods/CLI; compare scientific values,
    # never replace historical execution provenance with the current module hash.
    ignored={'seconds','source_sha256','producer_sha256','source_capsule_sha256','cone_preparation_seconds'}
    if isinstance(value,dict):return{k:stable(v)for k,v in value.items()if k not in ignored and not k.endswith('_seconds')}
    if isinstance(value,(list,tuple)):return[stable(v)for v in value]
    return value

def same(actual,expected,label):
    if stable(json.loads(json.dumps(actual)))!=stable(expected):raise ValueError('scientific replay differs:'+label)


def check_action_witnesses(packet):
    inputs=load(Path('docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz'));totals=Counter()
    for row in packet['rows']:
        family=next(f for f in inputs['families']if f['family']==row['family'])
        from scripts.leaper_h6_initial_truth import admit
        c=admit(family,next(r for r in inputs['rows']if r['family']==family['family']))
        current=None;intersection=None
        for h in row['histories']:
            s=restore(c,h['full_record'])
            if current is not None and current!=s.state.position:raise ValueError('action witnesses are not samePosition')
            current=s.state.position;tree=ExactTree(c,max_states=100000,seconds=30);v=tree.solve(s.state)
            if v!=h['value']:raise ValueError('action witness WDL differs')
            by_action={json.dumps(action_to_dict(a),sort_keys=True):tree.values[ch]for a,ch in tree.edges[s.state]}
            raw=s.legal_actions();vv=[by_action[json.dumps(action_to_dict(a),sort_keys=True)]for a in raw];best={i for i,x in enumerate(vv)if x==v}
            if [dict(action=action_to_dict(a),WDL=vv[i])for i,a in enumerate(raw)]!=h['actions']or sorted(best)!=h['optimal_offsets']:raise ValueError('literal action-quality frontier differs')
            intersection=best if intersection is None else intersection&best;totals['histories']+=1;totals['literal_nodes']+=len(tree.values)
        if intersection:raise ValueError('incompatible action witness is compatible')
        totals['incompatible_groups']+=1
    if dict(totals)!=packet['counts']:raise ValueError('action witness coverage differs')
    return dict(totals)


def check_actual_flow(base,source_directory):
    saved=load(base/'flow/result.json');cheap=load(base/'flow/baseline.json');old=load(base/'old/cost/game-000.json');cfg=load(base/'old/cost/plan.json');qualified=load(base/'old/graph/qualification.json')
    if cheap['source_flow_digest']!=digest(saved):raise ValueError('cycle baseline source binding differs')
    domain=source_directory/'domain.json.gz'
    if L.sha(domain)!=saved['spec']['graph_sha256']or qualified['sha256']!=L.sha(domain):raise ValueError('actual graph qualification differs')
    if L.sha(base/'old/cost/game-000.json')!=saved['spec']['source_game_sha256']:raise ValueError('actual original-game bytes differ')
    expected=dict(old['final_record']);expected['actions']=expected['actions'][:50]
    if expected!=saved['source_record']:raise ValueError('not the fixed original ply50 history')
    truth=next(x['root']for x in load(base/'old/graph/trace-truth.json')['queries']if x['ply']==50)
    if truth!=saved['prior_truth']:raise ValueError('prior WIN truth was altered')
    c=admit_world(cfg['world']);g=json.loads(gzip.decompress(domain.read_bytes()))
    if g['rule']!=cfg['world']['rule']or g['rule']!=saved['spec']['rule']:raise ValueError('full rule differs')
    chosen=[i for i,p in enumerate(g['positions'])if '6'not in p[1]and '3'not in p[1]];ix={i:j for j,i in enumerate(chosen)}
    if len(chosen)!=18936 or any(j not in ix for i in chosen for j in g['edges'][i]):raise ValueError('closed B-free future differs')
    edges=[[ix[j]for j in g['edges'][i]]for i in chosen];ts={ix[int(i)]:w for i,w in g['terminals'].items()if int(i)in ix};encoded={tuple(g['positions'][i]):ix[i]for i in chosen}
    initial=dict(saved['source_record'],actions=[]);s=restore(c,initial);wire={}
    def remember():wire[repetition_identity_key(s.state.position,c)]=encoded.get(tuple(encode_position(s.state.position,c.initial_position)))
    remember()
    for a in deserialize_game_record(json.dumps(saved['source_record'])).actions:s.submit(a);remember()
    cc=[0]*len(chosen);discarded=[]
    for key,n in s.state.repetition_counts:
        if wire[key]is None:discarded.append(dict(key=key,count=n))
        else:cc[wire[key]]=n
    if discarded!=saved['discarded_unreachable_prior']:raise ValueError('discarded past differs')
    target=encoded[tuple(encode_position(s.state.position,c.initial_position))]
    answer=min_first_repetition(edges,ts,target,cc,4,target,witness=True)
    if answer!=saved['flow']:raise ValueError('flow path/cost differs')
    candidate=repeated_single_cycle(edges,ts,target,cc,4)
    if candidate!=cheap['same_case']['baseline']:raise ValueError('cheap cycle path differs')
    for raw,record,states in((saved['literal_actions'],saved['final_record'],saved['literal_states']),(cheap['same_case']['literal_actions'],cheap['same_case']['final_record'],None)):
        z=restore(c,saved['source_record'])
        for i,a in enumerate(raw):
            if z.result.status.value!='ongoing':raise ValueError('firstrepeat witness stopped early')
            z.submit(L.match_action(z,a))
            if states is not None and (z.state.ply_count!=states[i]['ply']or record_value(z.state)!=states[i]['state']or record_value(z.result)!=states[i]['terminal']):raise ValueError('literal flow state differs')
        if record_value(z.to_record())!=record or z.result.status.value!='repetition'or z.state.ply_count!=62:raise ValueError('actual repetition certificate differs')
    if answer['distance']!=saved['cycle_lower_bound']or answer['distance']!=12 or cc[target]!=1:raise ValueError('independent12ply lower bound differs')
    abstract=cheap['abstract_separator'];ae=abstract['edges'];prefix=abstract['prefix'];counts=abstract['counts']
    if any(b not in ae[a]for a,b in zip(prefix,prefix[1:]))or counts!=[prefix.count(i)for i in range(len(ae))]or max(counts)>=4:raise ValueError('abstract incoming prefix differs')
    if repeated_single_cycle(ae,{},0,counts,4)is not None or min_first_repetition(ae,{},0,counts,4,0,witness=True)!=abstract['flow']:raise ValueError('abstract separator differs')
    return dict(actual_cases=1,literal_replayed_plies=24,distance=12,prior_WIN_unchanged=True,cheap_baseline_same_result=True)

def check_consumer_boundary(saved):
    source=load(Path('docs/research/data/leaper_h6_initial_truth_20261023/inputs.json.gz'))
    family=next(f for f in source['families']if f.get('fingerprint')==saved['fingerprint'])
    if saved['rule']!=family['rule']:raise ValueError('consumer-boundary full rule differs')
    from scripts.leaper_h6_initial_truth import admit
    c=admit(family,next(r for r in source['rows']if r['family']==family['family']))
    domain=load(Path('docs/research/data/leaper_h6_initial_truth_20261023')/f"domain{family['family']}.json.gz")
    if digest(domain)!=saved['source_domain_digest']:raise ValueError('consumer source domain differs')
    positions=[decode_position(p,c.initial_position)for p in domain['positions']]
    if domain['positions'][saved['past_vertex']]!=saved['past_position']:raise ValueError('forgotten past Position annotation differs')
    indices={p:i for i,p in enumerate(positions)};keys={repetition_identity_key(p,c):i for i,p in enumerate(positions)}
    if repetition_identity_key(positions[saved['past_vertex']],c)!=saved['past_repetition_key']:raise ValueError('forgotten feature key differs')
    signatures=[];scores=[];nodes=0;physical=None
    for row in saved['rows']:
        s=restore(c,row['record']);i=indices[s.state.position];h=6-s.state.ply_count
        if record_value(s.state.position)!=row['current_position']:raise ValueError('consumer current Position annotation differs')
        if physical is not None and physical!=s.state.position:raise ValueError('consumer pair not same Position')
        physical=s.state.position
        prior=sum(1<<keys[k]for k,n in s.state.repetition_counts if keys[k]!=i)
        frontier=first_hit_prior(domain['edges'],{int(k):v for k,v in domain['terminals'].items()},i,h,prior)
        if hex(frontier)!=row['first_hit_prior']or h!=row['remaining']:raise ValueError('consumer first-hit coordinate differs')
        tree=ExactTree(c,max_states=100000,seconds=30);v=tree.solve(s.state);memo={}
        def signature(state):
            if state in memo:return memo[state]
            term=state.terminal_status
            value=(tuple(encode_position(state.position,c.initial_position)),6-state.ply_count,term.status.value,term.winner,
                tuple((json.dumps(action_to_dict(a),sort_keys=True),signature(ch))for a,ch in tree.edges[state]))
            memo[state]=value;return value
        signatures.append(signature(s.state));features=[]
        for action in s.legal_actions():
            ch=copy(s);ch.submit(action)
            if ch.result.status.value!='ongoing':raise ValueError('consumer D1 leaf is terminal')
            features.append(dict(action=action_to_dict(action),history_feature=dict(ch.state.repetition_counts).get(saved['past_repetition_key'],0)))
        score=(max if s.state.position.side_to_move==0 else min)(x['history_feature']for x in features)
        if features!=row['child_features']or score!=row['hypothetical_D1_score']or v!=row['exact_WDL']or len(tree.values)!=row['literal_tree_nodes']:raise ValueError('consumer counterexample differs')
        scores.append(score);nodes+=len(tree.values)
    if len(signatures)!=2 or signatures[0]!=signatures[1]or scores[0]==scores[1]:raise ValueError('no consumer-factorization counterexample')
    return dict(histories=2,literal_nodes=nodes,game_suffix_equal=True,hypothetical_heuristic_differs=True,production_defect_claim=False)


def verify(directory,output):
    tick=time.perf_counter();output=Path(output);output.mkdir(parents=True,exist_ok=False);manifest,packet=read(directory,output)
    for parent,sha in manifest['parent_sources'].items():
        if parent.startswith('/')or'..'in Path(parent).parts or L.sha(Path(parent))!=sha:raise ValueError('parent source differs:'+parent)
    for binding in manifest['source_bindings']:
        obj=json.loads(packet['documents_utf8'][binding['document']])
        for field in binding['fields']:obj=obj[field]
        if obj!=manifest['source_capsules_utf8'][binding['capsule']]['sha256']:raise ValueError('actual executed source binding differs')
    old_directory=Path('docs/research/data/leaper_four_actor_signal_20261024');read(old_directory,output/'old')
    new=census(output/'replay-census');same(new,load(output/'context/census.json'),'context census')
    literal=literal_contexts(output/'context/census.json',output/'replay-literal.json');same(literal,load(output/'context/literal.json'),'literal histories')
    sessions=literal_sessions(output/'context/census.json',output/'replay-sessions.json')
    # Original independent Session receipt bound the identical class frontier
    # before witness-extraction-only v2; only the census document digest changed.
    expected=load(output/'context/sessions.json');expected['census_digest']=digest(load(output/'context/census.json'));same(sessions,expected,'Session context census')
    cone=analyze(output/'replay-cone');same(cone,load(output/'cone/result.json'),'cone values and full Uniform laws')
    partition=suffix_partition(output/'replay-partition.json');same(partition,load(output/'cone/first-hit-partition.json'),'actual suffix partition')
    action=action_necessity(output/'replay-actions.json');same(action,load(output/'action/result.json'),'fixed incoming action-necessity bounds')
    covers=action_necessity(output/'replay-action-covers.json',with_covers=True);same(covers,load(output/'action/covers.json'),'minimum action covers')
    action_literal=check_action_witnesses(load(output/'action/literal.json'))
    action_law=literal_action_law(load(output/'action/covers.json'),output/'replay-action-law.json')
    same(action_law,load(output/'action/covers-literal.json'),'full-GameState incoming action laws and minimum covers')
    flow=check_actual_flow(output,old_directory)
    consumer=check_consumer_boundary(load(output/'consumer/actual.json'))
    result=dict(verified=True,documents=len(packet['documents_utf8']),data_only_source_capsules=len(packet['source_capsules_utf8']),
        context_classes=new['counts']['contexts'],actual_H6_classes=partition['counts']['contexts'],ongoing_keys=partition['counts']['ongoing_full_keys'],
        first_hit_ongoing_keys=partition['counts']['ongoing_first_hit_keys'],action_witnesses=action_literal,actual_flow=flow,consumer_boundary=consumer,
        seconds=time.perf_counter()-tick,new_experimental_Player_queries=0,new_experiential_episodes=0,source_capsule_executions=0,
        scope='All new actual common-prefix classes, literal witnesses, finite suffix partition, exact fixed incoming action bounds and ONEactualq4repeat certificate replay. Abstract exhaustive-control receipts/capsules and original full-Core qualification remain hash-bound, not reexecuted by this default reader. SharedCore, not an independent rules engine or policy-gain claim.')
    (output/'verification.json').write_text(json.dumps(result,indent=2));print(result);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,default=DEFAULT);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.directory,a.output)
