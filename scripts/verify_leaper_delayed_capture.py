"""Data-only public qualification of delayed-capture/corner/entry evidence.

Source capsules are UTF8 strings: hash only, never import, unpack or execute.
"""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import argparse,gzip,hashlib,json,time
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import verify_measurements,nodes,snapshot,replay
from scripts.leaper_history_structural_witness import verify as verify_history
from scripts.leaper_corner_capacity_law import qualify as qualify_corner,d4
from scripts.leaper_mate_entry_witness import qualify as qualify_entry,qualify_parity_boundary
from scripts.leaper_entry_initialization_law import qualify as qualify_mu,mu_count,brute_mu
from scripts.leaper_entry_channels import qualify as qualify_channels,symmetry_analysis,qualify_obstruction
from scripts.leaper_named_mu_bridge import qualify as qualify_named
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from scripts.leaper_rule_coordinates import physical_action
from tools.local_agent.common import write_json


def load(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw)if path.suffix=='.gz'else raw)



def compile_scoped(raw,n,a,b,has_B=True):
    rule=L.ruleset_from_dict(raw)
    expected=L.RuleSet(board_size=n,
        piece_types=tuple(L.PieceType(t,t,tuple(L.LeapAtom(v)for v in L.offsets(mask)),is_anchor=(t=='K'))
                          for t,mask in(('K',3),('A',a),('B',b))),
        initial_position=rule.initial_position,
        drop_allowed={t:((False,)*(n*n),)*2 for t in('A','B')},
        max_ply=6,repetition_limit=2,stalemate_result='draw',capture_disposition='remove_from_game')
    inventory=Counter((p.owner,p.current_type_id,p.base_type_id)
                      for row in rule.initial_position for p in row if p is not None)
    expected_inventory=Counter({(0,'K','K'):1,(0,'A','A'):1,(1,'K','K'):1})
    if has_B:expected_inventory[(1,'B','B')]=1
    assert inventory==expected_inventory, 'outside declared roster inventory scope'
    assert L.ruleset_to_dict(rule)==L.ruleset_to_dict(expected), 'outside complete rule scope'
    return L.compile_rule(rule)


def pos(c,cells,n,side=1):
    board=[None]*(n*n)
    for sq,owner,tid in zip(cells,(0,0,1,1),('K','A','K','B')):
        board[sq]=L.Piece(owner,tid,tid)
    return replace(c.initial_position,board=tuple(board),side_to_move=side)


def records(compiled,value,cache):
    count=0
    for node in nodes(value):
        count+=1
        key=json.dumps(node['record'],sort_keys=True)
        if key in cache:
            assert node==cache[key], 'duplicate record with inconsistent retained node'
        else:
            assert snapshot(replay(compiled,node['record']))==node
            cache[key]=node
    return count


def qualify(root):
    tick=time.perf_counter();manifest=load(root/'manifest.json')
    for name,item in manifest['files'].items():
        raw=(root/name).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        assert len(raw)==item['bytes']
        if name.endswith('.gz'):
            assert hashlib.sha256(gzip.decompress(raw)).hexdigest()==item['decoded_original_sha256']
    sources=load(root/'executed-sources.json.gz')
    for key,value in sources['documents_utf8'].items():
        assert hashlib.sha256(value.encode('utf-8')).hexdigest()==sources['original_sha256'][key]
    for key,name in(('joint_cage','joint-cage-registration.json'),('radius_two','radius-two-registration.json'),
                    ('corner_law','corner-registration.json'),('mate_entry','mate-entry-registration.json'),
                    ('entry_mu','entry-mu-registration.json')):
        assert sources['original_sha256'][key]==load(root/name)['source_sha256']
    delayed=verify_measurements(load(root/'delayed.json.gz'))
    history=verify_history(load(root/'history.json.gz'))
    joint=load(root/'joint-cage.json.gz');static_frontiers=0
    for row in joint['rows']:
        c=compile_scoped(row['rule'],5,row['mask'],27)
        for case in row['cases']:
            p=pos(c,case['placement'],5)
            assert L.record_value(p)==case['static_position']
            assert is_in_check(p,1,c)
            assert is_in_check(p,0,c)==case['previous_mover_checked']
            if not case['previous_mover_checked']:
                assert L.record_value(legal_actions_from_position(p,c))==case['actual_legal_actions']
                static_frontiers+=1
    radius=load(root/'radius-two.json.gz')
    rindex={(x['n'],x['mask']):x for x in radius['rows']}
    for case in radius['boundary_raw_frontiers']:
        rr=rindex[case['n'],case['mask']];c=compile_scoped(rr['rule'],case['n'],case['mask'],27)
        p=pos(c,case['geometry']['placement'],case['n'])
        assert L.record_value(p)==case['static_position']
        assert L.record_value(legal_actions_from_position(p,c))==case['actions']
        static_frontiers+=1
    law=load(root/'corner-law.json.gz');cache={};record_occurrences=0
    for row in law['rows']:
        c=compile_scoped(row['rule'],5,row['mask'],row['B_mask'])
        for case in row['cases']:
            p=pos(c,case['placement'],5)
            assert L.record_value(p)==case['static_position']
            assert is_in_check(p,0,c)==case['previous_mover_checked']
            assert is_in_check(p,1,c)==case['target_checked']
            if not case['previous_mover_checked']:
                assert L.record_value(legal_actions_from_position(p,c))==case['actions']
                static_frontiers+=1
    for row in law['fresh_witnesses']:
        c=compile_scoped(row['rule'],5,row['mask'],5)
        record_occurrences+=records(c,row,cache)
    corner_q=qualify_corner(law)
    entry=load(root/'mate-entry.json.gz');inverse_checks=0
    for row in entry['n3_mate_rows']:
        c=compile_scoped(row['rule'],3,22,row['B_mask'])
        p=pos(c,row['cells'],3)
        assert L.record_value(p)==row['mate_position']
        assert is_in_check(p,1,c)and not is_in_check(p,0,c)
        assert not legal_actions_from_position(p,c)
        static_frontiers+=1
        for case in row['inverse_candidates']:
            if 'predecessor_position'not in case:continue
            which=0 if case['piece']=='K'else 1
            cells=list(row['cells']);cells[which]=case['from_square'][1]*3+case['from_square'][0]
            pre=pos(c,cells,3,side=0)
            assert L.record_value(pre)==case['predecessor_position']
            assert is_in_check(pre,1,c)==case['enemy_king_already_checked']
            assert is_in_check(pre,0,c)==case['own_king_checked']
            inverse_checks+=1
    for row in entry['n4_fresh_rows']:
        c=compile_scoped(row['rule'],4,row['mask'],row['B_mask'])
        record_occurrences+=records(c,row,cache)
    entry_q=qualify_entry(entry)
    mu=load(root/'entry-mu.json.gz')
    for cohort in mu['cohorts']:
        n=cohort['n'];assert mu_count(n)==cohort['mu_count']
        if n<=4:assert brute_mu(n)==cohort['mu_count']
        # Independent explicit inverse templates, not producer incoming().
        a_sources=[]if n==3 else[(1,3),(3,1),(3,3)]
        if n==5:a_sources +=[(4,2),(2,4),(0,4),(4,0),(4,4)]
        expected={x for ax,ay in a_sources for x in d4([2,ay*n+ax,0,n],n)}
        assert expected=={tuple(x['placement'])for x in cohort['positive_cases']}
        for case in cohort['positive_cases']:
            for row in case['states']:
                c=compile_scoped(row['rule'],n,row['mask'],5)
                record_occurrences+=records(c,row,cache)
                legal={physical_action(a,n)for a in row['root']['legal_actions']}
                assert row['action_present']==(tuple(case['action_key'])in legal)
                if row['after']:
                    record=L.deserialize_game_record(json.dumps(row['after']['record']))
                    assert physical_action(L.record_value(record.actions[-1]),n)==tuple(case['action_key'])
    mu_q=qualify_mu(mu)

    boundary_sources=load(root/'boundary-executed-sources.json.gz')
    for key,value in boundary_sources['documents_utf8'].items():
        assert hashlib.sha256(value.encode('utf-8')).hexdigest()==boundary_sources['original_sha256'][key]
    for key,name in(('parity_boundary','parity-boundary-registration.json'),('entry_channels','entry-channels-registration.json')):
        assert boundary_sources['original_sha256'][key]==load(root/name)['source_sha256']
    boundary=load(root/'parity-boundary.json.gz')
    for row in boundary['rows']:
        c=compile_scoped(row['rule'],3,row['mask'],5,has_B=row['B_present'])
        record_occurrences+=records(c,row,cache)
    boundary_q=qualify_parity_boundary(boundary)
    channels=load(root/'entry-channels.json.gz')
    # Independent Cartesian allowed-set admission, not the producer permutation loop.
    boardset=set(range(9));admitted={};from itertools import permutations
    for mask in(22,23):
        support=set()
        for u,v in permutations(range(9),2):
            if max(abs(u%3-v%3),abs(u//3-v//3))<=1:continue
            forbidden_a={y*3+x for dx,dy in L.offsets(mask)for x,y in[(v%3+dx,v//3+dy)]if 0<=x<3 and 0<=y<3}
            forbidden_b={y*3+x for dx,dy in L.offsets(5)for x,y in[(u%3+dx,u//3+dy)]if 0<=x<3 and 0<=y<3}
            for a in boardset-{u,v}-forbidden_a:
                for b in boardset-{u,v,a}-forbidden_b:support.add((u,a,v,b))
        admitted[mask]=support
    assert {tuple(r['placement'])for r in channels['rows']}==admitted[23]<=admitted[22]
    admission=load(root/'entry-channels-admission.json.gz')
    assert set(map(tuple,admission['source_only_placements']))==admitted[22]-admitted[23]
    assert (len(admitted[22]),len(admitted[23]),len(admitted[22]-admitted[23]))==(360,152,208)
    reuse_count=0
    for row in channels['rows']:
        low,high=row['pair'];compiled={}
        for frame in row['pair']:
            c=compile_scoped(frame['rule'],3,frame['mask'],5);compiled[frame['mask']]=c
            record_occurrences+=records(c,frame,cache)
            for branch in frame['branches']:
                if branch['source'].startswith('REUSED'):
                    source=next(r for r in boundary['rows']if r['B_present']and r['mask']==frame['mask']and r['rule']==frame['rule']and r['shared_action']==branch['action'])
                    assert source['initial']==frame['root']and source['after']==branch['child']
                    reuse_count+=1
        hindex={tuple(x['action_key']):x for x in high['branches']}
        for win in row['immediate_mating_actions']:
            if win['shared']:continue
            old=win['old_static_post'];rawboard=hindex[tuple(win['action_key'])]['child']['state']['position']['board']
            board=tuple(None if x is None else L.Piece(x['owner'],x['base_type_id'],x['current_type_id'])for x in rawboard)
            p=replace(compiled[22].initial_position,board=board,side_to_move=1)
            assert L.record_value(p)==old['position']
            checked=is_in_check(p,1,compiled[22]);acts=legal_actions_from_position(p,compiled[22])
            assert checked==old['checked']and L.record_value(acts)==old['legal_actions']
            assert old['static_mate']==(checked and not acts)
            static_frontiers+=1
    assert reuse_count==channels['reused_exact_child_returns']==2
    channel_q=qualify_channels(channels)

    named_sources=load(root/'named-executed-sources.json.gz')
    for key,value in named_sources['documents_utf8'].items():
        assert hashlib.sha256(value.encode('utf-8')).hexdigest()==named_sources['original_sha256'][key]
    named_reg=load(root/'named-mu-registration.json.gz');named=load(root/'named-mu-bridge.json.gz')
    assert named_sources['original_sha256']['named_mu_bridge']==named_reg['source_sha256']
    assert named_sources['original_sha256']['named_mu_failed_protocol']==load(root/'named-mu-generation-failure.json')['failed_source_sha256']
    assert named['ended_at']<=named_reg['original_phase_deadline']
    # Decode/check base rule grammar, then compile the ACTUAL full named rules.
    named_compiled={}
    selections=named_reg['mu']['keys'];old_by={tuple(r['placement']):r for r in channels['rows']}
    ordered_old=sorted(channels['rows'],key=lambda r:tuple(r['placement']))
    for mask in(22,23):
        rr=L.ruleset_from_dict(named_reg['fixed_rules'][str(mask)])
        compile_scoped(L.ruleset_to_dict(replace(rr,initial_setup_options=())),3,mask,5)
        assert rr.initial_position==L.ruleset_from_dict(ordered_old[0]['pair'][0]['rule']).initial_position
        options={o.setup_key:o.position for o in rr.initial_setup_options}
        assert set(options)==set(selections[1:])and len(options)==151
        for key,row in zip(selections[1:],ordered_old[1:]):
            assert options[key]==L.ruleset_from_dict(row['pair'][0]['rule']).initial_position
        named_compiled[mask]=L.compile_rule(rr)
    for row in named['rows']:
        for frame in row['frames']:
            record_occurrences+=records(named_compiled[frame['mask']],frame,cache)
    for cycle in named['cycles']:
        if cycle['mode']=='fixed_named':
            assert cycle['rule']==named_reg['fixed_rules'][str(cycle['mask'])]
            c=named_compiled[cycle['mask']]
        else:c=compile_scoped(cycle['rule'],3,cycle['mask'],5)
        record_occurrences+=records(c,cycle,cache)
    named_q=qualify_named(named_reg,named,channels)
    symmetry=symmetry_analysis(channels)
    assert symmetry==load(root/'symmetry-analysis.json.gz')

    obstruction_sources=load(root/'obstruction-executed-source.json.gz')
    raw_source=obstruction_sources['documents_utf8']['negative_obstruction']
    assert hashlib.sha256(raw_source.encode('utf-8')).hexdigest()==obstruction_sources['original_sha256']['negative_obstruction']
    obstruction_reg=load(root/'negative-obstruction-registration.json.gz')
    assert obstruction_reg['source_sha256']==obstruction_sources['original_sha256']['negative_obstruction']
    assert obstruction_reg['fixed_rule']==named_reg['fixed_rules']['23']
    obstruction=load(root/'negative-obstruction.json.gz')
    assert obstruction['ended_at']<=obstruction_reg['original_phase_deadline']
    for row in obstruction['roots']:
        record_occurrences+=records(named_compiled[23],row,cache)
    obstruction_q=qualify_obstruction(obstruction,channels,named)
    next_frontier=load(root/'next-two-orbits.json.gz')
    assert next_frontier['complete_rule']==named_reg['fixed_rules']['23']
    unresolved={}
    for row in obstruction['roots']:
        if not row['proof_complete']:unresolved.setdefault(min(d4(row['placement'],3)),[]).append(row)
    assert len(unresolved)==2 and all(len(v)==8 for v in unresolved.values())
    assert {tuple(r['representative'])for r in next_frontier['representatives']}==set(unresolved)
    for row in next_frontier['representatives']:
        reference=next(r for r in unresolved[tuple(row['representative'])]if tuple(r['placement'])==tuple(row['representative']))
        assert row['named_setup_key']==reference['key']
        assert row['full_root_record']==reference['root']['record']and row['root_state']==reference['root']['state']
        assert row['unresolved_children']==[c['white_child']for c in reference['clauses']if c['kind']=='unresolved_no_captureA_reply']
        assert {tuple(r['placement'])for r in row['all_members']}=={tuple(r['placement'])for r in unresolved[tuple(row['representative'])]}
        record_occurrences+=records(named_compiled[23],row,cache)



    return dict(status='PASS',public_files=len(manifest['files']),source_capsule_executions=0,
                new_Player_queries=0,new_graph_or_solver_calls=0,
                delayed_record_occurrences=delayed['node_occurrences'],delayed_unique_records=delayed['unique_full_records'],
                history_record_occurrences=history['node_occurrences'],history_unique_records=history['unique_full_records'],
                other_record_occurrences=record_occurrences,other_unique_full_records=len(cache),
                static_frontier_binding_occurrences=static_frontiers,inverse_position_check_occurrences=inverse_checks,
                corner=corner_q,entry=entry_q,mu=mu_q,boundary=boundary_q,channels=channel_q,
                admission_counts=dict(old=360,common=152,source_only=208),named_mu=named_q,
                symmetry={k:v for k,v in symmetry.items()if k!='orbits'},obstruction=obstruction_q,
                next_unknown_geometric_orbits=2,
                seconds=time.perf_counter()-tick,
                scope='Same-Core semantic binding and independently specified finite combinatorics; not an independent WDL engine or proof of all-n solely by finite tests.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise ValueError('NEW qualification output required')
    r=qualify(a.directory);write_json(a.output,r)
    print(json.dumps({k:v for k,v in r.items()if k not in('corner','entry','mu','boundary','channels','named_mu','symmetry','obstruction')}))


if __name__=='__main__':main()
