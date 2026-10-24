"""Portable data-only reader of the bounded deeper-target study.

Never executes source capsules or experimental Players. Existing graph and
clock truth are dependencies of the preceding, committed A/B evidence packet.
"""
from pathlib import Path,PurePosixPath
import argparse,gzip,json,hashlib,time
from scripts.leaper_ab_learner_exposure import write
from scripts.verify_leaper_ab_learning_packet import read as read_previous
from scripts.verify_leaper_ab_deeper_targets import verify as verify_deeper
from scripts.verify_leaper_ab_barrier_strategy import verify as verify_strategy
from scripts.verify_leaper_ab_barrier_choice import verify as verify_choice

DEFAULT=Path('docs/research/data/leaper_ab_depth_targets_20261024')
PREVIOUS=Path('docs/research/data/leaper_ab_learning_and_rank_20261024')


def sha(data):return hashlib.sha256(data).hexdigest()


def read(directory,output):
    m=json.loads((directory/'manifest.json').read_bytes());raw=(directory/'evidence.json.gz').read_bytes();assert sha(raw)==m['packet_sha256']
    decoded=gzip.decompress(raw);assert sha(decoded)==m['decoded_sha256'];packet=json.loads(decoded)
    for group in('documents_utf8','source_capsules_utf8'):
        assert set(packet[group])==set(m[group])
        for name,text in packet[group].items():
            rel=PurePosixPath(name);assert not rel.is_absolute()and'..'not in rel.parts and'\\'not in name
            b=text.encode('utf8');assert sha(b)==m[group][name]['sha256']and len(b)==m[group][name]['bytes']
            if group=='documents_utf8':
                path=output.joinpath(*rel.parts);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
    for name,item in m.get('external_files',{}).items():
        rel=PurePosixPath(name);assert not rel.is_absolute()and'..'not in rel.parts
        assert sha((directory/name).read_bytes())==item['sha256']
    for plan,source in m['producer_bindings'].items():assert json.loads(packet['documents_utf8'][plan])['producer_sha256']==m['source_capsules_utf8'][source]['sha256']
    return m,packet


def stable(x):
    if isinstance(x,dict):return{str(k):stable(v)for k,v in x.items()if k!='seconds'}
    if isinstance(x,(tuple,list)):return[stable(v)for v in x]
    return x


def verify(directory,output,*,full_odd=False):
    output.mkdir(parents=True,exist_ok=False);tick=time.perf_counter();m,p=read(directory,output)
    previous_manifest=(PREVIOUS/'manifest.json').read_bytes();assert sha(previous_manifest)==m['previous_manifest_sha256']
    _,old=read_previous(PREVIOUS,output/'previous')
    cost=verify_deeper(output/'cost',output/'cost-replay.json');panel=verify_deeper(output/'panel',output/'panel-replay.json');win_control=verify_deeper(output/'win-control',output/'win-control-replay.json')
    for name,actual in [('cost',cost),('panel',panel),('win-control',win_control)]:
        expected=json.loads((output/f'checks/{name}-verification.json').read_bytes());assert stable(actual)==stable(expected)
    strategy=verify_strategy(output/'barrier',output/'strategy-replay.json')
    assert stable(strategy)==stable(json.loads((output/'checks/barrier-strategy-verification.json').read_bytes()))
    spec=json.loads((output/'barrier/spec.json').read_bytes());oldrow=json.loads(old['documents_utf8']['uniform/game-049.json']);expected=dict(oldrow['final_record']);expected['actions']=expected['actions'][:36]
    assert expected==spec['record']
    win_cfg=json.loads((output/'win-control/plan.json').read_bytes());observed=json.loads((output/'panel/game-028.json').read_bytes());control=json.loads((output/'win-control/game-000.json').read_bytes())
    assert win_cfg['reference_game_sha256']==sha((output/'panel/game-028.json').read_bytes())
    assert observed['utility']==1 and observed['slot']==win_cfg['reference_slot']and observed['before']==win_cfg['reference_before']
    assert all(observed['slot'][k]==control['slot'][k]for k in('group','root','role','seed','depth'))
    reference=json.loads((output/'win-reference/result.json').read_bytes());reference_plan=json.loads((output/'win-reference/plan.json').read_bytes())
    from generic_chess.learning.incremental import Model
    assert len(reference['rows'])==4 and reference['attempted_queries']==4 and reference['unretained_queries']==1
    assert reference['rows'][0]['status']=='UNRETAINED_UNKNOWN'and reference['rows'][0]['receipt']is None
    for row in reference['rows'][1:]:
        r=row['receipt'];assert row['status']=='RETAINED'and r['complete']and not r['pv_terminal']
        assert r['value']==Model(reference_plan['weights'][row['arm']]).raw(r['pv_phi'])
    choice=verify_choice(output/'barrier-choice',output/'choice-replay.json')
    assert stable(choice)==stable(json.loads((output/'checks/barrier-choice-verification.json').read_bytes()))
    from scripts.leaper_ab_learning_truth import run as truth
    actual=truth(output/'panel',PREVIOUS,output/'previous/proofs',output/'truth-replay.json')
    assert stable(actual)==stable(json.loads((output/'checks/panel-truth.json').read_bytes()))
    from scripts.leaper_ab_next_input_features import run as next_features
    next_input=next_features(output/'next-input-replay.json')
    assert stable(next_input)==stable(json.loads((output/'checks/next-input-features.json').read_bytes()))
    from scripts.leaper_ab_material_cells import run as material_cells
    cells=material_cells(output/'panel',output/'material-cells-replay.json')
    assert stable(cells)==stable(json.loads((output/'checks/material-cells.json').read_bytes()))
    from scripts.leaper_ab_odd_truth import clock_proof,run as odd_truth
    graph=directory/'odd-domain.json.gz'
    odd_clock=clock_proof(graph,output/'odd-clock-replay.json')
    assert stable(odd_clock)==stable(json.loads((output/'odd/clock-proof.json').read_bytes()))
    odd=odd_truth(output/'panel',graph,output/'odd/qualification.json',output/'odd/swapped-qualification.json',output/'odd/clock-proof.json',output/'odd-truth-replay.json')
    assert stable(odd)==stable(json.loads((output/'checks/panel-odd-truth.json').read_bytes()))
    if full_odd:
        from scripts.verify_leaper_ab_deadzone import verify as domain_verify
        domain_verify(graph,output/'fresh-odd-frontiers.json',source_group='two-type',target_group='two-type')
        domain_verify(graph,output/'fresh-swapped-odd-frontiers.json',source_group='two-type',target_group='two-type',swap_owners=True)
    out=dict(verified=True,packet_sha256=m['packet_sha256'],documents=len(p['documents_utf8']),data_only_capsules=len(p['source_capsules_utf8']),cost_episodes=len(cost['rows']),panel_episodes=len(panel['rows']),panel_counts=panel['counts'],barrier_strategy_positions=strategy['strategy_positions'],barrier_choice_queries=choice['queries'],seconds=time.perf_counter()-tick,new_experimental_Player_queries=0,new_training_episodes=0,
        scope='Actual histories/RNG/PVs/TD sequence; complete selected strategy frontier/identity/root clock; bounded diagnostic PVs; new odd clock DP/posthoc truth and prior hash-bound complete graph qualifications. Static full odd frontiers hash-bound by default; --full-odd reexecutes both actual owner passes. No independent rules engine, new Player or capsule execution. Capped20k historytree remains UNKNOWN.')
    out['full_odd_frontier_passes']=2 if full_odd else 0
    out['posthoc_win_control_episodes']=len(win_control['rows'])
    out['posthoc_win_control_same_record']=observed['final_record']==control['final_record']
    out['retained_reference_queries']=3
    out['unretained_reference_queries_UNKNOWN']=1
    out['odd_newly_qualified_occurrences']=sum(r['counts'].get('newly_qualified_root_occurrences',0)for r in odd['rows'])
    write(output/'verification.json',out);print(out,flush=True);return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,default=DEFAULT);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--full-odd',action='store_true')
    a=ap.parse_args();verify(a.directory,a.output,full_odd=a.full_odd)
