"""Reproduce the portable trajectory/chance evidence from pinned JSON data.

One shared full-Core graph reconstruction supports the analyses. No saved
source capsule is executed, and no Player or learner update is issued. The
optional complete-history flag expands the 234 controllers without merging
positions; the default separately verifies their algebraic lower proofs.
"""
from pathlib import Path
import argparse,hashlib,json,time
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_twoa_graph import verify as graph_verify
from scripts.verify_leaper_twoa_safety import admission,SOURCE
from scripts.leaper_component_packet import read as primary_read
from scripts.leaper_twoa_trajectory_truth import census
from scripts.leaper_twoa_trajectory_capacity import analyze as capacity
from scripts.leaper_twoa_random_headroom import analyze as headroom,history_chance_gap
from scripts.leaper_twoa_chance_choices import analyze as choices,mechanisms
from scripts.verify_leaper_random_headroom import verify as lower_verify
from scripts.verify_leaper_chance_upper import verify as upper_verify
from scripts.verify_leaper_chance_bindings import verify as binding_verify
from scripts.verify_leaper_chance_histories import verify as actual_histories
from scripts.leaper_twoa_gradient_support import analyze as gradients,split_type_zero_crossing
from scripts.leaper_h6_opponent_objective import analyze as objective,compare_scalar_cells


def same(actual,saved,keys,label):
    normalize=lambda x:json.loads(json.dumps(x))
    for k in keys:
        if normalize(actual[k])!=normalize(saved[k]):raise ValueError(label+' scientific field differs: '+k)


def verify(directory,output,*,full_histories=False):
    tick=time.perf_counter();directory=Path(directory);output=Path(output);output.mkdir(parents=True,exist_ok=False)
    m=load(directory/'manifest.json')
    for name,sha in m['files_sha256'].items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest()!=sha:raise ValueError('payload hash differs: '+name)
    pp=Path('docs/research/data/leaper_component_policy_20261024');old=Path('docs/research/data/leaper_scope_and_headroom_20261024');h6=Path('docs/research/data/leaper_h6_initial_truth_20261023')
    if hashlib.sha256((pp/'packet.json.gz').read_bytes()).hexdigest()!=m['primary_packet_sha256']or hashlib.sha256((old/'twoa-graph.json.gz').read_bytes()).hexdigest()!=m['truth_packet_sha256']:raise ValueError('fixed source packet differs')
    primary=primary_read(pp/'packet.json.gz',pp/'manifest.json',output/'primary-qualification.json')
    packet=load(old/'twoa-graph.json.gz');source=load(SOURCE);c,_=admission(packet,source);qualified,graph=graph_verify(packet,source,return_graph=True)
    docs=load(pp/'packet.json.gz')['documents_utf8'];result=dict(payload_hashes=len(m['files_sha256']),primary=primary,graph=qualified,Player_queries=0,training_episodes=0,source_capsules_executed=False)
    a=census(pp/'packet.json.gz',pp/'manifest.json',old/'twoa-graph.json.gz',output/'trajectory',qualified_graph=(qualified,graph));same(a,load(directory/'trajectory-truth.json.gz'),['summary','events','rows','source_packet_sha256','truth_packet_sha256'],'trajectory');result['trajectory_summary']=a['summary']
    b=capacity(graph,c,docs,a,output/'capacity.json');same(b,load(directory/'capacity.json.gz'),['summary','rows','witnesses','positive_path_Core_plies','reverse_BFS_maps'],'capacity');result['capacity_summary']=b['summary']
    h=headroom(packet,graph,c,output/'headroom');same(h,load(directory/'headroom.json'),['rows','policies','upper'],'headroom');result['headroom']=h['rows']
    q=choices(graph,c,docs,a,output/'choice-bounds.json');same(q,load(directory/'choice-bounds.json.gz'),['summary','counts','rows','strict'],'chance choices');result['choice_summary']=q['summary']
    certs=load(directory/'choice-certificates.json.gz');lv=lower_verify(packet,certs,seconds=300);same(lv,load(directory/'choice-lower-qualification.json'),['counts','rows'],'lower proofs');result['lower_proofs']=lv
    result['headroom_lower']=lower_verify(packet,h)
    bv=binding_verify(c,docs,q,certs);same(bv,load(directory/'choice-bindings-qualification.json'),['strict_counts'],'source bindings');result['source_bindings']=bv
    u=upper_verify(graph,q,h,output/'upper-audit.json');same(u,load(directory/'upper-audit.json.gz'),['policy_summaries','strict','headroom_roots','max_interval_width'],'outward upper');result['outward_upper']={k:v for k,v in u.items()if k!='strict'}
    g=gradients(graph,c,docs,a);same(g,load(directory/'gradient-support.json'),list(g),'learner Jacobian');result['gradient']=g
    z=split_type_zero_crossing(h6);same(z,load(directory/'zero-crossing-gradient.json'),list(z),'zero crossing');result['zero_crossing']=z['counts']
    mech=mechanisms(c,docs,q);same(mech,load(directory/'choice-mechanisms.json'),list(mech),'retained mechanism');result['mechanism']={k:v for k,v in mech.items()if k!='strict_PV_rows'}
    barrier=load(directory/'history-barrier-chance.json');result['barrier_lower']=lower_verify(packet,barrier)
    gap=history_chance_gap(graph,c,load(old/'twoa-barrier-safety.json.gz'),load(old/'twoa-equalclock.json'),barrier)
    same(gap,load(directory/'history-chance-gap.json'),['root_ply','same_position','same_clock','WIN_history_optimal_uniform_value','DRAW_history_optimal_uniform_bounds','defender_draw_probability_lower','same_position_value_gap_lower','any_position_only_value_max_error_lower','safety_vertices'],'history chance');result['history_chance']=gap
    obj=objective(h6,old/'h6-policy-bounds.json.gz',output/'h6-objective.json');same(obj,load(directory/'h6-objective.json'),['rows','source_inputs_digest','source_truth_digest'],'A/B objective');result['h6_objective']=[{k:v for k,v in r.items()if k!='root_rows'}for r in obj['rows']]
    cells=compare_scalar_cells(h6,obj,output/'h6-scalar-cells.json');same(cells,load(directory/'h6-scalar-cells.json'),['rows'],'A/B cells');result['h6_cells']=cells['rows']
    actual=load(directory/'actual-history-qualification.json')
    if actual['controllers']!=234 or actual['counts']['actual_history_nodes']!=49254 or len(actual['rows'])!=234:raise ValueError('saved actual-history scope differs')
    if actual['rows']!=[{'root_state_sha':p['root_state_sha'],'lower':p['lower']}for r in(h,certs)for p in r['policies']]:raise ValueError('actual-history receipt roots differ')
    result['previous_actual_history_qualification']=actual
    if full_histories:
        fresh=actual_histories(packet,[h,certs],output/'actual-history-qualification.json')
        same(fresh,actual,['controllers','counts','rows'],'actual full-history trees');result['fresh_actual_history_qualification']=fresh
    result.update(verified=True,seconds=time.perf_counter()-tick,full_histories_reexecuted=full_histories)
    (output/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('PORTABLE_TRAJECTORY_CHANCE_PASS',result['seconds']);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--full-histories',action='store_true');a=p.parse_args();verify(a.directory,a.output,full_histories=a.full_histories)
