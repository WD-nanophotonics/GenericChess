"""Portable scientific reader; source capsules are hashed, never executed.

Default replays every new actual learning record/RNG/PV and TD update, finite
rank diagnostics and posthoc exposure. Already executed complete static graph
qualifications are hash-bound. --full-domains repeats those expensive Core
frontiers under each declared target rule/owner mapping, without new games.
"""
from pathlib import Path,PurePosixPath
from copy import copy
from collections import Counter
import argparse,gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,source_documents,write
from scripts.verify_leaper_ab_learning import verify,verify_uniform,verify_game
from scripts.verify_leaper_ab_rank_diagnostics import verify as verify_rank
from scripts.verify_leaper_ab_deadzone import verify as verify_domain
from scripts.leaper_ab_learning_truth import run as truth_run,tables,classify
from scripts.leaper_ab_rank_diagnostics import load_graph
from scripts.verify_leaper_frozen_learning import replay_query
from generic_chess.learning.incremental import Model
from generic_chess.core.actions import action_to_dict

DEFAULT=Path('docs/research/data/leaper_ab_learning_and_rank_20261024')


def no_time(value):
    if isinstance(value,dict):return{k:no_time(v)for k,v in value.items()if k!='seconds'}
    if isinstance(value,(list,tuple)):return[no_time(v)for v in value]
    return value


def read(directory,output):
    m=json.loads((directory/'manifest.json').read_bytes());raw=(directory/'evidence.json.gz').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=m['packet_sha256']:raise ValueError('packet hash differs')
    decoded=gzip.decompress(raw)
    if hashlib.sha256(decoded).hexdigest()!=m['decoded_sha256']:raise ValueError('decoded packet hash differs')
    packet=json.loads(decoded)
    for group in('documents_utf8','source_capsules_utf8'):
        if set(packet[group])!=set(m[group]):raise ValueError('document coverage differs')
        for name,text in packet[group].items():
            payload=text.encode('utf8');expected=m[group][name]
            if len(payload)!=expected['bytes']or hashlib.sha256(payload).hexdigest()!=expected['sha256']:raise ValueError('document bytes differ:'+name)
            if group=='documents_utf8':
                rel=PurePosixPath(name)
                if rel.is_absolute()or'..'in rel.parts or'\\'in name:raise ValueError('unsafe evidence path')
                path=output.joinpath(*rel.parts);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payload)
    for name,expected in m['external_files'].items():
        if PurePosixPath(name).is_absolute()or'..'in PurePosixPath(name).parts:raise ValueError('unsafe external path')
        if L.sha(directory/name)!=expected['sha256']:raise ValueError('external evidence hash differs:'+name)
    for plan,source in m['producer_bindings'].items():
        if json.loads(packet['documents_utf8'][plan])['producer_sha256']!=m['source_capsules_utf8'][source]['sha256']:raise ValueError('executed producer binding differs:'+plan)
    return m,packet


def clock_dp(graph,saved):
    g=json.loads(gzip.decompress(graph.read_bytes()));ts={int(k):v for k,v in g['terminals'].items()};vs={int(k):v for k,v in g['relative_values'].items()};rs={int(k):v for k,v in g['ranks'].items()};edges=g['edges'];sides=[p[0]for p in g['positions']];n=len(edges)
    if set(ts.values())!={None,0}:raise ValueError('single winning seat premise differs')
    values=[int(ts.get(i,-1)==0)for i in range(n)]
    for h,row in enumerate(saved['rows']):
        if row['H']!=h or values!=[int(vs[i]!=0 and rs[i]<=h)for i in range(n)]:raise ValueError('finite clock/rank relation differs')
        if row['digest']!=hashlib.sha256(bytes(values)).hexdigest()or row['WIN']!=sum(values):raise ValueError('clock DP receipt differs')
        if h+1<len(saved['rows']):values=[int(ts[i]==0)if i in ts else max(values[j]for j in ee)if sides[i]==0 else min(values[j]for j in ee)for i,ee in enumerate(edges)]
    if len(saved['rows'])!=max(rs.values())+1 or saved['graph_sha256']!=L.sha(graph):raise ValueError('clock DP coverage/binding differs')
    return dict(vertices=n,horizons=len(saved['rows']),fixed_point=max(rs.values()))


def natural_case(base,graphs):
    p=base/'natural';spec=json.loads((p/'spec.json').read_bytes());results=json.loads((p/'result.json').read_bytes());g,c,ix,vs,rs=load_graph(graphs/'domain-0.json.gz');s=restore(c,spec['source']['record']);slot=spec['source']['source_slot'];source=json.loads((base/'uniform'/f"game-{slot['id']:03d}.json").read_bytes())
    expected=dict(source['final_record']);expected['actions']=expected['actions'][:len(spec['source']['record']['actions'])]
    if expected!=spec['source']['record']or L.state_sha(s.state)!=spec['source']['state_sha256']:raise ValueError('natural diagnostic is not the retained actual prefix')
    lookup,keys,_=tables('contact',c,{0:g},[(0,False,graphs/'domain-0.json.gz',base/'proofs/domain-0-verification.json')]);counts=Counter()
    root_value,_=classify(s,c,lookup,keys)
    if root_value!=spec['source']['root_value']:raise ValueError('natural root truth differs')
    for row in results['rows']:
        r=row['receipt'];action=L.match_action(s,r['action']['action']);counts['PV_plies']+=replay_query(s,spec['weights'][row['arm']],r,action_to_dict(action));ch=copy(s);ch.submit(action)
        if classify(ch,c,lookup,keys)[0]!=row['chosen_value']:raise ValueError('natural chosen WDL differs')
        counts['queries']+=1;counts['nodes']+=r['nodes']
    reference=json.loads((p/'reference-result.json').read_bytes())
    for row in reference['rows']:
        if not row['complete']or row['terminal']or row['value']!=Model(spec['weights'][row['arm']]).raw(row['phi']):raise ValueError('reference score/feature claim differs')
    return dict(counts),len(reference['rows'])


def verify_packet(directory,output,*,full_domains=False):
    output.mkdir(parents=True,exist_ok=False);began=time.perf_counter();m,packet=read(directory,output);get=lambda name:json.loads((output/name).read_bytes());upstream=source_documents()
    worlds={g:json.loads(upstream[g+'/inputs.json'])for g in('two-type','contact')}
    for name in('unit','uniform'):
        if get(name+'/plan.json')['worlds']!=worlds:raise ValueError('original unfiltered input law changed')
    if get('initial/plan.json')['world']!=worlds['contact']or get('boundary/plan.json')['world']!=worlds['contact']:raise ValueError('control input rule changed')
    old=verify(output/'unit',output/'initial',output/'old-learning-replay.json')
    if no_time(old)!=no_time(get('derived/learning-verification.json')):raise ValueError('old learning reproduction differs')
    uniform=verify_uniform(output/'uniform',output/'uniform-learning-replay.json')
    if no_time(uniform)!=no_time(get('derived/uniform-verification.json')):raise ValueError('Uniform learning reproduction differs')
    boundary=[verify_game(worlds['contact'],json.loads(p.read_bytes()))for p in sorted((output/'boundary').glob('game-*.json'))]
    if boundary!=get('derived/boundary-verification.json')['rows']:raise ValueError('boundary replay differs')
    graph0=directory/'domain-0.json.gz';rank=verify_rank(graph0,output/'rank',output/'proofs/domain-0-verification.json',output/'rank-replay.json')
    if no_time(rank)!=no_time(get('derived/rank-panel-verification.json')):raise ValueError('rank diagnostic reproduction differs')
    clock=clock_dp(graph0,get('proofs/clock-rank-dp.json'))
    actual_truth=truth_run(output/'uniform',directory,output/'proofs',output/'truth-replay.json')
    if no_time(actual_truth)!=no_time(get('derived/uniform-truth.json')):raise ValueError('natural truth/exposure reproduction differs')
    natural,reference=natural_case(output,directory)
    suffix=get('suffix/result.json');literal=get('proofs/session-suffix.json')
    if suffix['status']!='COMPLETE'or literal['status']!='COMPLETE'or len(suffix['rows'])!=12 or literal['counts']['nodes']!=suffix['nodes']+12 or literal['counts'].get('terminal_checkmate',0):raise ValueError('complete suffix qualification differs')
    if any(not r['complete']or r['wdl_player0']!=0 or any(b['terminal_outcomes_player0']!=[0]for b in r['branches'])for r in suffix['rows']):raise ValueError('suffix outcome claim differs')
    full=[]
    if full_domains:
        for group in('contact','two-type'):
            for domain in range(3):full.append(verify_domain(directory/f'domain-{domain}.json.gz',output/f'full-{group}-{domain}.json',target_group=group))
            full.append(verify_domain(graph0,output/f'full-{group}-swap.json',target_group=group,swap_owners=True))
    summary=json.loads((directory/'summary.json').read_bytes())
    if summary['experiments']['Uniform_final_models']!=uniform['models']or summary['experiments']['Uniform_pairs']!=len(uniform['paired'])or summary['natural_truth_distinct']!=actual_truth['distinct_actual_contexts']:raise ValueError('public summary differs from replay')
    if any(r['utility']!=0 for r in uniform['rows']):raise ValueError('all-draw finite result claim differs')
    result=dict(verified=True,packet_sha256=m['packet_sha256'],documents=len(packet['documents_utf8']),source_capsules=len(packet['source_capsules_utf8']),learning_episodes=404,Uniform=uniform['counts'],old_learning=old['counts'],boundary=boundary,rank=rank['counts'],clock=clock,natural=natural,reference_score_receipts=reference,full_static_domain_passes=len(full),seconds=time.perf_counter()-began,
        new_experimental_Player_queries=0,new_training_episodes=0,
        scope='Default fresh actual records/RNG/PVs/TD sums, all natural posthoc rank/history classifications and finite clock DP; complete static Core qualifications and full suffix-tree receipts hash-bound, not reexecuted by default. Reference minimax scores are retained complete producer/library receipts with source, not independently rerun here. --full-domains separately reexecutes all8declared static Core target/owner passes. Capsules never executed.')
    write(output/'verification.json',result);print('AB_PACKET_PASS',result['documents'],'episodes404','seconds',result['seconds'],flush=True);return result


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=DEFAULT);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--full-domains',action='store_true');a=ap.parse_args();verify_packet(a.directory,a.output,full_domains=a.full_domains)
